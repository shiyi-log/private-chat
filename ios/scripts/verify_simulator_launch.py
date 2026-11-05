#!/usr/bin/env python3
"""Verify that an installed simulator app survives UIKit launch and activation."""
import argparse
import os
import re
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("simulator")
parser.add_argument("bundle_id")
parser.add_argument("--seconds", type=float, default=10)
args = parser.parse_args()
subprocess.run(["xcrun", "simctl", "terminate", args.simulator, args.bundle_id], capture_output=True)
result = subprocess.run(["xcrun", "simctl", "launch", args.simulator, args.bundle_id], text=True, capture_output=True)
match = re.search(r": (\d+)\s*$", result.stdout)
if result.returncode or not match:
    sys.exit(f"FAIL: simctl could not launch {args.bundle_id}: {result.stderr.strip()}")
pid = int(match.group(1))
deadline = time.monotonic() + args.seconds
while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        sys.exit(f"FAIL: {args.bundle_id} exited during UIKit launch (pid {pid})")
    time.sleep(0.25)
print(f"PASS: {args.bundle_id} remained running for {args.seconds:g}s after launch (pid {pid})")
