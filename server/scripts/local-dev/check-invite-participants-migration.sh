#!/usr/bin/env bash
# Apply the invite-participant migration to an old schema twice in disposable MySQL.
set -euo pipefail
server_dir="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
migration="$server_dir/teamgramd/deploy/sql/migrate-20261105.sql"
check_container="privatechat-invite-migration-check-$$-${RANDOM}"
mysql_password="migration-check-only"

cleanup() {
  docker rm -f "$check_container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "$check_container" --tmpfs /var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD="$mysql_password" mysql:8.0 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci \
  --default-authentication-plugin=mysql_native_password >/dev/null

ready=0
# The image's temporary initialization server accepts socket queries with networking disabled.
for attempt in $(seq 1 90); do
  if docker exec -e MYSQL_PWD="$mysql_password" "$check_container" \
    mysql --protocol=TCP -h127.0.0.1 -uroot --batch --skip-column-names -e "SELECT 1" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  docker logs "$check_container" >&2
  echo "Timed out waiting for disposable MySQL." >&2
  exit 1
fi

docker exec -e MYSQL_PWD="$mysql_password" "$check_container" mysql -uroot -e \
  "CREATE DATABASE teamgram CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"
docker exec -e MYSQL_PWD="$mysql_password" "$check_container" mysql -uroot teamgram -e \
  "CREATE TABLE chat_invite_participants (
     id BIGINT NOT NULL,
     link VARCHAR(32) NOT NULL,
     user_id BIGINT NOT NULL,
     date2 BIGINT NOT NULL,
     deleted TINYINT(1) NOT NULL DEFAULT '0',
     PRIMARY KEY (id)
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
   INSERT INTO chat_invite_participants (id, link, user_id, date2)
   VALUES (7, 'legacy-link', 42, 1730000000);"

for run in 1 2; do
  docker exec -i -e MYSQL_PWD="$mysql_password" "$check_container" \
    mysql -uroot teamgram < "$migration"
done

result="$(docker exec -e MYSQL_PWD="$mysql_password" "$check_container" \
  mysql -uroot --batch --skip-column-names teamgram -e \
  "SELECT CONCAT(COUNT(*), ':', SUM(requested = 0), ':', SUM(approved_by = 0),
                 ':', SUM(id = 7 AND user_id = 42 AND date2 = 1730000000))
   FROM chat_invite_participants;")"
if [[ "$result" != "1:1:1:1" ]]; then
  echo "Migration did not preserve legacy row data and default both columns to zero: $result" >&2
  exit 1
fi

echo "Legacy invite-participant schema migrated twice; row data and defaults verified."
