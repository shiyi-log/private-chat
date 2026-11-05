#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root/server"
mode="${1:-affected}"
case "$mode" in
  affected)
    packages=(
      ./pkg/localconfig
      ./pkg/code/...
      ./pkg/mtprotocompat
      ./app/bff/configuration/internal/core
      ./app/bff/configuration/internal/svc
      ./app/bff/account/internal/server/grpc/service
      ./app/bff/messages/internal/server/grpc/service
      ./app/bff/chatinvites/internal/server/grpc/service
    )
    go test -count=1 "${packages[@]}"
    go test -count=1 -tags privatechat_localtest "${packages[@]}"
    go build ./...
    go build -tags privatechat_localtest ./...
    ;;
  full)
    bash scripts/local-dev/check-invite-participants-migration.sh
    go test -count=1 ./...
    go test -count=1 -tags privatechat_localtest ./...
    ;;
  *)
    printf 'Usage: %s [affected|full]\n' "$0" >&2
    exit 2
    ;;
esac
