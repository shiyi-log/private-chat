#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="$ROOT/data/local-dev"
LOG_DIR="$ROOT/teamgramd/logs"
KAFKA_CONFIG="$DATA_DIR/kafka-server.properties"
KAFKA_LOG="$LOG_DIR/kafka-host.log"
KAFKA_CLUSTER_ID="MkU3OEVBNTcwNTJENDM2Qk"
MINIO_LOG="$LOG_DIR/minio-host.log"
MINIO_DATA="$DATA_DIR/minio"
KAFKA_HOST_PORT=9092
KAFKA_DOCKER_PORT=19092

mkdir -p "$DATA_DIR/kafka" "$MINIO_DATA" "$LOG_DIR"

cat > "$KAFKA_CONFIG" <<CFG
process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=localhost:9093
listeners=PLAINTEXT_HOST://0.0.0.0:${KAFKA_HOST_PORT},PLAINTEXT_DOCKER://0.0.0.0:${KAFKA_DOCKER_PORT},CONTROLLER://127.0.0.1:9093
advertised.listeners=PLAINTEXT_HOST://localhost:${KAFKA_HOST_PORT},PLAINTEXT_DOCKER://host.docker.internal:${KAFKA_DOCKER_PORT},CONTROLLER://127.0.0.1:9093
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,PLAINTEXT_DOCKER:PLAINTEXT
inter.broker.listener.name=PLAINTEXT_HOST
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=$DATA_DIR/kafka/kraft-combined-logs
num.partitions=1
num.recovery.threads.per.data.dir=2
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
CFG

if [ ! -f "$DATA_DIR/kafka/kraft-combined-logs/meta.properties" ]; then
  kafka-storage format --standalone -t "$KAFKA_CLUSTER_ID" -c "$KAFKA_CONFIG" >/dev/null
fi

if ! lsof -nP -iTCP:${KAFKA_HOST_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  nohup kafka-server-start "$KAFKA_CONFIG" >> "$KAFKA_LOG" 2>&1 &
fi

if ! lsof -nP -iTCP:9000 -sTCP:LISTEN >/dev/null 2>&1; then
  MINIO_ROOT_USER=minio MINIO_ROOT_PASSWORD=miniostorage \
    nohup minio server "$MINIO_DATA" --address ":9000" --console-address ":9001" >> "$MINIO_LOG" 2>&1 &
fi

for _ in $(seq 1 60); do
  if kafka-topics --bootstrap-server localhost:${KAFKA_HOST_PORT} --list >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:9000/minio/health/live >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

kafka-topics --bootstrap-server localhost:${KAFKA_HOST_PORT} --create --if-not-exists --topic Inbox-T --partitions 1 --replication-factor 1 >/dev/null
kafka-topics --bootstrap-server localhost:${KAFKA_HOST_PORT} --create --if-not-exists --topic Sync-T --partitions 1 --replication-factor 1 >/dev/null
kafka-topics --bootstrap-server localhost:${KAFKA_HOST_PORT} --create --if-not-exists --topic teamgram-log --partitions 1 --replication-factor 1 >/dev/null

if ! command -v mc >/dev/null 2>&1; then
  echo "缺少 mc 命令，请先安装 minio/mc。" >&2
  exit 1
fi

mc alias set local http://127.0.0.1:9000 minio miniostorage >/dev/null
for bucket in documents encryptedfiles photos videos; do
  mc mb "local/$bucket" --ignore-existing >/dev/null
done

echo "本机 Kafka 和 MinIO 已启动并完成初始化。"
