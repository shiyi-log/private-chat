#!/usr/bin/env bash
set -euo pipefail

config_dir="${CONFIG_DIR:-/app/etc2}"
: "${MYSQL_URI:?MYSQL_URI is required}"
: "${MINIO_KEY:?MINIO_KEY is required}"
: "${MINIO_SECRET:?MINIO_SECRET is required}"

escape_sed_replacement() {
	printf '%s' "$1" | sed 's/[\\&|]/\\&/g'
}

mysql_uri="$(escape_sed_replacement "$MYSQL_URI")"
minio_key="$(escape_sed_replacement "$MINIO_KEY")"
minio_secret="$(escape_sed_replacement "$MINIO_SECRET")"

for config in "$config_dir"/*.yaml; do
	[ -f "$config" ] || continue
	tmp_file="${config}.tmp"
	sed \
		-e "s|teamgram:teamgram@tcp(mysql:3306)/teamgram?charset=utf8mb4&parseTime=true|$mysql_uri|g" \
		-e "s|AccessKeyID: minio$|AccessKeyID: $minio_key|g" \
		-e "s|SecretAccessKey: miniostorage$|SecretAccessKey: $minio_secret|g" \
		"$config" > "$tmp_file"
	mv "$tmp_file" "$config"
done
