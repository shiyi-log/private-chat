#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
config_dir="$temp_dir/etc2"
mkdir -p "$config_dir"

for name in authsession biz dfs media msg sync; do
	cp "$repo_root/teamgramd/etc2/$name.yaml" "$config_dir/$name.yaml"
done

MYSQL_URI='teamgram:0123456789abcdef@tcp(mysql:3306)/teamgram?charset=utf8mb4&parseTime=true'
MINIO_KEY='minio'
MINIO_SECRET='abcdef0123456789'
CONFIG_DIR="$config_dir" MYSQL_URI="$MYSQL_URI" MINIO_KEY="$MINIO_KEY" MINIO_SECRET="$MINIO_SECRET" \
	bash "$repo_root/teamgramd/docker/configure-runtime.sh"

for name in authsession biz media msg sync; do
	grep -Fq "DSN: $MYSQL_URI" "$config_dir/$name.yaml"
done
grep -Fq "AccessKeyID: $MINIO_KEY" "$config_dir/dfs.yaml"
grep -Fq "SecretAccessKey: $MINIO_SECRET" "$config_dir/dfs.yaml"
! grep -R -E 'teamgram:teamgram|SecretAccessKey: miniostorage' "$config_dir"
