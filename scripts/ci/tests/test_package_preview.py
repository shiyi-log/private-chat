"""Release regressions: prevent runtime disclosure and ambiguous preview assets."""
import gzip
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "package_preview.py"


class PreviewPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("package_preview", SCRIPT)
        cls.release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.release)

    def archive(self, entries):
        source = io.BytesIO()
        with tarfile.open(fileobj=source, mode="w") as archive:
            for name, content in entries:
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mtime = 12345
                archive.addfile(info, io.BytesIO(content))
        source.seek(0)
        return source

    def test_source_archive_contains_source_but_excludes_local_secrets_and_runtime(self):
        source = self.archive([
            ("server/go.mod", b"module example\n"),
            ("docs/local-integration.md", b"Setup\n"),
            ("ios/build-system/BUILD.bazel", b"exports_files([])\n"),
            ("server/.env", b"PRIVATE=secret"),
            ("server/.env.example", b"PUBLIC=example"),
            ("server/teamgramd/bin/server_pkcs1.key", b"private"),
            ("android/local.properties", b"PRIVATE_CHAT_API_HASH=secret"),
            ("ios/build-input/configuration-repository/variables.bzl", b"secret"),
            ("integration/otp/outbox/record.json", b"secret"),
            ("toolchains/ios-local-development.json", b"secret"),
            ("desktop/out/Debug/tdata/key_datas", b"secret"),
        ])
        output = io.BytesIO()
        self.release.write_source_archive(source, output, "v0.2.0-preview.1", 1700000000)
        output.seek(0)
        with tarfile.open(fileobj=output, mode="r:gz") as archive:
            names = archive.getnames()
        self.assertEqual(names, [
            "private-chat-v0.2.0-preview.1/docs/local-integration.md",
            "private-chat-v0.2.0-preview.1/ios/build-system/BUILD.bazel",
            "private-chat-v0.2.0-preview.1/server/.env.example",
            "private-chat-v0.2.0-preview.1/server/go.mod",
        ])

    def test_source_archive_preserves_only_required_teamgramd_runtime_scripts(self):
        source = self.archive([
            ("server/teamgramd/bin/config.json", b"{}\n"),
            ("server/teamgramd/bin/killall.sh", b"#!/bin/sh\n"),
            ("server/teamgramd/bin/runall2.sh", b"#!/bin/sh\n"),
            ("server/teamgramd/bin/runall-docker.sh", b"#!/bin/sh\n"),
            ("server/teamgramd/bin/server_pkcs1.key", b"private"),
            ("server/teamgramd/bin/server", b"binary"),
            ("server/teamgramd/bin/unreviewed.txt", b"not required"),
        ])
        output = io.BytesIO()
        self.release.write_source_archive(source, output, "v0.2.0-preview.1", 1700000000)
        output.seek(0)
        with tarfile.open(fileobj=output, mode="r:gz") as archive:
            names = archive.getnames()
        self.assertEqual(names, [
            "private-chat-v0.2.0-preview.1/server/teamgramd/bin/config.json",
            "private-chat-v0.2.0-preview.1/server/teamgramd/bin/killall.sh",
            "private-chat-v0.2.0-preview.1/server/teamgramd/bin/runall-docker.sh",
            "private-chat-v0.2.0-preview.1/server/teamgramd/bin/runall2.sh",
        ])

    def test_preserves_tracked_build_sources_and_fixture_data_but_excludes_generated_outputs(self):
        source = self.archive([
            ("desktop/Telegram/build/prepare/prepare.py", b"source"),
            ("ios/build-system/bazel-rules/rules_xcodeproj/xcodeproj/internal/templates/xcodeproj.bazelrc", b"source"),
            ("ios/bazel-out/arm64-darwin/bin/generated.bzl", b"generated"),
            ("ios/third-party/library/build/CMakeLists.txt", b"source"),
            ("server/pkg/format/testdata/data/sample.json", b"fixture"),
            ("android/TMessagesProj/build/intermediates/output.bin", b"generated"),
            ("android/TMessagesProj/.cxx/output.bin", b"generated"),
            ("server/data/local-integration/outbox.json", b"private"),
            ("Libraries/local/Qt/libQt.a", b"local dependency"),
            ("ThirdParty/local/tool", b"local tool"),
        ])
        output = io.BytesIO()
        self.release.write_source_archive(source, output, "v0.2.0-preview.1", 1)
        output.seek(0)
        with tarfile.open(fileobj=output, mode="r:gz") as archive:
            self.assertEqual(archive.getnames(), [
                "private-chat-v0.2.0-preview.1/desktop/Telegram/build/prepare/prepare.py",
                "private-chat-v0.2.0-preview.1/ios/build-system/bazel-rules/rules_xcodeproj/xcodeproj/internal/templates/xcodeproj.bazelrc",
                "private-chat-v0.2.0-preview.1/ios/third-party/library/build/CMakeLists.txt",
                "private-chat-v0.2.0-preview.1/server/pkg/format/testdata/data/sample.json",
            ])

    def test_source_archive_is_byte_reproducible_despite_input_order_and_metadata(self):
        entries = [("docs/README.md", b"docs\n"), ("server/go.mod", b"module example\n")]
        outputs = []
        for source_entries in (entries, list(reversed(entries))):
            output = io.BytesIO()
            self.release.write_source_archive(self.archive(source_entries), output, "v1.0.0-preview.1", 1700000000)
            outputs.append(output.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(int.from_bytes(outputs[0][4:8], "little"), 0)

    def test_source_archive_fails_if_an_unexpected_file_contains_a_private_key(self):
        source = self.archive([("server/config/sample.pem", b"-----BEGIN RSA PRIVATE KEY-----\nprivate\n")])
        with self.assertRaisesRegex(ValueError, "private key"):
            self.release.write_source_archive(source, io.BytesIO(), "v1.0.0-preview.1", 1700000000)

    def test_source_archive_preserves_only_the_exact_verified_vendor_key_fixture(self):
        name = "android/TMessagesProj/jni/boringssl/crypto/dsa/dsa_test.cc"
        expected_sha256 = "b44576fefea97f0867cab09a77d76fce2bb3c6750ce8dd0a498ac880b3289502"
        fixture = (self.release.ROOT / name).read_bytes()
        self.assertEqual(self.release.hashlib.sha256(fixture).hexdigest(), expected_sha256)

        source = self.archive([(name, fixture)])
        output = io.BytesIO()
        self.release.write_source_archive(source, output, "v1.0.0-preview.1", 1700000000)
        output.seek(0)
        with tarfile.open(fileobj=output, mode="r:gz") as archive:
            self.assertEqual(archive.extractfile(f"private-chat-v1.0.0-preview.1/{name}").read(), fixture)

        changed = self.archive([(name, fixture + b"\n")])
        with self.assertRaisesRegex(ValueError, "private key"):
            self.release.write_source_archive(changed, io.BytesIO(), "v1.0.0-preview.1", 1700000000)

    def test_source_archive_rejects_path_traversal_and_escaping_symlinks(self):
        with self.assertRaises(ValueError):
            self.release.write_source_archive(self.archive([("server/../../leak", b"secret")]), io.BytesIO(), "v1.0.0-preview.1", 1)
        source = io.BytesIO()
        with tarfile.open(fileobj=source, mode="w") as archive:
            info = tarfile.TarInfo("desktop/link")
            info.type = tarfile.SYMTYPE
            info.linkname = "../../outside"
            archive.addfile(info)
        source.seek(0)
        with self.assertRaises(ValueError):
            self.release.write_source_archive(source, io.BytesIO(), "v1.0.0-preview.1", 1)

    def test_bundle_archive_preserves_internal_framework_symlinks_and_rejects_external_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "Private Chat.app"
            (bundle / "Contents" / "Frameworks" / "Kit.framework" / "Versions" / "A").mkdir(parents=True)
            binary = bundle / "Contents" / "Frameworks" / "Kit.framework" / "Versions" / "A" / "Kit"
            binary.write_bytes(b"executable")
            binary.chmod(0o755)
            (binary.parents[2] / "Kit").symlink_to("Versions/A/Kit")
            archive_path = root / "bundle.tar.gz"
            self.release.write_bundle_archive(bundle, archive_path, 1)
            with tarfile.open(archive_path, "r:gz") as archive:
                member = archive.getmember("Private Chat.app/Contents/Frameworks/Kit.framework/Kit")
                self.assertTrue(member.issym())
                self.assertEqual(member.linkname, "Versions/A/Kit")
            (bundle / "outside").symlink_to(root / "private")
            with self.assertRaises(ValueError):
                self.release.write_bundle_archive(bundle, root / "invalid.tar.gz", 1)

    def test_native_provenance_rejects_products_changed_after_the_build(self):
        with tempfile.TemporaryDirectory() as directory:
            product = Path(directory) / "android.apk"
            product.write_bytes(b"changed")
            evidence = {
                "component": "android", "source_commit": "a" * 40,
                "source_dirty": False, "build_exit_code": 0,
                "distribution": "debug-android-preview",
                "artifact_sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            }
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.release.validate_native_provenance(evidence, "android", "a" * 40, product)
            product.write_bytes(b"abc")
            self.release.validate_native_provenance(evidence, "android", "a" * 40, product)
            evidence["source_dirty"] = True
            with self.assertRaisesRegex(ValueError, "clean"):
                self.release.validate_native_provenance(evidence, "android", "a" * 40, product)

    def test_checksums_describe_asset_bytes_and_manifest_labels_simulator(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            asset = output / "preview.apk"
            asset.write_bytes(b"abc")
            records = self.release.write_checksums(output, [asset])
            self.assertEqual((output / "SHA256SUMS").read_text(),
                             "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  preview.apk\n")
            self.assertEqual(records[0]["size_bytes"], 3)
            self.assertEqual(self.release.NATIVE_KINDS["ios"]["distribution"], "unsigned-ios-simulator-preview")

    def test_source_revision_requires_all_components_and_no_unexpanded_gitlinks(self):
        entries = [("100644", name) for name in self.release.REQUIRED_SOURCES]
        self.release.validate_source_tree(entries)
        with self.assertRaisesRegex(ValueError, "missing"):
            self.release.validate_source_tree(entries[:-1])
        with self.assertRaisesRegex(ValueError, "gitlink"):
            self.release.validate_source_tree(entries + [("160000", "ios/submodules/missing")])


if __name__ == "__main__":
    unittest.main()
