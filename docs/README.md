# Private Chat Documentation

`Private Chat` 是一套可自建的聊天系统，由私有消息服务端、Android、iOS、桌面客户端及本仓库的项目文档组成。这里的“私有”指服务可由操作者自行部署和管理。

统一源码仓库为 [shiyi-log/private-chat](https://github.com/shiyi-log/private-chat)，根目录按 `server/`、`desktop/`、`android/`、`ios/`、`docs/` 保存五个组件。公开首次发布采用经过敏感文件筛选的无历史源码快照；本地导入工作区另行保留完整历史供审计，下面列出源仓库。

## 历史套件仓库

| 仓库 | 范围 | 源码许可 |
| --- | --- | --- |
| [private-chat-server](https://github.com/shiyi-log/private-chat-server) | 基于 Teamgram 的 Go / MTProto 服务端 | Apache-2.0 |
| [private-chat-desktop](https://github.com/shiyi-log/private-chat-desktop) | Windows、Linux、macOS 桌面客户端 | GPL-3.0，保留 OpenSSL 链接例外；见该仓库 `LICENSE` |
| [private-chat-android](https://github.com/shiyi-log/private-chat-android) | Android 客户端 | GPL-2.0；见该仓库 `LICENSE` |
| [private-chat-ios](https://github.com/shiyi-log/private-chat-ios) | iOS 客户端 | GPL-2.0-or-later；保留上游及第三方许可声明 |
| [private-chat-docs](https://github.com/shiyi-log/private-chat-docs) | 架构、任务与历史版本记录 | 本仓库原创文档采用 Apache-2.0；见 `LICENSE` |

macOS 端由 `private-chat-desktop` 覆盖。目前这五个仓库没有独立 Web 聊天客户端。服务端的 WebSocket 网关不等于浏览器聊天界面。

服务端保留 Teamgram 上游署名；客户端基于 Telegram 开源客户端源码快照，保留各自上游许可与第三方声明。各仓库的许可证分别适用；本仓库文档的 Apache-2.0 授权不改变客户端和第三方代码的许可。

## 当前源码预览范围（2026-11-05）

服务端 `v0.1.15-preview.1` 的范围是供本地评估的源码预览。默认 `none` 验证器已关闭：不返回验证码，也不再接受固定验证码。生产账号登录需要经过审查的真实验证码提供方；显式启用的本地测试构建使用短时、绑定事务的随机验证码，仅允许本地白名单账号。

历史文档中的固定验证码、默认密码和测试账号描述用于记录旧版本本地实验，不能作为当前预览版的操作说明。启动当前服务端前，应按服务端 README 设置独立的 MySQL、MinIO 和 Grafana 密码；Compose 发布端口默认绑定 `127.0.0.1`。

客户端当前默认 DC 地址仍面向本地开发：

- Desktop、iOS 模拟器：`127.0.0.1:10443`。
- Android 模拟器：`10.0.2.2:10443`，即模拟器访问宿主机的地址。
- 真机或跨机器部署需要改为可访问的局域网 IP 或域名，并保持服务端和客户端 MTProto 公钥一致。

当前源码公开不表示已经提供完整的正式客户端安装包。Android ARM64 Debug、iOS 模拟器 Debug 和 macOS universal Debug 均已本地构建；统一仓库本轮新 Desktop App 补齐辅助资源后已重新签名，通过严格代码签名验证、独立启动和原生登录。Android101↔iOS102、Desktop101↔iOS102 的跨账号双向文本与附件验收均已通过；真机签名、正式更新及生产推送配置仍需各自验证。

候选统一源码预览版本为 `v0.2.0-preview.1`。已验证候选基线 `83cab6ef6ec66fa452e11f0abb50618d34a5612c` 的 CI run `42027610583` 五个 jobs 全部成功，Release preview dry run `42028718339` 已生成源码包和 release notes；该 dry run 不代表版本已发布。已发布资产的来源以 Release tag 与 manifest 的 `source_commit` 为准，当前状态见 [GitHub Releases](https://github.com/shiyi-log/private-chat/releases)。2026-11-05 本地验证已通过默认与 `privatechat_localtest` 两种全量 Go 测试、两种完整构建以及三个客户端配置验证器。两账号协议烟测和两组原生跨账号验收分别保留证据，接收端附件均已打开并核对字节数与 SHA-256。Android101 与 Desktop101 同账号历史同步通过：Android 显示了新文本与附件条目，并下载、打开和校验了 iOS 回发的 79 字节附件；Desktop 新发的 63 字节附件仅确认 Android 历史可见，详细状态见 [local-integration.md](local-integration.md)。

## 文档索引

- [local-integration.md](local-integration.md)：五仓库当前机器的本地联调、隔离验证码模式、协议烟测及原生客户端验收进度。
- [development-tasks.md](development-tasks.md)：开发任务与实施状态，顶部标注当前发行边界。
- [private-server-migration.md](private-server-migration.md)：原始架构迁移方案与接口定位，包含历史本地配置示例。
- [版本记录.md](版本记录.md)：历史版本变更记录，保留当时验证结果和限制。

修改方案时应同步更新任务状态，涉及服务地址、密钥、账号或生产拓扑的内容应使用脱敏示例，不在文档中保存真实凭据。版本记录保留历史事实；发行说明和当前任务状态用于说明新版本与旧实验的差异。

## English summary

Private Chat consolidates five components in `shiyi-log/private-chat`: a Teamgram-based server, desktop clients for Windows/Linux/macOS, Android, iOS, and documentation. The public first release is a screened source snapshot; the original imported histories remain in the local import workspace for audit. There is no standalone web chat client in this suite.

The server source preview disables the default verification provider. Production sign-in requires a reviewed real provider; the explicit local-test build uses short-lived, transaction-bound random codes for allowlisted local accounts. Current client addresses target local development. Native bidirectional text and file transfers passed for Android101 ↔ iOS102 and Desktop101 ↔ iOS102, including receiver-side file opening and byte/SHA-256 checks. Android101 and Desktop101 share an account, and Android showed the new messages and attachment entries in account history. Android also downloaded, opened, and hashed the new 79-byte iOS attachment; the new 63-byte Desktop attachment was visible in history only. Upstream and third-party licenses apply independently in each repository; the Apache-2.0 license here covers original documentation only.
