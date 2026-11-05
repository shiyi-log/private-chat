#!/usr/bin/env python3
"""Create reviewable preview assets from one committed monorepo revision.

Source archives are reproducible. Native products keep their own signatures and
are labelled as previews; this script never signs, builds, logs in, or uploads.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMPONENTS = {"server", "desktop", "android", "ios", "docs", ".github", "scripts"}
ROOT_FILES = {"README.md", "LICENSE", "NOTICE", "VERSION", ".gitignore", ".gitattributes", ".gitmodules", "components.json", "repository-imports.json", "THIRD_PARTY_NOTICES.md"}
SERVER_RUNTIME_FILES = {
    "server/teamgramd/bin/config.json",
    "server/teamgramd/bin/killall.sh",
    "server/teamgramd/bin/runall2.sh",
    "server/teamgramd/bin/runall-docker.sh",
}
REQUIRED_SOURCES = ("server/go.mod", "desktop/CMakeLists.txt", "android/settings.gradle", "ios/versions.json", "docs/README.md")
EXCLUDED_PARTS = {".git", ".gradle", "__pycache__", ".idea", ".vscode", "node_modules", "DerivedData", "out", "build-input", ".cxx", "tdata", "DebugLogs", "fastlanematch", "xcuserdata"}
# A standalone PEM header marks key material. Source-code examples containing
# the header as a quoted string are not themselves private keys.
PRIVATE_KEY = re.compile(br"(?m)^-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----\r?$")
# These tracked upstream cryptography tests contain known public test keys.
# Pin full-file hashes so edits or newly added PEM material still fail closed.
PUBLIC_KEY_FIXTURE_SHA256 = {
    "android/TMessagesProj/jni/boringssl/crypto/dsa/dsa_test.cc": "b44576fefea97f0867cab09a77d76fce2bb3c6750ce8dd0a498ac880b3289502",
    "android/TMessagesProj/jni/boringssl/crypto/pem/pem_test.cc": "2b0328e9653efc596b651c549048e9df847ddf5f790d128f5e358b44401e300a",
    "android/TMessagesProj/jni/boringssl/crypto/pkcs7/pkcs7_test.cc": "809fca2081db69c794d379feeb2f83bb9fa7824fc544952c17712246927862c3",
    "android/TMessagesProj/jni/boringssl/crypto/x509/x509_test.cc": "62117d3f4495e6f1356763ff864a421efb1743422a0cfe7c8c81d5da02744f25",
    "android/TMessagesProj/jni/boringssl/pki/testdata/path_builder_unittest/multi-root-A-by-B.pem": "b36fc9b31770412926e25ed0a22e5cfe9649bb8efbe1707a04f15a5fc7d0a543",
    "android/TMessagesProj/jni/boringssl/pki/testdata/verify_signed_data_unittest/rsa-pss-sha256.pem": "2f1fedb079b51e667e303d4216b41940c77e13cc298399120bcb92e0aae4fe8b",
    "android/TMessagesProj/jni/boringssl/ssl/ssl_test.cc": "38c677bcbf7d13e5405c9f511f8b7ca7243d53a69f2ab41bbdd17e6adae4d22c",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/channel_id_key.pem": "476fa95e770f5d27a5251192b5d46c5aa445014b3589af5cbde6503eeb68a84d",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/ecdsa_p224_key.pem": "35d96675fbe71c4b4ea895d3cb8b3f44477c5e9d7d65b0427aadaf78407014fe",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/ecdsa_p256_key.pem": "ca7d6ce7ecb54d5b8233bdf3476eb143d31367d981d84d6be6d1c5e7fbfc0f2b",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/ecdsa_p384_key.pem": "997b7ba56a79fe69373a0c2c8b7efcd1fd3df93f7e6a8a4913863bcf333c7ca1",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/ecdsa_p521_key.pem": "964bc9015fa6e4ab422bb8a7889ec0be4dc7d721cb6a51639469be621c07c876",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/ed25519_key.pem": "c4932a9b6b97423b249a53e58d706f820185467464699038ed7ca5b29815ba03",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/rsa_1024_key.pem": "09d7e7a04cceb4d5a8c84ad020c199b2c09a9ac31df48a4c1a29d777843a036c",
    "android/TMessagesProj/jni/boringssl/ssl/test/runner/rsa_2048_key.pem": "c7ba07e53101b26e544c5a97367dda9cd9c85059228b3dae47533bc418c33782",
    "ios/third-party/boringssl/src/crypto/dsa/dsa_test.cc": "e8457f091bc32152868f5b4cd2f098ed8401e30435ab14134567c1fca509ad8a",
    "ios/third-party/boringssl/src/crypto/pkcs7/pkcs7_test.cc": "997f9e5465d87d73d1d4403a0771a87cd27ee2f8db369cbb279b9149c1d39dab",
    "ios/third-party/boringssl/src/crypto/x509/x509_test.cc": "112c5b3fadb0c235db3214835c0a4aa7c85f7cce8f2ca0fc8c632de4b8a5e48d",
    "ios/third-party/boringssl/src/ssl/ssl_test.cc": "d054a5d6b8590edaad990d66b3fb021b9bce350594708a6123b11f954494fa99",
    "ios/third-party/td/td/tdutils/test/crypto.cpp": "556dec23d648083f682f762b4bec8616723475a890ff569d2ad3b63f08e6e78c",
}
NATIVE_KINDS = {
    "android": {"distribution": "debug-android-preview", "suffix": "android-debug.apk"},
    "desktop": {"distribution": "local-macos-debug-preview", "suffix": "macos-debug.app.tar.gz"},
    "ios": {"distribution": "unsigned-ios-simulator-preview", "suffix": "ios-simulator.app.tar.gz"},
}


def validate_version(version):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)?", version):
        raise ValueError("version must be a safe vMAJOR.MINOR.PATCH[-preview.N] tag")
    return version


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"unsafe archive path: {name}")
    return path


def source_allowed(name):
    path = safe_path(name)
    parts = path.parts
    if not parts:
        return False
    if len(parts) == 1:
        return name in ROOT_FILES
    if parts[0] not in SOURCE_COMPONENTS:
        return False
    if parts[0] == "scripts" and parts[1] != "ci":
        return False
    if EXCLUDED_PARTS.intersection(parts):
        return False
    if parts[:2] == ("server", "data"):
        return False
    if parts[0] == "android" and len(parts) > 2 and parts[2] == "build":
        return False
    if parts[:2] in {("android", "build"), ("ios", "build"), ("desktop", "build")}:
        return False
    base = parts[-1]
    if base == "local.properties" or base == ".DS_Store" or base.startswith("bazel-") or base.endswith(".local.json"):
        return False
    if base == ".env" or (base.startswith(".env.") and not base.endswith((".example", ".sample"))):
        return False
    if base.endswith((".key", ".keystore", ".jks", ".p12", ".pfx", ".mobileprovision", ".pyc", ".log", ".session")):
        return False
    if "teamgramd" in parts and "bin" in parts and name not in SERVER_RUNTIME_FILES:
        return False
    # Bazel output roots (for example ios/bazel-out) are generated artifacts;
    # nested source directories such as ios/build-system/bazel-rules are not.
    if len(parts) > 1 and parts[1].startswith("bazel-"):
        return False
    return True


def validate_link(name, target):
    safe_path(name)
    if PurePosixPath(target).is_absolute() or "\\" in target:
        raise ValueError(f"absolute/external symlink: {name}")
    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
    safe_path(normalized)
    # Do not let a component point at a sibling component or runtime directory.
    if normalized.split("/")[0] != name.split("/")[0]:
        raise ValueError(f"escaping symlink: {name}")


def normalized_info(member, name, epoch):
    result = tarfile.TarInfo(name)
    result.uid = result.gid = 0
    result.uname = result.gname = ""
    result.mtime = epoch
    result.mode = 0o755 if member.mode & 0o111 else 0o644
    result.type = member.type
    result.linkname = member.linkname
    result.size = member.size if member.isfile() else 0
    if member.isdir():
        result.mode = 0o755
    return result


def is_pinned_public_key_fixture(name, data):
    expected = PUBLIC_KEY_FIXTURE_SHA256.get(name)
    return expected is not None and hashlib.sha256(data).hexdigest() == expected


def write_source_archive(source, destination, version, epoch):
    validate_version(version)
    with tarfile.open(fileobj=source, mode="r:") as original:
        members = []
        for member in original.getmembers():
            if not source_allowed(member.name):
                continue
            if member.isdir():
                continue
            if not (member.isfile() or member.issym()):
                raise ValueError(f"unsupported source member: {member.name}")
            if member.issym():
                validate_link(member.name, member.linkname)
            members.append(member)
        with gzip.GzipFile(fileobj=destination, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for member in sorted(members, key=lambda item: item.name):
                    data = original.extractfile(member).read() if member.isfile() else None
                    if (data is not None and PRIVATE_KEY.search(data)
                            and not is_pinned_public_key_fixture(member.name, data)):
                        raise ValueError(f"private key detected in source asset: {member.name}")
                    info = normalized_info(member, f"private-chat-{version}/{member.name}", epoch)
                    archive.addfile(info, io.BytesIO(data) if data is not None else None)


def write_bundle_archive(bundle, destination, epoch):
    bundle = Path(bundle).resolve()
    if not bundle.is_dir() or bundle.suffix != ".app":
        raise ValueError("native Apple asset must be an existing .app directory")
    with open(destination, "wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted([bundle] + list(bundle.rglob("*"))):
                    relative = path.relative_to(bundle.parent).as_posix()
                    safe_path(relative)
                    if path.is_symlink():
                        target = os.readlink(path)
                        validate_link(relative, target)
                        try:
                            path.resolve(strict=True).relative_to(bundle)
                        except (ValueError, FileNotFoundError) as error:
                            raise ValueError(f"external/broken native symlink: {relative}") from error
                    if any(part in {"tdata", "DebugLogs", "xcuserdata", ".git"} for part in path.relative_to(bundle).parts):
                        raise ValueError(f"runtime data found in app bundle: {relative}")
                    info = archive.gettarinfo(str(path), relative)
                    info = normalized_info(info, relative, epoch)
                    if not (info.isdir() or info.isfile() or info.issym()):
                        raise ValueError(f"unsupported native asset member: {relative}")
                    if info.isfile():
                        with path.open("rb") as handle:
                            # Scan small text-like files only; larger Mach-O assets
                            # contain no deployment configuration generated here.
                            if info.size < 1024 * 1024:
                                sample = handle.read()
                                if PRIVATE_KEY.search(sample):
                                    raise ValueError(f"private key detected in native asset: {relative}")
                                handle.seek(0)
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def write_checksums(output, assets):
    records = [{"file": asset.name, "sha256": digest(asset), "size_bytes": asset.stat().st_size}
               for asset in sorted(assets, key=lambda path: path.name)]
    (Path(output) / "SHA256SUMS").write_text("".join(f"{item['sha256']}  {item['file']}\n" for item in records), encoding="utf-8")
    return records


def validate_native_provenance(evidence, component, revision, artifact):
    if evidence.get("source_commit") != revision or evidence.get("component") != component:
        raise ValueError(f"{component} native provenance must match the packaged commit and component")
    if evidence.get("source_dirty") is not False or evidence.get("build_exit_code") != 0:
        raise ValueError(f"{component} native provenance requires a clean source and successful build")
    if evidence.get("distribution") != NATIVE_KINDS[component]["distribution"]:
        raise ValueError(f"{component} native distribution does not match the preview type")
    if evidence.get("artifact_sha256") != digest(artifact):
        raise ValueError(f"{component} native artifact checksum does not match build provenance")


def validate_source_tree(entries):
    files = set()
    for mode, name in entries:
        if mode == "160000":
            raise ValueError(f"unexpanded gitlink cannot be packaged: {name}")
        files.add(name)
    missing = sorted(set(REQUIRED_SOURCES) - files)
    if missing:
        raise ValueError(f"source revision is missing monorepo components: {', '.join(missing)}")


def source_tree(revision):
    tree = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-rz", revision])
    entries = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        entries.append((metadata.split()[0].decode("ascii"), name.decode("utf-8")))
    validate_source_tree(entries)


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments], text=True).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", default="HEAD", help="immutable commit/tag to archive; resolved once")
    parser.add_argument("--output", required=True, type=Path, help="new or empty output directory")
    parser.add_argument("--android-apk", type=Path)
    parser.add_argument("--desktop-app", type=Path)
    parser.add_argument("--ios-simulator-app", type=Path)
    parser.add_argument("--android-provenance", type=Path, help="JSON emitted by native_build.py")
    parser.add_argument("--desktop-provenance", type=Path)
    parser.add_argument("--ios-provenance", type=Path)
    args = parser.parse_args(argv)
    validate_version(args.version)
    revision = git("rev-parse", "--verify", "--end-of-options", f"{args.revision}^{{commit}}")
    source_tree(revision)
    epoch = int(git("show", "-s", "--format=%ct", revision))
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be empty; existing release assets are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    # Use a temporary staging directory so a failed validation leaves no
    # plausible release asset or partial checksum list in the output folder.
    with tempfile.TemporaryDirectory(prefix="private-chat-preview-") as directory:
        staging = Path(directory)
        assets = []
        source_path = staging / f"private-chat-{args.version}-source.tar.gz"
        with tempfile.TemporaryFile() as source:
            subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", revision], stdout=source, check=True)
            source.seek(0)
            with source_path.open("wb") as destination:
                write_source_archive(source, destination, args.version, epoch)
        assets.append(source_path)
        native = []
        for kind, input_path, evidence_path in (
            ("android", args.android_apk, args.android_provenance),
            ("desktop", args.desktop_app, args.desktop_provenance),
            ("ios", args.ios_simulator_app, args.ios_provenance),
        ):
            if input_path is None:
                if evidence_path is not None:
                    raise ValueError(f"{kind} provenance supplied without an asset")
                continue
            if evidence_path is None:
                raise ValueError(f"{kind} native asset requires --{kind}-provenance")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            asset_path = staging / f"private-chat-{args.version}-{NATIVE_KINDS[kind]['suffix']}"
            if kind == "android":
                if not input_path.is_file() or input_path.suffix != ".apk":
                    raise ValueError("Android asset must be an existing .apk file")
                shutil.copyfile(input_path, asset_path)
            else:
                write_bundle_archive(input_path, asset_path, epoch)
            validate_native_provenance(evidence, kind, revision, asset_path)
            evidence_name = f"private-chat-{args.version}-{kind}-build.json"
            # Re-serialize an explicit allowlist; never copy local paths or
            # environment variables from an arbitrary evidence file.
            public_evidence = {key: evidence[key] for key in (
                "component", "source_commit", "source_dirty", "build_exit_code", "build_command",
                "tool_versions", "architecture", "distribution", "api_identity", "artifact_sha256") if key in evidence}
            (staging / evidence_name).write_text(json.dumps(public_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            assets.extend([asset_path, staging / evidence_name])
            native.append({"component": kind, "asset": asset_path.name, "provenance": evidence_name,
                           "distribution": NATIVE_KINDS[kind]["distribution"]})
        manifest = {
            "schema_version": 1,
            "version": args.version,
            "source_commit": revision,
            "source_date_epoch": epoch,
            "source_archive": source_path.name,
            "source_archive_reproducible": True,
            "native_products_reproducible": False,
            "native_assets": native,
            "limitations": ["Preview only; native assets are not notarized/App Store distribution packages.",
                            "iOS asset, when present, runs in an Apple Silicon simulator and is not an IPA.",
                            "Source archives exclude deployment keys, signing stores and all local runtime data."],
            "assets": [{"file": path.name, "sha256": digest(path), "size_bytes": path.stat().st_size} for path in assets],
        }
        manifest_path = staging / f"private-chat-{args.version}-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        assets.append(manifest_path)
        write_checksums(staging, assets)
        for path in [*assets, staging / "SHA256SUMS"]:
            shutil.copyfile(path, output / path.name)
    print(f"Packaged {len(assets)} assets from {revision}; checksum list: {output / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Preview packaging failed: {error}", file=sys.stderr)
        sys.exit(1)
