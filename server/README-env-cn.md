# Docker Compose 本地环境

`docker-compose-env.yaml` 提供 MySQL、Redis、etcd、Kafka、MinIO 和可选的日志、监控组件。此配置用于本地开发与验收，不是生产部署模板：Elasticsearch 未启用认证，所有基础设施和监控端口仅绑定到本机回环地址。

服务端目前没有生产可用的短信验证码实现。默认配置会拒绝登录验证码请求；在接入并审查真实短信服务前，客户端无法登录。

## 启动

需要 Docker Engine 和 Docker Compose V2。首次启动前创建 `.env`，并为四个密码分别生成不同的随机值：

```bash
cp .env.example .env
openssl rand -hex 32
```

将命令输出分别填入 `MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD`、`MINIO_ROOT_PASSWORD` 和 `GRAFANA_ADMIN_PASSWORD`。每项都要使用独立值。默认 `TEAMGRAM_HOST_BIND_ADDRESS=127.0.0.1`，只允许本机访问客户端网关。

```bash
docker compose -f docker-compose-env.yaml config --quiet
docker compose -f docker-compose-env.yaml up -d
docker compose up -d
docker compose ps
```

停止容器但保留数据：

```bash
docker compose down
docker compose -f docker-compose-env.yaml down
```

数据保存在 `./data/`。执行 `down` 不会删除这些数据；删除卷或目录前先完成备份。

## 本机端口

所有宿主机映射默认绑定 `127.0.0.1`。依赖栈还会将 Jaeger、Node Exporter、Prometheus、Grafana、Elasticsearch 和 Kibana 的端口绑定到本机。

| 服务 | 宿主机端口 | 地址 |
|------|------------|------|
| 客户端网关（TCP MTProto） | 10443 | `127.0.0.1:10443` |
| 客户端网关（WebSocket） | 11443 | `127.0.0.1:11443` |
| 客户端网关（TCP） | 5222 | `127.0.0.1:5222` |
| MySQL | 13306 | `127.0.0.1:13306` |
| Redis | 16380 | `127.0.0.1:16380` |
| etcd | 12379、12380 | `127.0.0.1:12379`、`127.0.0.1:12380` |
| Kafka | 19092、19094 | `127.0.0.1:19092`、`127.0.0.1:19094` |
| MinIO API / Console | 19000、19001 | `http://127.0.0.1:19000`、`http://127.0.0.1:19001` |
| Jaeger UI | 16686 | `http://127.0.0.1:16686` |
| Prometheus | 9090 | `http://127.0.0.1:9090` |
| Grafana | 13001 | `http://127.0.0.1:13001` |
| Elasticsearch | 9200、9300 | `127.0.0.1:9200`、`127.0.0.1:9300` |
| Kibana | 5601 | `http://127.0.0.1:5601` |

## 局域网客户端

如需从其他设备连接，将 `.env` 中的 `TEAMGRAM_HOST_BIND_ADDRESS` 改为服务器的内网网卡 IP，并只在防火墙中开放客户端实际需要的网关端口。不要发布内部 RPC、数据库、缓存、对象存储或监控端口，也不要直接将 Elasticsearch 暴露到互联网。

客户端二进制和自研聊天界面不包含在本仓库中。上游客户端的配置补丁见 [`clients/`](clients/)；各客户端需单独构建和验证。
