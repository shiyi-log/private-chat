"""Integration coverage for history-free public source snapshots."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/ci/public_snapshot.py"
REQUIRED = {
    "server/go.mod": b"module example/server\n",
    "desktop/CMakeLists.txt": b"project(example)\n",
    "android/settings.gradle": b"rootProject.name = 'example'\n",
    "ios/versions.json": b'{"xcode":"26.2"}\n',
    "docs/README.md": b"# docs\n",
}


class PublicSnapshotTests(unittest.TestCase):
    def git(self, repository, *args, env=None):
        return subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            capture_output=True,
            env=env,
        ).stdout

    def write(self, repository, name, content):
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def make_repository(self, repository):
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        self.git(repository, "config", "user.name", "Snapshot Test")
        self.git(repository, "config", "user.email", "snapshot@example.invalid")
        for name, content in REQUIRED.items():
            self.write(repository, name, content)
        self.write(repository, "README.md", b"initial README\n")
        self.write(repository, "server/teamgramd/bin/server_pkcs1.key", b"legacy key bytes\n")
        self.write(repository, "outside/private.txt", b"outside source\n")
        self.git(repository, "add", "-A")
        self.git(repository, "commit", "-qm", "legacy history contains a tracked server key")
        return self.git(repository, "rev-parse", "HEAD").decode().strip()

    def invoke(self, repository, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repository", str(repository), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_snapshot_has_no_parent_filters_legacy_key_and_preserves_git_state(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            old_head = self.make_repository(repository)

            self.write(repository, "README.md", b"dirty README included in snapshot\n")
            self.write(repository, "docs/new-guide.md", b"new source included\n")
            self.write(repository, "docs/staged.md", b"staged version\n")
            self.git(repository, "add", "docs/staged.md")
            self.write(repository, "docs/staged.md", b"dirty working tree version\n")
            head_before = self.git(repository, "rev-parse", "HEAD")
            index_before = self.git(repository, "ls-files", "--stage", "-z")
            status_before = self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")

            result = self.invoke(repository, "--message", "Public snapshot test")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), result.stdout.strip().splitlines()[0])
            snapshot = result.stdout.strip()
            self.assertRegex(snapshot, r"^[0-9a-f]{40,64}$")
            self.assertEqual(self.git(repository, "rev-list", "--parents", "-n", "1", snapshot).decode().strip(), snapshot)
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").decode().strip(), old_head)
            self.assertEqual(self.git(repository, "rev-parse", "HEAD"), head_before)
            self.assertEqual(self.git(repository, "ls-files", "--stage", "-z"), index_before)
            self.assertEqual(self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"), status_before)

            entries = self.git(repository, "ls-tree", "-r", "--name-only", "-z", snapshot).decode().split("\0")
            entries = {name for name in entries if name}
            self.assertTrue(set(REQUIRED).issubset(entries))
            self.assertIn("README.md", entries)
            self.assertIn("docs/new-guide.md", entries)
            self.assertIn("docs/staged.md", entries)
            self.assertNotIn("server/teamgramd/bin/server_pkcs1.key", entries)
            self.assertNotIn("outside/private.txt", entries)
            self.assertEqual(self.git(repository, "show", f"{snapshot}:README.md"), b"dirty README included in snapshot\n")
            self.assertEqual(self.git(repository, "show", f"{snapshot}:docs/staged.md"), b"dirty working tree version\n")
            self.assertEqual(self.git(repository, "show", f"{old_head}:server/teamgramd/bin/server_pkcs1.key"), b"legacy key bytes\n")

    def test_snapshot_includes_worktree_changes_for_index_flagged_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            for flag, content in (
                ("--assume-unchanged", b"assume-unchanged working tree content\n"),
                ("--skip-worktree", b"skip-worktree working tree content\n"),
            ):
                with self.subTest(flag=flag):
                    self.git(repository, "update-index", flag, "README.md")
                    self.write(repository, "README.md", content)
                    index_path = Path(
                        self.git(repository, "rev-parse", "--git-path", "index").decode().strip()
                    )
                    if not index_path.is_absolute():
                        index_path = repository / index_path
                    index_bytes_before = index_path.read_bytes()
                    status_before = self.git(
                        repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"
                    )

                    result = self.invoke(repository)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        self.git(repository, "show", f"{result.stdout.strip()}:README.md"),
                        content,
                    )
                    self.assertEqual(index_path.read_bytes(), index_bytes_before)
                    self.assertEqual(
                        self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
                        status_before,
                    )

    def test_snapshot_excludes_conflict_copy_go_files_without_changing_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            duplicate = "server/pkg/goffmpeg/tests/transcoding_test 2.go"
            self.write(repository, duplicate, b"accidental editor conflict copy\n")
            status_before = self.git(
                repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"
            )

            result = self.invoke(repository)

            self.assertEqual(result.returncode, 0, result.stderr)
            entries = self.git(
                repository, "ls-tree", "-r", "--name-only", "-z", result.stdout.strip()
            ).decode().split("\0")
            self.assertNotIn(duplicate, entries)
            self.assertTrue((repository / duplicate).is_file())
            self.assertEqual(
                self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
                status_before,
            )

    def test_snapshot_rejects_unexpected_private_key_without_mutating_git_state(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            self.write(repository, "docs/unexpected.pem", b"-----BEGIN PRIVATE KEY-----\nnot public\n")
            head_before = self.git(repository, "rev-parse", "HEAD")
            index_before = self.git(repository, "ls-files", "--stage", "-z")
            status_before = self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")

            result = self.invoke(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("private key", result.stderr.lower())
            self.assertEqual(result.stdout, "")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD"), head_before)
            self.assertEqual(self.git(repository, "ls-files", "--stage", "-z"), index_before)
            self.assertEqual(self.git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"), status_before)

    def test_snapshot_rejects_missing_components(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            self.git(repository, "rm", "-q", "ios/versions.json")
            self.git(repository, "commit", "-qm", "remove required source")
            result = self.invoke(repository)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing", result.stderr.lower())

    def test_snapshot_rejects_gitlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)

            nested = repository / "docs/vendor"
            nested.mkdir()
            subprocess.run(["git", "init", "-q", str(nested)], check=True)
            self.git(nested, "config", "user.name", "Nested Snapshot Test")
            self.git(nested, "config", "user.email", "nested@example.invalid")
            self.write(nested, "README.md", b"nested source\n")
            self.git(nested, "add", "-A")
            self.git(nested, "commit", "-qm", "nested source")
            self.git(repository, "add", "docs/vendor")
            self.git(repository, "commit", "-qm", "add an unexpanded source gitlink")

            result = self.invoke(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gitlink", result.stderr.lower())

    def test_cli_only_emits_commit_sha_on_success(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            result = self.invoke(repository)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"^[0-9a-f]{40,64}\n$")

    def test_snapshot_preserves_internal_symlinks_and_rejects_external_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            self.write(repository, "docs/guide.md", b"source guide\n")
            (repository / "docs/current.md").symlink_to("guide.md")

            result = self.invoke(repository)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                self.git(repository, "show", f"{result.stdout.strip()}:docs/current.md"),
                b"guide.md",
            )
            (repository / "docs/external.md").symlink_to("../../outside/private.txt")

            rejected = self.invoke(repository)

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("symlink", rejected.stderr.lower())
            self.assertEqual(rejected.stdout, "")

    def test_streaming_scan_handles_pem_headers_and_non_headers_at_chunk_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "fixture"
            repository.mkdir()
            self.make_repository(repository)
            header = b"-----BEGIN PRIVATE KEY-----"
            block_size = 1024 * 1024
            non_header = b"x" * (block_size - len(header)) + header + b"continued text\n"
            self.write(repository, "docs/large.txt", non_header)

            accepted = self.invoke(repository)

            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            split_header = b"x" * (block_size - 12) + b"\n" + header + b"\r\nsecret\n"
            self.write(repository, "docs/large.txt", split_header)

            rejected = self.invoke(repository)

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("private key", rejected.stderr.lower())
            self.assertEqual(rejected.stdout, "")


if __name__ == "__main__":
    unittest.main()
