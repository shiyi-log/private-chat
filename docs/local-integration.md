# 五组件本地联调

本说明针对统一仓库中的 `server`、`desktop`、`android`、`ios`、`docs` 五个组件。Desktop 在当前 Mac 上构建 macOS 客户端，Android 和 iOS 使用本机模拟器。本次范围不额外要求构建 Windows 或 Linux 客户端。下文的 `toolchains` 和 `integration` 均位于统一仓库根目录，属于本地工具和验收记录。

## 当前验收记录（2026-11-05）

| 组件 | 当前机器上的证据 | 尚待完成 |
| --- | --- | --- |
| Server | 独立 Compose 栈已初始化；两账号协议登录、双向文本及文件字节/SHA-256 烟测通过；已升级 proto v0.227.0，匿名 Config 探针覆盖 layer 224/225/227；本地全量 Go 测试在默认与 `privatechat_localtest` 两种模式下通过；Android/iOS 原生互通通过；公开 CI 的 affected 测试与两种构建通过 | 公开 CI 的全量 Go suite 因 `server/pkg/goffmpeg/tests/transcoding_test 2.go` 中重复测试声明失败，修复待复验；Desktop 原生客户端登录及与移动端的消息/附件互通；持续运行检查 |
| Android | ARM64 Debug APK 已构建、安装和启动；静态配置 481/481、API identity loader 测试 5/5；模拟器已登录 Local Smoke 1，与 iOS 双向收发原生文本及附件；iOS→Android 下载文件 65 字节，SHA-256 `728ae30410c49f096f0b5eb71b3473f7c81e80e242c7b3e9bb470e102b5b0110`，并已用系统 HTML Viewer 打开 | 公开 CI 的 Android job 在安装 SDK 阶段因 `sdkmanager: command not found` 失败，APK 构建未运行；与 Desktop 原生客户端联合验收 |
| Desktop | macOS Debug App 已完成 x86_64+arm64 构建；含产物的静态配置验证 304/304；同签名缓存克隆严格验签通过 | 登录尚未完成；原生界面文本及附件互通尚未验证 |
| iOS | ARM64 模拟器 Debug App 的 scene-v6 构建、安装成功；静态配置 457/457；启动存活检查通过 15 秒；已登录 Local Smoke 2，与 Android 双向收发原生文本及附件；Android→iOS 下载文件 69 字节，SHA-256 `484403719257afc8d8db636aa9946d8344a397414c78aec67f00cd159a3e879c`，并用原生预览打开 | 与 Desktop 原生客户端联合验收；签名分发不在本地模拟器验收范围内 |
| Docs / CI/CD | 公开快照 `21c76203` 已推送到 `main`；CI 的静态配置/契约和 server affected job 通过 | CI 的 Server complete Go suite、Android job 和 Required suite gates 失败；没有候选 Release 或公开预览 |

协议烟测已通过服务端核心链路，但它使用两个内存会话，不能替代原生客户端界面验收。Android 与 iOS 的双向文本及附件互通已在原生客户端完成；这项结果不覆盖 Desktop。

