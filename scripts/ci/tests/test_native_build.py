"""Failure contracts for native build evidence, without invoking native toolchains."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
