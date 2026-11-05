#!/usr/bin/env python3
"""Docker health check for the isolated local client integration stack."""

import os
import socket
import sys
from pathlib import Path


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


def fail(message):
    print(f"localtest unhealthy: {message}", file=sys.stderr)
    return 1


def check_processes(pid_dir):
    for service in SERVICES:
        pid_file = pid_dir / f"{service}.pid"
        try:
            pid = int(pid_file.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return f"{service} PID file is missing or invalid"
        try:
            os.kill(pid, 0)
        except OSError:
            return f"{service} process {pid} is not running"
    return None


def check_endpoint(label, host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return None
    except OSError as exc:
        return f"{label} endpoint {host}:{port} is unreachable ({exc})"


def main():
    pid_dir = Path(
        os.environ.get("PRIVATECHAT_LOCALTEST_PID_DIR", "/run/privatechat-localtest/pids")
    )
    process_error = check_processes(pid_dir)
    if process_error:
        return fail(process_error)

    kafka_error = check_endpoint(
        "Kafka",
        os.environ.get("PRIVATECHAT_LOCALTEST_KAFKA_HOST", "kafka"),
        int(os.environ.get("PRIVATECHAT_LOCALTEST_KAFKA_PORT", "9092")),
    )
    if kafka_error:
        return fail(kafka_error)

    gateway_error = check_endpoint(
        "client gateway",
        os.environ.get("PRIVATECHAT_LOCALTEST_GATEWAY_HOST", "127.0.0.1"),
        int(os.environ.get("PRIVATECHAT_LOCALTEST_GATEWAY_PORT", "10443")),
    )
    if gateway_error:
        return fail(gateway_error)

    return 0


if __name__ == "__main__":
    sys.exit(main())
