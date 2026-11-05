#!/usr/bin/env python3
"""Exercise the same Gradle credential loader used by the Android library."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
GRADLE = os.environ.get("PRIVATE_CHAT_GRADLE", str(ROOT / "gradlew"))
FAKE_HASH = "0123456789abcdef0123456789abcdef"
OTHER_HASH = "abcdef0123456789abcdef0123456789"


class PrivateChatApiConfigTests(unittest.TestCase):
    def run_config(self, *, environment=None, properties=""):
        env = os.environ.copy()
        env.pop("PRIVATE_CHAT_API_ID", None)
        env.pop("PRIVATE_CHAT_API_HASH", None)
        env.update(environment or {})
        with tempfile.TemporaryDirectory(prefix="private-chat-api-test-") as directory:
            root = Path(directory)
            (root / "settings.gradle").write_text("rootProject.name = 'api-config-test'\n")
            (root / "local.properties").write_text(properties)
            loader = str(ROOT / "gradle/private-chat-api.gradle").replace("'", "\\'")
            (root / "build.gradle").write_text(
                f"apply from: '{loader}'\n"
                "def credentials = privateChatApiConfig()\n"
                "tasks.register('showApiConfig') { doLast {\n"
                "    println('apiId=' + credentials.apiId)\n"
                "    println('apiHash=' + credentials.apiHash)\n"
                "} }\n"
            )
            return subprocess.run(
                [GRADLE, "--offline", "--console=plain", "--quiet", "showApiConfig"],
                cwd=root, env=env, text=True, capture_output=True,
            )

    def test_reads_operator_credentials_from_environment(self):
        result = self.run_config(environment={
            "PRIVATE_CHAT_API_ID": "123456", "PRIVATE_CHAT_API_HASH": FAKE_HASH,
        })
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("apiId=123456", result.stdout)
        self.assertIn("apiHash=" + FAKE_HASH, result.stdout)

    def test_reads_local_properties_when_environment_is_absent(self):
        result = self.run_config(properties=(
            "PRIVATE_CHAT_API_ID=456789\nPRIVATE_CHAT_API_HASH=" + FAKE_HASH + "\n"
        ))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("apiId=456789", result.stdout)
        self.assertIn("apiHash=" + FAKE_HASH, result.stdout)

    def test_environment_overrides_local_properties(self):
        result = self.run_config(
            properties="PRIVATE_CHAT_API_ID=456789\nPRIVATE_CHAT_API_HASH=" + OTHER_HASH + "\n",
            environment={"PRIVATE_CHAT_API_ID": "123456", "PRIVATE_CHAT_API_HASH": FAKE_HASH},
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("apiId=123456", result.stdout)
        self.assertIn("apiHash=" + FAKE_HASH, result.stdout)
        self.assertNotIn(OTHER_HASH, result.stdout)

    def test_missing_credentials_stop_configuration_without_disclosing_the_other_value(self):
        result = self.run_config(environment={"PRIVATE_CHAT_API_HASH": FAKE_HASH})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("PRIVATE_CHAT_API_ID", result.stdout + result.stderr)
        self.assertNotIn(FAKE_HASH, result.stdout + result.stderr)

    def test_rejects_invalid_values_without_echoing_them(self):
        for key, invalid in (("PRIVATE_CHAT_API_ID", "0"),
                             ("PRIVATE_CHAT_API_ID", "2147483648"),
                             ("PRIVATE_CHAT_API_HASH", "invalid-private-hash"),
                             ("PRIVATE_CHAT_API_HASH", "")):
            with self.subTest(key=key, invalid=invalid):
                environment = {"PRIVATE_CHAT_API_ID": "123456", "PRIVATE_CHAT_API_HASH": FAKE_HASH}
                environment[key] = invalid
                result = self.run_config(environment=environment)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(key, result.stdout + result.stderr)
                if invalid == "invalid-private-hash":
                    self.assertNotIn(invalid, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
