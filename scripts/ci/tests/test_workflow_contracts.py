"""Security boundaries for manually dispatched workflows."""
import os
import re
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class WorkflowContractTests(unittest.TestCase):
    def test_apple_native_workflow_rejects_non_main_refs_before_self_hosted_job(self):
        workflow = (ROOT / ".github/workflows/native-preview.yml").read_text(encoding="utf-8")
        validation_job = re.search(
            r"(?ms)^  validate:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", workflow
        )
        self.assertIsNotNone(validation_job, "a hosted validation job must run before native builds")
        self.assertRegex(validation_job["body"], r"(?m)^    runs-on: ubuntu-latest$")
        validate = re.search(
            r"(?ms)^      - name: Validate trusted source branch\n"
            r"        shell: bash\n        run: \|\n(?P<script>(?:          .*\n)+)",
            validation_job["body"],
        )
        self.assertIsNotNone(validate, "a hosted branch validation step must run before native builds")

        for ref, expected in (
            ("refs/heads/main", 0),
            ("refs/heads/feature", 1),
            ("refs/tags/v0.2.0-preview.1", 1),
            ("", 1),
        ):
            with self.subTest(ref=ref):
                result = subprocess.run(
                    ["bash", "-e", "-u", "-o", "pipefail", "-c", textwrap.dedent(validate["script"])],
                    env={**os.environ, "GITHUB_REF": ref},
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, expected, result.stderr)

        native = re.search(r"(?ms)^  native:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", workflow)
        self.assertIsNotNone(native, "the native self-hosted job must be present")
        self.assertRegex(native["body"], r"(?m)^    needs: validate$")


if __name__ == "__main__":
    unittest.main()
