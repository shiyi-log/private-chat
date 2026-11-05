#!/usr/bin/env bash
# Verify every initialization SQL file against a disposable MySQL with no host ports.
set -euo pipefail
server_dir="$(cd "$(dirname "$0")/../.." && pwd)"
check_container="privatechat-sql-check-$$-${RANDOM}"
cleanup() {
  docker rm -f "$check_container" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker run -d --name "$check_container" --env-file "$server_dir/.env" \
  --tmpfs /var/lib/mysql \
  -v "$server_dir/teamgramd/deploy/sql:/docker-entrypoint-initdb.d:ro" \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci \
  --default-authentication-plugin=mysql_native_password >/dev/null
for attempt in $(seq 1 90); do
  init_log="$(docker logs "$check_container" 2>&1)"
  if [[ "$init_log" == *"[ERROR]"* || "$init_log" == *"ERROR "* ]]; then
    printf '%s\n' "$init_log" >&2
    exit 1
  fi
  if [[ "$init_log" == *"MySQL init process done. Ready for start up."* ]] && \
     docker exec "$check_container" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqladmin -uroot ping' >/dev/null 2>&1; then
    docker exec "$check_container" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot teamgram -e "SELECT requested, approved_by FROM chat_invite_participants LIMIT 0; SELECT rank2 FROM chat_participants LIMIT 0; SELECT COUNT(*) AS system_user_count FROM users WHERE id=777000; SELECT COUNT(*) AS tables_initialized FROM information_schema.tables WHERE table_schema=\"teamgram\";"'
    echo "All initialization SQL files completed successfully."
    exit 0
  fi
  sleep 1
done
docker logs "$check_container" >&2
echo "Timed out waiting for initialization SQL." >&2
exit 1
