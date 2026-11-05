# 协议与兼容性

本文档说明 Teamgram Server 所支持的 MTProto 子协议、API Layer 及与官方客户端的兼容范围。

## MTProto 2.0

Teamgram 实现 [MTProto 2.0](https://core.telegram.org/mtproto)，支持以下传输格式：

- **Abridged**
- **Intermediate**
- **Padded intermediate**
- **Full**

客户端通过 TCP 或 WebSocket 连接 gnetway，使用上述任一格式进行握手与 RPC。

## API Layer

- 当前支持的 **API Layer** 为 **222**（见主 README；随 proto 更新可能变动）。
- TL 方法与类型以项目依赖的 [teamgram/proto](https://github.com/teamgram/proto) 为准。

## 兼容客户端

| 客户端 | 说明 |
|--------|------|
| [Android (teamgram-android)](../clients/teamgram-android.md) | 修改 ConnectionsManager.cpp 中的服务器地址与端口 |
| [iOS (teamgram-ios)](../clients/teamgram-ios.md) | 配置连接自建服务器 |
| [桌面端 (teamgram-tdesktop)](../clients/teamgram-tdesktop.md) | 配置连接自建服务器 |

**账号登录状态：** 社区版的 `none` 短信验证码实现已关闭，不会返回验证码，并拒绝所有验证码校验。项目未包含生产可用的短信服务；管理员接入并审查短信服务前，账号登录不可用。

## 部署说明

- 客户端需能访问 gnetway 端口（默认 10443、11443、5222）。TLS 或反向代理（如 Nginx WebSocket）需按需配置。
