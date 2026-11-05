#!/usr/bin/env python3
"""Build a native preview from clean committed source and record its artifact hash.

Uses a public dummy API identity accepted only by the local development server.
Does not launch clients, send OTPs, sign for distribution, or upload artifacts.
"""
import argparse
import fcntl
import hashlib
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_preview import NATIVE_KINDS, digest, source_tree, write_bundle_archive

ROOT = Path(__file__).resolve().parents[2]
DUMMY_ID = "100001"
DUMMY_HASH = "0123456789abcdef0123456789abcdef"


def run_command(command, *, cwd, log, env=None):
    with Path(log).open("a", encoding="utf-8") as output:
        with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors="replace") as process:
            for line in process.stdout:
                output.write(line)
                output.flush()
                print(line, end="", flush=True)
            code = process.wait()
    if code:
        raise subprocess.CalledProcessError(code, command)


def record_product(component, product, output, revision, epoch, commands, versions):
    product, output = Path(product), Path(output)
    if not product.exists() or (component == "android" and not product.is_file()):
        raise ValueError(f"native product not found: {product}")
    artifact = output / NATIVE_KINDS[component]["suffix"]
    if component == "android":
        shutil.copyfile(product, artifact)
    else:
        if component == "ios":
            with (product / "Info.plist").open("rb") as handle:
                info = plistlib.load(handle)
            if "iPhoneSimulator" not in info.get("CFBundleSupportedPlatforms", []):
                raise ValueError("iOS product is not an iPhoneSimulator bundle")
        write_bundle_archive(product, artifact, epoch)
    evidence = {
        "schema_version": 1,
        "component": component,
        "source_commit": revision,
        "source_dirty": False,
        "build_exit_code": 0,
        "build_command": commands,
        "tool_versions": versions,
        "architecture": platform.machine(),
        "distribution": NATIVE_KINDS[component]["distribution"],
        "api_identity": "public-dummy-local-development-only",
        "artifact_file": artifact.name,
        "artifact_sha256": digest(artifact),
    }
    (output / "build.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments], text=True).strip()


def tool_version(*command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


def find_android_product(component):
    # AGP 8.6 can place this overridden app.apk in intermediates instead of
    # outputs. Trust its variant metadata, and require exactly one real APK.
    products = []
    for location in ("outputs", "intermediates"):
        variant = Path(component) / f"TMessagesProj_App/build/{location}/apk/afat/debug"
        metadata_path = variant / "output-metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("variantName") != "afatDebug" or metadata.get("applicationId") != "com.privatechat.messenger.beta":
            raise ValueError("Android output metadata does not describe the preview variant")
        for element in metadata.get("elements", []):
            name = element.get("outputFile", "")
            if not name or Path(name).name != name or not name.endswith(".apk"):
                raise ValueError("unsafe Android output filename")
            product = variant / name
            if product.is_file():
                products.append(product)
    if len(products) != 1:
        raise ValueError(f"expected one Android debug product, found {len(products)}")
    return products[0]


def android_build(run, env, temporary, args):
    env = {**env, "PRIVATE_CHAT_API_ID": DUMMY_ID, "PRIVATE_CHAT_API_HASH": DUMMY_HASH}
    keystore = temporary / "ci-debug.keystore"
    run(["keytool", "-genkeypair", "-noprompt", "-keystore", str(keystore), "-storepass", "android",
         "-alias", "androiddebugkey", "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
         "-validity", "30", "-dname", "CN=Private Chat CI Debug,O=Private Chat,C=US"], ROOT, env)
    init = temporary / "ci-debug-signing.gradle"
    escaped = str(keystore).replace("\\", "\\\\").replace("'", "\\'")
    init.write_text("gradle.projectsEvaluated {\n"
                    "  allprojects { p ->\n"
                    "    if (p.plugins.hasPlugin('com.android.application')) {\n"
                    "      p.android.signingConfigs.debug {\n"
                    f"        storeFile p.file('{escaped}')\n"
                    "        storePassword 'android'\n"
                    "        keyAlias 'androiddebugkey'\n"
                    "        keyPassword 'android'\n"
                    "      }\n"
                    "    }\n"
                    "  }\n"
                    "}\n", encoding="utf-8")
    wrapper = str(ROOT / "android" / "gradlew")
    run([wrapper, "--version"], ROOT / "android", env)
    run([sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"], ROOT / "android", env)
    run([wrapper, "--no-daemon", "--console=plain", f"--max-workers={args.jobs}", "--init-script", str(init),
         ":TMessagesProj_App:assembleAfatDebug", "-Pandroid.injected.build.abi=arm64-v8a"], ROOT / "android", env)
    product = find_android_product(ROOT / "android")
    with zipfile.ZipFile(product) as apk:
        abis = {name.split("/")[1] for name in apk.namelist() if name.startswith("lib/") and name.endswith(".so")}
        if abis != {"arm64-v8a"}:
            raise ValueError(f"Android preview must contain ARM64 native libraries only; found {sorted(abis)}")
    sdk = Path(env.get("ANDROID_SDK_ROOT", env.get("ANDROID_HOME", "")))
    run([str(sdk / "build-tools/35.0.0/apksigner"), "verify", str(product)], ROOT / "android", env)
    return product, {"java": tool_version("java", "-version"), "gradle": "8.7", "ndk": "27.2.12479018"}


def desktop_build(run, env, temporary, args):
    component = ROOT / "desktop"
    env = {**env, "CMAKE_BUILD_PARALLEL_LEVEL": str(args.jobs), "MAKEFLAGS": f"-j{args.jobs}"}
    xcode = tool_version("xcodebuild", "-version")
    if xcode.startswith("Xcode 27"):
        overrides = temporary / "desktop-xcode27.xcconfig"
        overrides.write_text("MACOSX_DEPLOYMENT_TARGET = 12.0\n", encoding="utf-8")
        env["XCODE_XCCONFIG_FILE"] = str(overrides)
    run([sys.executable, "Telegram/build/prepare/prepare.py", "skip-release", "silent"], component, env)
    configure = [sys.executable, "Telegram/configure.py", "-D", f"TDESKTOP_API_ID={DUMMY_ID}",
                 "-D", f"TDESKTOP_API_HASH={DUMMY_HASH}", "-D", "CMAKE_OSX_DEPLOYMENT_TARGET=12.0"]
    if xcode.startswith("Xcode 27"):
        configure += ["-D", "CMAKE_CXX_FLAGS=-DMETA_NO_STD_FORWARD_DECLARATIONS",
                      "-D", "CMAKE_OBJCXX_FLAGS=-DMETA_NO_STD_FORWARD_DECLARATIONS"]
    run(configure, component, env)
    run(["cmake", "--build", "out", "--config", "Debug", "--target", "Telegram", "--parallel", str(args.jobs)], component, env)
    product = component / "out/Debug/Private Chat.app"
    run(["codesign", "--verify", "--deep", "--strict", str(product)], component, env)
    return product, {"xcode": xcode, "cmake": tool_version("cmake", "--version")}


def ios_build(run, env, temporary, args):
    component = ROOT / "ios"
    expected = json.loads((component / "versions.json").read_text())["xcode"]
    actual = tool_version("xcodebuild", "-version")
    if actual.splitlines()[0] != f"Xcode {expected}":
        raise ValueError(f"iOS CI requires source-pinned Xcode {expected}; found {actual.splitlines()[0]}. "
                         "Local Xcode 27 compatibility experiments are documented in docs/ci-cd.md.")
    config = json.loads((component / "build-system/template_minimal_development_configuration.json").read_text())
    config.update(api_id=DUMMY_ID, api_hash=DUMMY_HASH, team_id="LOCALDEBUG")
    configuration = temporary / "ios-simulator-configuration.json"
    configuration.write_text(json.dumps(config), encoding="utf-8")
    configuration.chmod(0o600)
    cache = Path(env.get("PRIVATE_CHAT_IOS_CACHE", str(ROOT / "toolchains/ios-bazel-cache"))).resolve()
    run([sys.executable, "build-system/Make/Make.py", f"--cacheDir={cache}", "generateProject",
         f"--configurationPath={configuration}", "--codesigningInformationPath=build-system/fake-codesigning",
         "--disableProvisioningProfiles", "--disableExtensions"], component, env)
    bazelrc = component / "xcodeproj.bazelrc"
    with bazelrc.open("a", encoding="utf-8") as handle:
        handle.write(f"\nbuild --jobs={args.jobs}\nbuild --worker_max_instances=1\n")
        handle.write(f"build --@build_bazel_rules_swift//swift:copt=-j\nbuild --@build_bazel_rules_swift//swift:copt={args.jobs}\n")
    derived = ROOT / "toolchains/ios-ci-derived-data"
    run(["xcodebuild", "-project", "Telegram/Telegram.xcodeproj", "-scheme", "Telegram", "-configuration", "Debug",
         "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(derived),
         "CODE_SIGNING_ALLOWED=NO", "-jobs", str(args.jobs), "build"], component, env)
    products = []
    for product in (derived / "Build/Products/Debug-iphonesimulator").rglob("Telegram.app"):
        plist = product / "Info.plist"
        if plist.is_file():
            with plist.open("rb") as handle:
                if "iPhoneSimulator" in plistlib.load(handle).get("CFBundleSupportedPlatforms", []):
                    products.append(product.resolve())
    products = sorted(set(products))
    if len(products) != 1:
        raise ValueError(f"expected one iOS simulator product, found {len(products)} under the CI DerivedData tree")
    return products[0], {"xcode": actual, "bazel": json.loads((component / "versions.json").read_text())["bazel"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=sorted(NATIVE_KINDS))
    parser.add_argument("--output", required=True, type=Path, help="new/empty directory outside the repository")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args(argv)
    if args.jobs < 1:
        raise ValueError("jobs must be positive")
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("output must be outside the source repository")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be empty")
    if args.component in {"desktop", "ios"} and platform.system() != "Darwin":
        raise ValueError("Apple native builds require macOS with full licensed Xcode")
    revision = git("rev-parse", "--verify", "HEAD^{commit}")
    source_tree(revision)
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("native provenance requires a clean committed monorepo checkout")
    epoch = int(git("show", "-s", "--format=%ct", revision))
    lock_name = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    with open(Path(tempfile.gettempdir()) / f"private-chat-native-{lock_name}.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("another native build is active for this checkout") from error
        output.mkdir(parents=True, exist_ok=True)
        commands = []
        log = output / "build.log"

        def run(command, cwd, env):
            public = [value.replace(str(ROOT), "$REPO").replace(str(temporary), "$TEMP") for value in command]
            commands.append({"cwd": str(Path(cwd).relative_to(ROOT)) or ".", "argv": public})
            run_command(command, cwd=cwd, env=env, log=log)

        with tempfile.TemporaryDirectory(prefix="private-chat-build-") as temporary_path:
            temporary = Path(temporary_path)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            build = {"android": android_build, "desktop": desktop_build, "ios": ios_build}[args.component]
            product, versions = build(run, env, temporary, args)
            if git("status", "--porcelain", "--untracked-files=all"):
                raise ValueError("build changed source files; provenance was not emitted")
            artifact = record_product(args.component, product, output, revision, epoch, commands, versions)
    print(f"Native preview built from {revision}: {artifact.name}; evidence: build.json")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Native preview build failed: {error}", file=sys.stderr)
        sys.exit(error.returncode if isinstance(error, subprocess.CalledProcessError) and 0 < error.returncode < 126 else 1)
