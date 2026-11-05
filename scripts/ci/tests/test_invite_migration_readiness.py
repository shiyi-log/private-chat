"""Regression coverage for the disposable MySQL startup race."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_CHECK = ROOT / "server/scripts/local-dev/check-invite-participants-migration.sh"


class InviteMigrationReadinessTests(unittest.TestCase):
    def test_socket_only_temporary_server_is_not_treated_as_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            state = temp / "mysql-ready"
            docker = bin_dir / "docker"
            docker.write_text(
                "#!/usr/bin/env python3\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "args = sys.argv[1:]\n"
                "text = ' '.join(args)\n"
                "state = Path(os.environ['FAKE_MYSQL_READY'])\n"
                "if args[0] == 'exec' and 'SELECT 1' in text:\n"
                "    if '--protocol=TCP' in args and '-h127.0.0.1' in args:\n"
                "        if not state.exists():\n"
                "            state.touch()\n"
                "            raise SystemExit(1)\n"
                "    print('1')\n"
                "    raise SystemExit(0)\n"
                "if args[0] == 'exec' and 'CREATE DATABASE' in text and not state.exists():\n"
                "    print(\"ERROR 2002 (HY000): Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock' (2)\", file=sys.stderr)\n"
                "    raise SystemExit(1)\n"
                "if args[0] == 'exec' and 'SELECT CONCAT' in text:\n"
                "    print('1:1:1:1')\n"
            )
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["FAKE_MYSQL_READY"] = str(state)

            result = subprocess.run(
                ["bash", str(MIGRATION_CHECK)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("row data and defaults verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
