"""Native build contracts; opt into the AGP signing and ABI fixture with
PRIVATE_CHAT_TEST_ANDROID_SIGNING=1 and a prepared JDK17/Android35 SDK.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[1] / "native_build.py"


class NativeBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("native_build", SCRIPT)
        cls.native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.native)

    def test_failed_native_command_propagates_exit_and_logs_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "build.log"
            with self.assertRaises(subprocess.CalledProcessError) as failure:
                self.native.run_command([sys.executable, "-c", "print('compiler diagnostic'); raise SystemExit(17)"],
                                        cwd=directory, log=log)
            self.assertEqual(failure.exception.returncode, 17)
            self.assertIn("compiler diagnostic", log.read_text())

    def test_missing_product_cannot_receive_successful_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaisesRegex(ValueError, "product"):
                self.native.record_product("android", output / "missing.apk", output, "a" * 40, 1, [], {})
            self.assertFalse((output / "build.json").exists())

    def test_android_evidence_hash_is_bound_to_the_exported_product(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            apk = output / "input.apk"
            apk.write_bytes(b"abc")
            self.native.record_product("android", apk, output, "a" * 40, 1, [["gradle", "assembleAfatDebug"]], {"java": "17"})
            evidence = json.loads((output / "build.json").read_text())
            self.assertEqual(evidence["artifact_sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            self.assertEqual(evidence["source_commit"], "a" * 40)
            self.assertFalse(evidence["source_dirty"])
            self.assertEqual(evidence["build_exit_code"], 0)
            self.assertEqual((output / evidence["artifact_file"]).read_bytes(), b"abc")

    def test_android_product_uses_agp_intermediates_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            variant = root / "TMessagesProj_App/build/intermediates/apk/afat/debug"
            variant.mkdir(parents=True)
            (variant / "app.apk").write_bytes(b"apk")
            metadata = {"applicationId": "com.privatechat.messenger.beta", "variantName": "afatDebug",
                        "elements": [{"outputFile": "app.apk"}]}
            (variant / "output-metadata.json").write_text(json.dumps(metadata))
            self.assertEqual(self.native.find_android_product(root), variant / "app.apk")
            metadata["elements"][0]["outputFile"] = "../../outside.apk"
            (variant / "output-metadata.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "output"):
                self.native.find_android_product(root)

    @unittest.skipUnless(os.environ.get("PRIVATE_CHAT_TEST_ANDROID_SIGNING") == "1",
                         "requires the prepared Android SDK and JDK17")
    def test_android_ci_signing_and_preview_abi_are_finalized_before_agp_locks_the_dsl(self):
        # Exercise the exact init script emitted by android_build in a tiny app.
        class BuildCaptured(Exception):
            pass

        with tempfile.TemporaryDirectory(prefix="private-chat signing '") as directory:
            temporary = Path(directory)
            init = None

            def capture(command, cwd, env):
                nonlocal init
                if ":TMessagesProj_App:assembleAfatDebug" in command:
                    init = Path(command[command.index("--init-script") + 1])
                    raise BuildCaptured

            with self.assertRaises(BuildCaptured):
                self.native.android_build(capture, dict(os.environ), temporary, SimpleNamespace(jobs=1))
            self.assertIsNotNone(init)
            fixture = temporary / "fixture"
            fixture.mkdir()
            (fixture / "settings.gradle").write_text("rootProject.name = 'ci-signing-fixture'\n")
            (fixture / "build.gradle").write_text("""
buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:8.6.1' }
}
apply plugin: 'com.android.application'
android {
    namespace 'test.privatechat.signing'
    compileSdk 35
    buildToolsVersion '35.0.0'
    defaultConfig { minSdk 23 }
    flavorDimensions 'minApi'
    productFlavors {
        afat {
            dimension 'minApi'
            ndk { abiFilters 'armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64' }
        }
        full {
            dimension 'minApi'
            ndk { abiFilters 'armeabi-v7a', 'x86_64' }
        }
    }
    signingConfigs {
        debug {
            storeFile file('source-release.keystore')
            storePassword 'source-password'
            keyAlias 'source-alias'
            keyPassword 'source-key-password'
        }
        release {
            storeFile file('source-release.keystore')
            storePassword 'source-password'
            keyAlias 'source-alias'
            keyPassword 'source-key-password'
        }
    }
}
tasks.register('checkCiSigning') {
    doLast {
        def debug = android.signingConfigs.debug
        assert debug.storeFile.canonicalFile == file('../ci-debug.keystore').canonicalFile
        assert debug.storePassword == 'android'
        assert debug.keyAlias == 'androiddebugkey'
        assert debug.keyPassword == 'android'
        def abis = android.productFlavors.getByName('afat').ndk.abiFilters
        assert abis == ['arm64-v8a'] as Set
        def fullAbis = android.productFlavors.getByName('full').ndk.abiFilters
        assert fullAbis == ['armeabi-v7a', 'x86_64'] as Set
        def release = android.signingConfigs.release
        assert release.storeFile.canonicalFile == file('source-release.keystore').canonicalFile
        assert release.storePassword == 'source-password'
        assert release.keyAlias == 'source-alias'
        assert release.keyPassword == 'source-key-password'
    }
}
""", encoding="utf-8")
            result = subprocess.run(
                [str(self.native.ROOT / "android/gradlew"), "--no-daemon", "--console=plain",
                 "--max-workers=1", "--init-script", str(init), "checkCiSigning"],
                cwd=fixture, env=dict(os.environ), text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
