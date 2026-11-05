#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
python3 desktop/scripts/verify_private_chat_desktop_config.py
python3 android/scripts/verify_private_chat_android_config.py
python3 ios/scripts/verify_private_chat_ios_config.py
python3 -m unittest discover -s docs/scripts/tests -v
python3 -m unittest discover -s scripts/ci/tests -v
