# 私有聊天系统服务端迁移方案 / Private Server Migration

本文档说明如何让现有 MTProto 客户端连接我们自己的服务端。

涉及仓库：

- 服务端 / Server：`server`
- PC/Mac 桌面端 / Desktop：`desktop`
- iOS 端：`ios`
- 安卓端：`android`
- 项目文档 / Docs：`docs`

说明：当前 Mac 桌面端由 `desktop` 支持。如果后续需要单独的原生 macOS 客户端，需要另建仓库和任务。

## 总体判断 / Decision

这些客户端不是普通 REST/WebSocket 聊天客户端，而是通过 MTProto 传输 Telegram TL API 对象。

如果保留现有前端，服务端必须兼容足够多的 MTProto 和 Telegram API，至少要支撑：

- 启动连接
- 登录
- 会话同步
- 私聊消息
- 基础群聊
- 文件上传下载

可选路线：

1. 保留 MTProto 客户端网络栈，搭建兼容服务端。
2. 大改三端客户端网络层，换成自定义协议。

第一阶段建议走路线 1，先基于 Teamgram Server 做最小闭环。

## 推荐基础：Teamgram Server

Teamgram Server 是当前最适合优先评估的开源基础：

- 仓库：`https://github.com/teamgram/teamgram-server`
- 语言/许可证：Go，Apache-2.0
- 协议：MTProto 2.0
- API Layer：README 当前写的是 225
- 功能：私聊、基础群聊、联系人、Web
- 依赖：MySQL、Redis、etcd、Kafka、MinIO、FFmpeg
- 客户端网关端口：
  - TCP `10443`
  - TCP `5222`
  - WebSocket `11443`

注意：公开文档里有默认验证码示例，生产环境前必须替换。

优先结论：先用 Teamgram 跑通，不要一开始从零写 MTProto 服务端。

## Teamgram 客户端接入点 / Client Patch Points

### PC/Mac 桌面端：`desktop`

Teamgram 文档建议修改：

`Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp`

目标配置：

```cpp
const BuiltInDc kBuiltInDcs[] = {
    { 1, "SERVER_IP", 10443 },
};

const BuiltInDc kBuiltInDcsTest[] = {
    { 1, "SERVER_IP", 10443 },
};
```

还要确认：

- 内置 RSA 公钥是否匹配服务端。
- `TDESKTOP_API_ID` / `TDESKTOP_API_HASH` 构建参数。
- macOS 构建同样走 `desktop`。

### Android：`android`

Teamgram 文档建议修改：

`TMessagesProj/jni/tgnet/ConnectionsManager.cpp`

目标逻辑：

```cpp
void ConnectionsManager::initDatacenters() {
    Datacenter *datacenter;
    if (datacenters.find(1) == datacenters.end()) {
        datacenter = new Datacenter(instanceNum, 1);
        datacenter->addAddressAndPort("SERVER_IP", 10443, 0, "");
        datacenters[1] = datacenter;
    }
}
```

还要确认：

- `TMessagesProj/jni/tgnet/Handshake.cpp` 中的 RSA 公钥。
- `BuildVars.java` 中的 `APP_ID` / `APP_HASH`。
- 包名、图标、Firebase、推送配置。

### iOS：`ios`

Teamgram 文档建议修改：

`submodules/TelegramCore/Sources/Network/Network.swift`

目标逻辑：

```swift
seedAddressList = [
    1: ["SERVER_IP"]
]
```

还要确认：

- 当前代码中 `Network.swift` 的实际位置或等效入口。
- 是否需要额外配置端口 `10443`。
- `MTDatacenterAuthMessageService.m` 中的 RSA 公钥。
- iOS 构建配置里的 `api_id` / `api_hash`。

## 服务端启动顺序 / Server Startup Order

Teamgram 是服务化架构，文档中的启动顺序为：

1. `idgen`
2. `status`
3. `authsession`
4. `dfs`
5. `media`
6. `biz`
7. `msg`
8. `sync`
9. `bff`
10. `session`
11. `gnetway`

Docker 方式会通过 Compose 管理这些服务。

## 运行依赖 / Runtime Dependencies

本地默认依赖：

- MySQL `127.0.0.1:3306`
- Redis `127.0.0.1:6379`
- etcd `127.0.0.1:2379`
- Kafka `127.0.0.1:9092`
- MinIO `localhost:9000`

第一阶段建议直接用 `server/docker-compose-env.yaml` 和 `server/docker-compose.yaml`。

## 服务端 MVP 范围 / Server MVP Scope

第一版不要做全量 Telegram 功能，只做最小可用：

- 登录
- 私聊
- 基础群聊
- 历史消息
- 多端同步
- 小图片/文件上传下载

暂缓：

- 频道
- 机器人
- 语音/视频通话
- 支付
- Premium
- Stories
- Secret Chat
- CDN 多数据中心

## 必需协议能力 / Required Protocol Capabilities

服务端必须支持：

- TCP abridged/intermediate transport
- MTProto auth-key handshake：
  - `req_pq_multi`
  - `req_DH_params`
  - `set_client_DH_params`
- RSA 私钥和客户端内置公钥匹配
- DH 参数和 auth key 生成
- server salt
- encrypted message container
- message id / seqno / ack / bad message
- gzip packed payload
- auth session 持久化

Teamgram 已经实现了这些能力，优先复用。

## 第一阶段最小 API / Minimum API Surface

初始需要关注这些 Telegram API：

- `invokeWithLayer`
- `initConnection`
- `help.getConfig`
- `help.getNearestDc`
- `help.getAppConfig`
- `auth.sendCode`
- `auth.signIn`
- `auth.signUp`
- `auth.logOut`
- `users.getUsers`
- `contacts.getContacts`
- `messages.getDialogs`
- `messages.getHistory`
- `messages.sendMessage`
- `messages.readHistory`
- `updates.getState`
- `updates.getDifference`
- `upload.saveFilePart`
- `upload.getFile`

原则：不支持的接口要稳定返回 `rpc_error`，不要让客户端直接断线。

## 里程碑 / Milestones

### 里程碑 1：服务端本地启动

- 启动 Docker 依赖。
- 启动 Teamgram 应用。
- 验证 `10443` 端口可连接。
- 确认 `gnetway` 日志正常。

### 里程碑 2：桌面端连接

- 修改 `desktop` 的 DC 地址。
- 构建 PC/Mac 桌面端。
- 客户端能连到本地/测试服务端。
- 能进入登录流程。

### 里程碑 3：Android 连接

- 修改 Android DC 地址。
- 构建 Debug APK。
- 安卓端能进入登录流程。

### 里程碑 4：iOS 连接

- 修改 iOS DC 地址。
- 构建模拟器版本。
- iOS 端能进入登录流程。

### 里程碑 5：三端互通

- PC/Mac、Android、iOS 各建一个测试用户。
- 三端互发文本消息。
- 验证历史消息和未读数。
- 验证基础群聊。
- 验证小文件。

## 合规和品牌 / Compliance And Branding

派生客户端不能继续使用上游官方名称和 Logo。需要处理：

- 产品名称
- 包名 / Bundle ID
- 应用图标
- 启动画面
- 支持链接
- 隐私政策
- 服务条款
- 自动更新端点
- 崩溃上报端点
- 开源许可证和源码发布要求

## 下一步 / Next Step

按任务文档执行第一轮：

1. 本地启动 Teamgram。
2. 修改 `desktop` 指向 `SERVER_IP:10443`。
3. 跑通 PC/Mac 登录流程。
4. 再接 Android。
5. 最后接 iOS。
