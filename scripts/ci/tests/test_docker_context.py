"""Docker build-context regressions for private runtime material."""
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOCKERIGNORE = ROOT / "server/.dockerignore"
PRIVATE_KEY = "teamgramd/bin/server_pkcs1.key"
LEGACY_NEGATIONS = (
    "!teamgramd/bin/server_pkcs1.key\n",
    "!teamgramd/bin/*\n",
)


@unittest.skipUnless(shutil.which("docker"), "Docker CLI is required")
class DockerContextTests(unittest.TestCase):
    def build_key_copy(self, directory, ignore_rules):
        context = Path(directory)
        key = context / PRIVATE_KEY
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_bytes(b"private-key sentinel")
        (context / ".dockerignore").write_text(ignore_rules)
        (context / "Dockerfile.context-test").write_text(
            "FROM scratch\n"
            f"COPY {PRIVATE_KEY} /key\n"
        )
        tag = f"private-chat-context-test:{uuid.uuid4().hex}"
        result = subprocess.run(
            ["docker", "build", "--quiet", "--file", str(context / "Dockerfile.context-test"), "--tag", tag, str(context)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            subprocess.run(["docker", "image", "rm", "--force", tag], capture_output=True, check=False)
        return result

    def test_nested_legacy_negations_cannot_reinclude_the_server_private_key(self):
        current_rules = DOCKERIGNORE.read_text()

        for negation in LEGACY_NEGATIONS:
            with self.subTest(negation=negation.strip()), tempfile.TemporaryDirectory() as directory:
                old_rules = f"teamgramd/bin\n{negation}"
                result = self.build_key_copy(directory, old_rules)
                self.assertEqual(result.returncode, 0, result.stderr)

        with tempfile.TemporaryDirectory() as directory:
            result = self.build_key_copy(directory, current_rules)
            self.assertNotEqual(result.returncode, 0, "the ignored private key was available to Docker COPY")
            self.assertRegex(result.stderr.lower(), r"not found|excluded|no such file")


if __name__ == "__main__":
    unittest.main()
