#!/bin/bash
set -euo pipefail

bash "$(dirname "$0")/configure-runtime.sh"
cd /app/bin
./runall-docker.sh
tail -f /dev/null
