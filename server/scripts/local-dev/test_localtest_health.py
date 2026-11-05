import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HEALTH_CHECK = Path(__file__).with_name("check-localtest-health.py")
SERVICES = (
    "idgen",
    "status",
    "authsession",
    "dfs",
    "media",
    "biz",
    "msg",
    "sync",
    "bff",
    "session",
    "gnetway",
)


class LocaltestHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.pid_dir = Path(self.temp_dir.name) / "pids"
        self.pid_dir.mkdir()
        for service in SERVICES:
            (self.pid_dir / f"{service}.pid").write_text(f"{os.getpid()}\n")

    def listener(self):
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        self.addCleanup(listener.close)
        return listener.getsockname()[1]

    def run_health_check(self, kafka_port, gateway_port):
        env = os.environ.copy()
        env.update(
            {
                "PRIVATECHAT_LOCALTEST_PID_DIR": str(self.pid_dir),
                "PRIVATECHAT_LOCALTEST_KAFKA_HOST": "127.0.0.1",
                "PRIVATECHAT_LOCALTEST_KAFKA_PORT": str(kafka_port),
                "PRIVATECHAT_LOCALTEST_GATEWAY_HOST": "127.0.0.1",
                "PRIVATECHAT_LOCALTEST_GATEWAY_PORT": str(gateway_port),
            }
        )
        return subprocess.run(
            [sys.executable, str(HEALTH_CHECK)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )

    def test_unready_kafka_prevents_healthy_status(self):
        result = self.run_health_check(1, self.listener())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("kafka", result.stderr.lower())

    def test_exited_service_prevents_healthy_status(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait(timeout=5)
        (self.pid_dir / "status.pid").write_text(f"{child.pid}\n")

        result = self.run_health_check(self.listener(), self.listener())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status", result.stderr.lower())

    def test_all_services_and_endpoints_ready(self):
        result = self.run_health_check(self.listener(), self.listener())
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