Desktop 尚未登录，原生消息和附件互通未验收，因此五个组件的本地联调仍未全部打通。公开快照 `21c76203ba0379bca3f1bf6ba823a0488bad1d89` 已进入 `main`；[CI run 42012475721](https://github.com/shiyi-log/private-chat/actions/runs/42012475721) 中静态配置/契约和 server affected job 通过，Server complete Go suite 因重复测试声明失败，Android job 因找不到 `sdkmanager` 而未进入 APK 构建，Required suite gates 失败。CI 修复仍待复验；尚无候选 Release 或公开预览发布。

## 服务端

本地联调显式使用 `privatechat_localtest` 构建标签。普通构建仍禁用默认验证码提供方。本地标签还要求 `PRIVATECHAT_LOCALTEST=1`、电话号码白名单和绝对路径 OTP outbox；验证码随机生成，绑定具体登录事务并有过期时间，不使用固定验证码，不发送真实短信。

本机使用独立 Compose 项目 `privatechat-local` 和 `server/data/local-integration` 数据目录。服务端网关仅发布 `127.0.0.1:10443`、`127.0.0.1:5222`、`127.0.0.1:11443`，数据库和内部 RPC 不发布到宿主机。

首次准备时，在 `server/.env` 设置 `.env.example` 要求的独立密码。不要覆盖已有 `.env` 或数据目录。本地镜像依赖 `private-chat-server:v0.1.15-preview.1`；如果本机不存在该镜像，先在 `server` 中执行：

```sh
docker build -t private-chat-server:v0.1.15-preview.1 .
```

在 `server` 中启动当前核心栈：

```sh
docker compose -p privatechat-local \
  -f docker-compose-env.yaml -f docker-compose.yaml -f docker-compose.local.yaml \
  up -d --build mysql redis etcd kafka minio kafka-init minio-mc teamgram

docker compose -p privatechat-local \
  -f docker-compose-env.yaml -f docker-compose.yaml -f docker-compose.local.yaml \
  ps -a
```

`kafka-init` 和 `minio-mc` 是一次性初始化任务，预期退出码为 `0`。当前机器无法拉取原 MinIO 镜像，本地 overlay 使用固定 digest 的 RustFS S3 兼容镜像；这不表示已经验证生产存储迁移。初始化脚本验证 `documents`、`encryptedfiles`、`photos`、`videos` 四个桶的签名 PUT/GET/DELETE。

可在不改动联调数据库的情况下检查所有 SQL 初始化脚本：

```sh
bash scripts/local-dev/check-sql-init.sh
```

该脚本创建并移除一个无宿主机端口的临时 MySQL 容器。修复后的 `chat_invite_participants` 表含 DAO 需要的 `requested` 和 `approved_by` 列。

全量服务端门禁还会从旧版 `chat_invite_participants` schema 执行一次前向 migration，确认已有行保留、新列默认值正确且重复执行不报错。可单独复验：

```sh
bash server/scripts/local-dev/check-invite-participants-migration.sh
```

该检查同样只使用可删除的 tmpfs MySQL 容器，不连接本地联调数据库。

## 本地协议烟测

在统一仓库根目录执行：

```sh
python3 -m venv toolchains/protocol-smoke
toolchains/protocol-smoke/bin/python -m pip install \
  -r docs/scripts/local_mtproto_smoke_requirements.txt
toolchains/protocol-smoke/bin/python -m unittest discover -s docs/scripts/tests -v
toolchains/protocol-smoke/bin/python docs/scripts/local_mtproto_smoke.py --run-local-test
```

脚本仅访问 DC 1 的 `127.0.0.1:10443`，只信任 Desktop 中的私服 RSA 公钥，拒绝导出授权和切换至其他地址；会话仅在内存里存在。它使用白名单测试号 `12025550101`、`12025550102`，根据服务端返回的事务 hash 读取未过期 OTP，然后验证两个方向的历史消息及文件下载字节。

锁定的 Telethon `1.43.2` 使用 TL layer 224。当前服务端依赖已升级为 `github.com/teamgram/proto v0.227.0`；本地匿名 Config 实测覆盖 layer 224、225、227，协议回归测试也覆盖这些层的核心响应与消息请求。更新烟测依赖前仍应核对协议层，不能把 layer 227 的验证延伸为更高层全部受支持。烟测进程对旧版库的 RSA 加密回调应用现代 `RSA_PAD`，并有解密/哈希回归测试；不改动服务端加密验证。

默认 API identity 为仅供本地自建服务验证的占位值，可以通过 `PRIVATE_CHAT_SMOKE_API_ID` 和 `PRIVATE_CHAT_SMOKE_API_HASH` 覆盖。当前服务端 API ID/hash 校验尚未实现，因此这些值不代表向第三方申请的正式客户端身份。脚本会创建或复用测试账号，并在双方历史中保留本次测试消息和小文件。

成功输出 JSON 应包含 `login_1`、`login_2`、`text_roundtrip_1`、`text_roundtrip_2`、`file_roundtrip`，以及总结果 `passed: true`。完整检查限制为 180 秒，对端历史等待最多 15 秒以容纳 Kafka 异步投递。

## 客户端地址与公钥

| 客户端 | 本地 DC 地址 |
| --- | --- |
| macOS Desktop | `127.0.0.1:10443` |
| iOS Simulator | `127.0.0.1:10443` |
| Android Emulator | `10.0.2.2:10443` |

Android 的 `10.0.2.2` 指宿主机。三端公钥和服务端样例私钥导出的公钥一致：SPKI DER SHA-256 为 `8f6c301fbc4b05617136fcd9e88d794d20a23ab8ebe7bcf28fe73f746aad2040`，MTProto fingerprint 为 `12240908862933197005`。这仍是源码样例身份，正式部署应在客户端与服务端同步替换。

本地运行服务已应用 DC 配置覆盖。2026-11-05 15:54 +0800 的匿名 `help.getConfig` 探针在 layer 224、225、227 均返回 DC 1 的 `127.0.0.1:10443`，`webfile_dc_id` 为 1；结果记录在 `integration/server-runtime-config-layers.json`。客户端初始地址见上表。Android/iOS 原生互通的附件字节与 SHA-256 记录见根目录 `integration/android-progress.md` 和 `integration/ios-progress.md`。普通小文件上传下载也由协议烟测验证；WebFile 及跨 DC 下载不在该结果内。

## 构建记录与证据

当前机器已通过 App Store 安装 Xcode `27.2 (27B52)`，开发目录为 `/Applications/Xcode.app/Contents/Developer`，首次启动检查及 clang 解析通过。Android SDK/JDK、Desktop 的 CMake/原生构建工具和协议 venv 放在根目录 `toolchains` 中。iOS 本机构建使用了已记录的 Xcode 27 兼容设置；CI 的 iOS 包装器仍要求源码固定的 Xcode 26.2。各客户端 README 给出各自配置入口，完整 CI 与工具链边界见 `ci-cd.md`。

完整构建日志、运行 JSON 和当前进度保存在根目录 `integration`，包括 `server-progress.md`、`server-proto-progress.md`、`server-runtime-recovery.md`、`android-progress.md`、`desktop-progress.md`、`ios-progress.md`、`ios-runtime-progress.md`、`protocol-smoke.json`。原始进度保留历史失败和修复过程，应以对应平台的最新验收记录为准。日志未纳入版本库。OTP outbox、客户端本地 API 配置和 `.env` 不应进入版本库或报告。

2026-11-05 最新本地 Go 验证记录已通过 `go test -count=1 ./...` 和 `go test -count=1 -tags privatechat_localtest ./...`，并通过两种模式的完整 build。验证使用 `golang:1.23.0` 容器及 FFmpeg/FFprobe 5.1.9；证据为 `integration/go-ci-root-default-verified.log`、`integration/go-ci-root-localtest-verified.log` 和完整脚本复验的 `integration/go-ci-root-script-full-verified.log`。曾阻塞全套测试的 bot username 断言、格式检查、JPEG fixture、status mock 接口和 FFmpeg 测试问题已在本地修复或改用自包含 fixture；旧 `server/data/local-integration/go-test.log` 只保留修复前失败。

可在具备上述 Go 与媒体工具的环境中从统一仓库根目录复验：

```sh
bash scripts/ci/check-server.sh affected
bash scripts/ci/check-server.sh full
```

独立运行 `go vet -p 2 ./...` 仍报告生成 TL codec 的 unreachable-code 和 `bff_proxy_client.go` 的未调用 context cancel 告警；这里的全量测试成功指 `go test` 默认 vet 行为，不能延伸为独立 vet 全绿。上述均为本地记录，不表示线上 CI、签名分发或 Release 已成功。
