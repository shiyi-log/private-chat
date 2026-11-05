"""Server CI mode contracts without running Go builds or Docker workloads."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHECK_SERVER = ROOT / "scripts/ci/check-server.sh"


class CheckServerTests(unittest.TestCase):
    def run_mode(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            call_log = temp / "calls.log"
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            go = bin_dir / "go"
            go.write_text("#!/bin/sh\nprintf 'go %s\\n' \"$*\" >> \"$CALL_LOG\"\n")
            go.chmod(0o755)
            docker = bin_dir / "docker"
            docker.write_text(
                "#!/bin/sh\n"
                "printf 'docker %s\\n' \"$*\" >> \"$CALL_LOG\"\n"
                "case \" $* \" in\n"
                "  *'mysqladmin -uroot ping'*) exit 0 ;;\n"
                "  *'--skip-column-names teamgram -e'*) printf '1:1:1:1\\n' ;;\n"
                "esac\n"
            )
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["CALL_LOG"] = str(call_log)
            result = subprocess.run(
                ["bash", str(CHECK_SERVER), mode],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return call_log.read_text().splitlines()

    def test_full_mode_runs_disposable_sql_migration_check(self):
        calls = self.run_mode("full")
        self.assertTrue(any(call.startswith("docker run ") for call in calls))

    def test_affected_mode_does_not_start_docker(self):
        calls = self.run_mode("affected")
        self.assertFalse(any(call.startswith("docker ") for call in calls))


if __name__ == "__main__":
    unittest.main()
