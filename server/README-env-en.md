# Local Docker Compose Environment

`docker-compose-env.yaml` provides MySQL, Redis, etcd, Kafka, MinIO, and optional logging and monitoring services. It is intended for local development and evaluation, not production: Elasticsearch authentication is disabled, and infrastructure and monitoring ports bind to the local loopback address only.

The server does not include a production SMS verification provider. Its default verifier rejects sign-in code requests, so clients cannot sign in until a real provider is integrated and reviewed.

## Start

Docker Engine and Docker Compose V2 are required. Create `.env` before starting, and generate a different random value for each password:

```bash
cp .env.example .env
openssl rand -hex 32
```

Use separate outputs for `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `MINIO_ROOT_PASSWORD`, and `GRAFANA_ADMIN_PASSWORD`. The default `TEAMGRAM_HOST_BIND_ADDRESS=127.0.0.1` keeps client gateway access local to this machine.

```bash
docker compose -f docker-compose-env.yaml config --quiet
docker compose -f docker-compose-env.yaml up -d
docker compose up -d
docker compose ps
```

Stop containers while preserving data:

```bash
docker compose down
docker compose -f docker-compose-env.yaml down
```

Data is stored under `./data/`. `down` preserves it; back up the data before removing volumes or directories.

## Local Ports

All host mappings bind to `127.0.0.1` by default. The dependency stack also binds Jaeger, Node Exporter, Prometheus, Grafana, Elasticsearch, and Kibana ports locally.

| Service | Host port | Address |
|---------|-----------|---------|
| Client gateway (TCP MTProto) | 10443 | `127.0.0.1:10443` |
| Client gateway (WebSocket) | 11443 | `127.0.0.1:11443` |
| Client gateway (TCP) | 5222 | `127.0.0.1:5222` |
| MySQL | 13306 | `127.0.0.1:13306` |
| Redis | 16380 | `127.0.0.1:16380` |
| etcd | 12379, 12380 | `127.0.0.1:12379`, `127.0.0.1:12380` |
| Kafka | 19092, 19094 | `127.0.0.1:19092`, `127.0.0.1:19094` |
| MinIO API / Console | 19000, 19001 | `http://127.0.0.1:19000`, `http://127.0.0.1:19001` |
| Jaeger UI | 16686 | `http://127.0.0.1:16686` |
| Prometheus | 9090 | `http://127.0.0.1:9090` |
| Grafana | 13001 | `http://127.0.0.1:13001` |
| Elasticsearch | 9200, 9300 | `127.0.0.1:9200`, `127.0.0.1:9300` |
| Kibana | 5601 | `http://127.0.0.1:5601` |

## LAN Clients

To connect from another device, set `TEAMGRAM_HOST_BIND_ADDRESS` in `.env` to the server's private interface IP and allow only the required client gateway ports through the firewall. Do not publish internal RPC, database, cache, object storage, or monitoring ports, and never expose Elasticsearch directly to the internet.

Client binaries and a first-party chat interface are not included in this repository. Configuration patches for upstream clients are documented under [`clients/`](clients/); build and validate each client separately.
