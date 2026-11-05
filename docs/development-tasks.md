# 私有聊天系统开发任务 / Private Chat Development Tasks

## 当前机器本地联调（2026-11-05）

当前目标为 Server、Desktop、Android、iOS、Docs 五仓库本地联通，范围和实际验收结果见 [local-integration.md](local-integration.md)。服务端已使用显式本地测试构建完成双账号登录、双向文本和文件字节校验；原生客户端构建及界面联调正在继续。以下历史勾选保留原始记录，不作为当前机器全部可运行的证明。

## 当前发行状态（2026-11-03）

以下阶段清单及测试结果保留为此前开发的历史快照。当前服务端源码预览 `v0.1.15-preview.1` 已关闭 `none` 验证器，不再返回验证码或接受固定验证码；接入并审查真实提供方前，默认配置不能完成登录。下文记录的 `12345`、旧测试号及消息互发结果不适用于当前发行配置。

- 套件由 `private-chat-server`、`private-chat-desktop`、`private-chat-android`、`private-chat-ios`、`private-chat-docs` 五个仓库组成。macOS 包含在 desktop；目前没有独立 Web 聊天客户端。
- 当前服务端 Compose 要求操作者设置独立的 MySQL、MinIO 和 Grafana 密码，发布端口默认绑定 `127.0.0.1`。
- 客户端默认地址仍为本地开发地址：Desktop / iOS 使用 `127.0.0.1:10443`，Android 模拟器使用 `10.0.2.2:10443`。跨设备联调需要修改地址并匹配 MTProto 公钥。
- 服务端定向验证已覆盖禁用验证码提供方、配置替换、Compose 配置和镜像构建；完整 Go 测试仍有 KV 接口不兼容及缺少 FFmpeg 的失败。
- 历史客户端构建和 Android 双模拟器消息验证不能替代当前预览版的完整多端测试。Desktop / Android / iOS 全套登录、消息和文件上传联调，以及正式签名和分发配置仍需完成。
- 源码许可按仓库分别适用，详见本仓库 README 的套件索引，保留上游及第三方许可声明。

## 历史开发清单


本文档用于管理五个本地仓库的开发任务：

- 服务端 / Server：`server`
- PC/Mac 桌面端 / Desktop：`desktop`
- iOS 端 / iOS：`ios`
- 安卓端 / Android：`android`
- 项目文档 / Docs：`docs`

说明：当前 **Mac 桌面端包含在 `desktop` 仓库中**。如果后续决定单独支持原生 macOS 客户端，再新增独立仓库和任务列表。

## 阶段 0：仓库基线 / Repository Baseline

- [x] 为 `server` 创建本地 Git 仓库。
- [x] 为 `server` 创建 `private-main` 分支。
- [x] 为 `desktop` 创建 `private-main` 分支。
- [x] 为 `ios` 创建 `private-main` 分支。
- [x] 为 `android` 创建 `private-main` 分支。
- [x] 为 `docs` 创建 `private-main` 分支。
- [x] 备份三端客户端旧 `.git` 元数据，不补全庞大的上游历史。
- [x] 当前客户端仓库采用私有源码快照模式独立维护。
- [x] 提交安卓端已有的私有 `APP_ID` / `APP_HASH` 修改。
- [x] 确定我们自己的 Git 托管地址：GitHub 私有仓库。
- [x] 为五个仓库添加我们自己的远程地址 / private remote。
- [x] 推送五个仓库的 `private-main` 分支。
- [x] 将仓库命名统一为中性私有品牌：`private-chat-*`。

## 阶段 1：本地启动服务端 / Local Server Boot

目标：在本机用 Docker 启动 Teamgram，并确认客户端网关可连接。

- [x] 检查 `server/docker-compose-env.yaml` 的端口和数据目录。
- [x] 检查 `server/docker-compose.yaml` 的应用服务配置。
- [x] 检查本机 Docker / Docker Compose 是否可用。
- [x] 启动依赖服务：MySQL、Redis、etcd、Kafka、MinIO。
- [x] 启动 Teamgram 应用服务。
- [x] 验证客户端网关端口：
  - TCP `10443`
  - TCP `5222`
  - WebSocket `11443`
- [x] 检查 `gnetway`、`session`、`bff`、`msg`、`sync` 日志。
- [x] 确认默认登录验证码逻辑：当前本地 none 验证器固定验证码为 `12345`。
- [x] 修复 Android 实际发送纯数字测试号导致 `42400` 被误判为无效号码的问题。
- [x] 修复授权登录链路未复用公共测试号池导致 `42401` 被误判为无效号码的问题。
- [x] 修复验证码缓存 TTL 低于业务过期时间导致第二账号登录慢操作时 `PHONE_CODE_EXPIRED` 的问题。
- [ ] 生产环境前替换默认/演示验证码逻辑。

## 阶段 2：服务端私有化配置 / Server Configuration

目标：把服务端变成我们自己的私有测试环境。

- [ ] 生成项目专用密钥和配置。
- [x] 确认当前服务端 RSA key，并导出客户端可用公钥。
- [ ] 配置私有服务器 IP / 域名。
- [ ] 修改数据库、Redis、MinIO 等默认账号密码。
- [ ] 整理必需环境变量。
- [ ] 关闭或替换演示账号、演示验证码。
- [ ] 确定第一版登录验证方式：
  - 本地固定验证码，仅测试使用
  - 后台可见验证码
  - 短信/邮箱验证码服务
- [ ] 写一份单服务器部署说明。

## 阶段 3：PC/Mac 桌面端 / Desktop Client

仓库：`desktop`

目标：桌面端连接我们自己的 Teamgram 服务端。

- [x] 决定第一轮继续改当前桌面端快照。
- [x] 修改 `Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp`。
- [x] 将生产和测试 DC 1 指向本机私有服务端 `127.0.0.1:10443`。
- [x] 确认 Desktop 使用的 RSA 公钥需要和服务端一致。
- [x] 同步替换 Desktop 内置 RSA 公钥。
- [x] 完成静态验证：内置 DC 地址已收敛到本机私有服务端，diff 检查无空白错误。
- [x] 提交并推送：`983e0f1 桌面端接入本地私有服务端`。
- [ ] 配置私有 `TDESKTOP_API_ID` / `TDESKTOP_API_HASH`。
- [x] 替换应用显示名称和 Linux/Windows 用户可见安装信息。
- [ ] 替换图标。
- [x] 替换 macOS Debug Bundle/App ID 和应用名生成配置。
- [ ] 替换 macOS Bundle/App ID 的完整发布签名配置。
- [x] 默认禁用上游官方自动更新和崩溃上报。
- [x] 替换 Desktop 高可见版本记录、主菜单和 Windows 更新器支持/更新链接为私有占位地址。
- [x] 替换 Desktop 默认英文账号、安全、存储、代理、FAQ、会话、手机号隐私和 Bot 隐私入口中的通用品牌漏项。
- [x] 替换 Desktop 默认英文普通运行入口第二批品牌漏项，覆盖主题、下载、通话、邀请、联系人、Bot、条款、导出、语言包、辅助功能、mini app、冻结账号、年龄验证和 Passport 普通入口。
- [x] 替换 Desktop 默认英文剩余非商业化普通入口品牌漏项和上游链接示例。
- [ ] 接入正式自建更新、崩溃收集、隐私政策、服务条款和支持链接。
- [x] 将 Desktop 对外系统 URL scheme 改为 `privatechat://`，并保留内部 handler 兼容映射。
- [x] 构建 macOS 桌面端 Debug 版本：`out/Debug/Private Chat.app` 已生成。
- [ ] 按需构建 Windows / Linux 桌面端。
- [x] 完成桌面端构建环境检查。
- [x] 安装完整 Xcode 26.5 并确认 `xcode-select` 指向 `/Applications/Xcode.app/Contents/Developer`。
- [x] 准备桌面端 Qt 6.11.1 和第三方库环境。
- [x] 执行桌面端私有化静态配置验证：当前 `304/304` 项通过。
- [x] 修复 macOS 依赖准备中 `libjxl` 的 `third_party/lcms` GitHub 下载中断问题。
- [x] 修复 Desktop macOS 构建中 FFmpeg 根目录 include 污染导致 `<version>` 标准库头误命中的问题。
- [x] 完成 Desktop macOS Debug 构建签名校验：`codesign --verify --deep --strict "out/Debug/Private Chat.app"` 通过。
- [ ] 修复或切换 Linux Docker 构建镜像源后重新准备 `tdesktop:centos_env`。
- [ ] 完成登录冒烟测试 / login smoke test。
- [ ] 完成私聊消息收发测试。

## 阶段 4：安卓端 / Android Client

仓库：`android`

目标：安卓端连接我们自己的 Teamgram 服务端。

- [x] 提交当前 `BuildVars.java` 中的私有 API 配置。
- [x] 决定第一轮继续改当前安卓端快照。
- [x] 修改 `TMessagesProj/jni/tgnet/ConnectionsManager.cpp`。
- [x] 在 `ConnectionsManager::initDatacenters()` 中将 DC 1 指向 Android 模拟器访问宿主机的 `10.0.2.2:10443`。
- [x] 检查 `TMessagesProj/jni/tgnet/Handshake.cpp` 中的 RSA 公钥逻辑。
- [x] 同步替换 Android 内置 RSA 公钥。
- [x] 同步替换 simple config 解密公钥。
- [x] 完成静态验证：目标网络文件不再包含官方 DC 地址，diff 检查无空白错误。
- [x] 提交并推送：`a634c447 安卓端接入本地私有服务端`。
- [x] 安装 Java Runtime 后重新运行 Gradle 工程解析。
- [x] 替换 Android 对外包名和应用显示名。
- [x] 修复 Android 默认英文欢迎页和登录权限弹窗的上游品牌漏项。
- [x] 新增并运行 Android 私有化静态配置验证脚本：`scripts/verify_private_chat_android_config.py`，当前 `482/482` 项通过。
- [x] 修复 Android Debug/Beta 包名判断仍使用旧包名的问题。
- [x] 修复 Android 默认英文登录验证码入口仍显示上游品牌的问题。
- [x] 修复 Android 默认英文帮助、通知、QR 登录、更新入口和联系人加入提示中的高可见品牌漏项。
- [x] 修复 Android 默认英文权限、锁屏、存储、Passcode 和通话通知渠道说明中的系统入口品牌漏项。
- [x] 修复 Android 默认英文手机号、账号切换、代理提示、版本更新、邮箱登录、登出确认、账号查找、设备会话和邀请文案中的品牌漏项。
- [x] 修复 Android 默认英文付款、导入、群组/频道、举报、屏蔽、用户名、Secret Chat、主题、通知、缓存/数据库、网页会话、两步验证、隐私、通话、旧目录迁移、下载和 Passcode 创建说明中的通用体验品牌漏项。
- [x] 修复 Android 默认英文 Passport、地图预览、直播/群组通话、设备会话、登录邮箱重置、SD 卡存储、故事、登录码安全、内置浏览器、Bot 隐私/权限、账号冻结、短信费用、年龄验证、搜索新闻和普通链接示例中的品牌漏项。
- [ ] 替换图标。
- [x] 替换 Android 通知渠道名称和系统通知入口品牌。
- [x] 替换 Android 默认英文服务条款拒绝、删除账号警告和 WebApp / mini app 条款入口为私有占位地址。
- [x] 替换 Firebase / `google-services.json` 和 Huawei AGConnect 包名配置。
- [x] 默认禁用 Firebase / Huawei 第三方推送 token 获取，避免未配置第三方项目时报错。
- [ ] 接入正式自建推送、支持、更新、上报接口。
- [x] 构建 Debug APK：`TMessagesProj_App/build/outputs/apk/afat/debug/app.apk`。
- [x] 确认 Debug APK 对外包名为 `com.privatechat.messenger.beta`。
- [x] 安装 Debug APK 到 Android 15 ARM64 模拟器。
- [x] 重新构建并覆盖安装最新 Debug APK 到两台 Android 15 ARM64 模拟器。
- [x] 修复私有单 DC 配置下首次启动 native 崩溃。
- [x] 完成 Android 模拟器启动冒烟验证：应用进程存活，已连接私有 DC 1，完成握手、`TL_config` 和 `TL_pong`。
- [x] 完成 Android 最新 Debug APK 双模拟器启动复测：`emulator-5554`、`emulator-5564` 均可显式启动 `LaunchActivity`，进程存活且未发现 `FATAL EXCEPTION`。
- [x] 完成 Android 登录/注册冒烟测试：测试号 `+4 2400`，验证码 `12345`，注册用户 `Android Smoke`，进入主界面。
- [x] 修复 Android 登录成功后的默认英文空会话页和联系人权限说明品牌漏项。
- [x] 完成两台 Android 模拟器私聊消息互发测试：`Android Smoke` 与 `Android Two` 可互发文本消息并在对端会话页显示。

## 阶段 5：iOS 端 / iOS Client

仓库：`ios`

目标：iOS 端连接我们自己的 Teamgram 服务端。

- [x] 决定第一轮继续改当前 iOS 端快照。
- [x] 定位当前代码中的 `Network.swift` 网络入口。
- [x] 将 DC 1 的 `seedAddressList` 指向本机私有服务端 `127.0.0.1`。
- [x] 确认 iOS 端需要显式配置 `10443` 端口。
- [x] 检查 `submodules/MtProtoKit/Sources/MTDatacenterAuthMessageService.m` 中的 RSA 公钥逻辑。
- [x] 同步替换 iOS 内置 RSA 公钥。
- [x] 同步替换备用配置解密公钥。
- [x] 完成静态验证：目标网络文件不再包含官方 DC 地址，diff 检查无空白错误。
- [x] 提交并推送：`3201a932 iOS端接入本地私有服务端`。
- [x] 安装完整 Xcode 后生成工程并构建模拟器版本。
- [x] 在构建配置中设置可生成工程的本地开发 `api_id` / `api_hash`。
- [x] 替换 iOS fork 配置中的 Bundle ID、应用显示名和 URL Scheme。
- [x] 替换 iOS 权限弹窗、分享扩展登录提示和主题文件类型中的用户可见品牌。
- [x] 新增并运行 iOS 私有化静态配置验证脚本：`scripts/verify_private_chat_ios_config.py`，当前 `456/456` 项通过。
- [x] iOS README 已改为中文优先的 `Private Chat iOS` 私有快照说明，并纳入验证脚本门禁。
- [x] 修复 iOS 默认英文 `PresentationStrings`、Widget 扩展、登录、联系人、会话、权限、通话、邀请和缓存等高可见入口中的品牌漏项。
- [ ] 替换图标和签名配置。
- [x] 替换 iOS 默认英文条款、隐私、更新和 WebApp 免责声明入口为私有占位地址。
- [x] 替换 iOS 默认英文登录验证码、联系人上下文菜单、通知音、浏览器和 Passport 复用帮助入口中的上游品牌漏项。
- [x] 替换 iOS 默认英文第一批普通运行入口品牌漏项，覆盖联系人加入、公开链接、缓存、定位、清空聊天、网站登录、联系人重置、Passport、分享登录、语言包、验证码、Passcode、权限和壁纸入口。
- [x] 将 iOS App Store / AppCenter 发布配置收敛为私有占位配置。
- [x] 将 iOS 旧发布校验脚本、扩展构建 plist、上游 merchant / Bundle ID 发布身份收敛为私有占位。
- [ ] 接入正式自建分发、支持、上报、隐私政策和服务条款。
- [x] 完成 iOS 构建系统入口检查：`build-system/Make/Make.py --help` 可运行。
- [x] 完成 iOS Bazel 前置检查：当前缺 `build-input/configuration-repository`。
- [x] 将 `build-system/template_minimal_development_configuration.json` 中的 `api_id`、`api_hash`、`team_id` 占位值替换为可生成工程的本地开发配置；生产发布前仍需替换正式私有凭据。
- [x] 生成 Xcode 工程。
- [x] 构建模拟器版本。
- [x] 安装 iOS 模拟器包并完成启动冒烟验证：`com.privatechat.ios` 可启动，显示名为 `Private Chat`。
- [ ] 签名准备好后构建设备版本。
- [ ] 完成登录冒烟测试。
- [ ] 完成私聊消息收发测试。

## 阶段 6：多端互通 / Cross-Client Compatibility

目标：确认所有客户端都能通过我们的服务端互相通信。

- [ ] 在 PC/Mac 上创建测试用户 A。
- [x] 在 Android 上创建测试用户 B：`Android Smoke` / `Android Two` 已在两台模拟器完成登录注册。
- [ ] 在 iOS 上创建测试用户 C。
- [ ] 测试 A -> B 文本消息。
- [ ] 测试 B -> C 文本消息。
- [ ] 测试 C -> A 文本消息。
- [x] 验证 Android B -> Android B 文本消息：两台 Android 模拟器已完成双向文本消息互发。
- [x] 验证 Android 双端历史消息可拉取并在会话页显示。
- [x] 验证 Android 双端联系人逻辑：`contacts.importContacts` 已触发，`contacts.getContacts` 能返回对方。
- [ ] 验证跨 Desktop / Android / iOS 的历史消息仍存在。
- [ ] 验证跨 Desktop / Android / iOS 的未读数。
- [ ] 验证跨 Desktop / Android / iOS 的联系人逻辑。
- [ ] 验证基础群聊。
- [ ] 验证小图片上传下载。
- [ ] 验证小文件上传下载。

## 阶段 7：产品私有化 / Product Fork Cleanup

目标：去掉官方品牌身份，形成我们自己的产品。

- [ ] 确定产品名称。
- [x] 第一轮临时产品显示名确定为 `Private Chat`。
- [ ] 确定域名：
  - API/DC 域名
  - 官网域名
  - 支持域名
- [x] 替换三端第一批系统级、安装级、应用显示名级官方品牌用户可见文案。
- [ ] 替换官方 Logo 和应用图标。
- [ ] 替换隐私政策、服务条款、支持链接。
- [ ] 替换崩溃上报和自动更新端点。
- [ ] 检查开源许可证和源码发布要求。
- [ ] 准备内测版本发布说明。

## 阶段 8：服务器部署 / Deployment

目标：部署到我们自己的服务器和域名。

- [ ] 确定服务器系统和配置。
- [ ] 安装 Docker 和 Docker Compose。
- [ ] 配置 DNS。
- [ ] 配置防火墙：
  - 开放 `10443`
  - 按需开放 `5222`
  - 按需开放 `11443`
  - 限制数据库和管理端口
- [ ] 配置持久化数据目录。
- [ ] 配置数据库备份。
- [ ] 配置日志轮转。
- [ ] 配置基础监控。
- [ ] 部署依赖服务。
- [ ] 部署应用服务。
- [ ] 使用所有客户端跑一轮冒烟测试。

## 阶段 9：压力测试与验收 / Load Test

目标：在可重复环境里确认服务端和三端客户端的基础稳定性。

- [ ] 准备公网 IP 或局域网固定 IP，保证桌面端、Android 真机、iOS 真机可同时访问。
- [x] 准备 Android Java/SDK 环境并构建 Debug APK。
- [x] 准备 Android Emulator 环境并完成 Debug APK 启动验证。
- [x] 完成 Android 本机登录/注册业务冒烟测试。
- [x] 完成 Android 双模拟器私聊消息互发验证。
- [x] 准备完整 Xcode 和 iOS 模拟器环境，并完成模拟器构建/启动验证。
- [ ] 准备 iOS 签名证书和真机环境。
- [x] 准备桌面端 Qt 6.11.1 / 第三方库依赖并构建 macOS Debug 版本。
- [x] 执行服务端入口短连接验证，覆盖 TCP `10443`、`5222`、`11443`。
- [x] 新增可重复执行的服务端入口压测脚本：`server/scripts/local-dev/tcp_entry_stress.py`。
- [x] 执行第一轮低并发入口连接测试，记录 CPU、内存、MySQL、Redis、Kafka、MinIO 指标快照。
- [ ] 编写服务端业务压测脚本，覆盖登录、发消息、WebSocket `11443` 和文件入口。
- [ ] 执行登录、发消息、上传小文件的多端冒烟测试。
- [ ] 执行 1 小时稳定性测试。
- [ ] 输出压测报告和下一轮容量建议。

## 当前阻塞项

- Android Debug APK 已重新构建并覆盖安装到两台 Android 15 ARM64 模拟器；账号 `+42400` / `+42401` 已完成登录注册、联系人导入和双向私聊文本消息验证。
- Android 最新 APK 复测结果：两台模拟器均可启动 `LaunchActivity`，进程存活，日志中未发现 `FATAL EXCEPTION`。
- Android 已默认禁用 Firebase / Huawei 第三方推送 token 获取，避免未配置第三方项目时继续触发 `FIS_AUTH_ERROR` / client blocked；生产推送仍需接入自建服务或正式第三方项目。
- 服务端当前 Docker 镜像已完成重建并在线运行；后续生产部署仍需替换默认验证码、默认账号密码和公网/局域网固定入口。
- Desktop 私有化静态配置验证当前 `304/304` 项通过；完整 Xcode 26.5、Qt 6.11.1 和第三方库依赖已完成准备。
- Desktop macOS Debug 构建已通过，产物为 `desktop/out/Debug/Private Chat.app`，生成产物 `CFBundleIdentifier = com.privatechat.desktop.debug`，`CFBundleName = Private Chat`，并已通过本地 `codesign --verify --deep --strict` 校验。
- Desktop 已默认关闭上游自动更新和崩溃上报，已将对外系统 URL scheme 改为 `privatechat://`，并已将高可见支持/更新链接、默认英文通用账号/安全/存储/代理/FAQ/会话/隐私入口、第二批普通运行入口，以及剩余非商业化普通链接示例替换为私有品牌或私有占位地址；当前剩余默认英文品牌命中集中在 Premium、Stars、广告、礼物、商业化、TON、Fragment 和 Cocoon 等深层策略功能，仍需继续处理图标、发布签名、正式自建更新/崩溃收集/隐私政策/服务条款，以及跨端登录和消息收发冒烟测试。
- Desktop Linux Docker 构建环境被 EPEL 镜像源 SSL 连接失败阻塞。
- iOS 私有化静态配置验证已扩展到默认英文 `PresentationStrings`、Widget 扩展、实际构建用主 App plist 片段、App Store / AppCenter 发布配置、旧发布校验脚本、扩展构建 plist、默认英文条款、隐私、更新、登录验证码、联系人上下文菜单、通知音、浏览器、Passport 复用帮助和第一批普通运行入口，当前 `456/456` 项通过；Xcode 26.5 / iOS 26.5 Simulator 已完成工程读取、Debug 构建、安装和启动冒烟验证。
- iOS 发布配置当前已收敛为私有占位：App Store ID / AppCenter ID 为 `0`，Premium IAP 产品 ID 为空，Siri / iCloud 默认关闭，旧发布校验脚本和扩展构建 plist 不再使用上游发布身份；正式发布前仍需替换真实 Apple Developer Team ID、签名证书、provisioning profile、正式域名、隐私政策和服务条款。
- iOS 真机/发布构建仍需要真实 Apple Developer Team ID、签名证书、provisioning profile 和正式私有 `api_id` / `api_hash`。
- 真机和多端互通测试需要局域网固定 IP 或公网域名，不能继续使用本机回环地址。
- iOS 真机包需要开发者账号和签名证书。
- 正式压力测试需要先完成可运行客户端包和稳定服务端入口地址。
- Android 已完成账号/邀请/会话/版本更新、通用体验入口、通知渠道名称、服务条款拒绝、WebApp / mini app 条款入口、Passport、内置浏览器、通话/直播、年龄验证、账号冻结和普通链接示例品牌补漏，并已默认禁用第三方推送 token 获取；私有化静态验证扩展到 `482/482` 项通过，最新 Debug APK 构建通过。
- 品牌彻底清理仍需正式产品域名、图标、隐私政策、服务条款、崩溃上报、自动更新端点，以及 Premium、Stars、广告、礼物、商业化、TON、Fragment、NFT、Affiliate、SMS Premium 等深层功能入口的产品策略。

## 统一语言和品牌词入口策略

- 产品层统一维护一份中文优先的语言与品牌词表，所有端按同一套中文命名、英文 fallback 和禁用词规则执行。
- 代码层没有四端共享的单一语言文件，需要分端落地：
  - Desktop：重点入口为 `Telegram/SourceFiles/lang`、`Telegram/Resources/langs` 和 `td_lang_lang` 代码生成流程。
  - Android：重点入口为 `TMessagesProj/src/main/res/values*/strings.xml` 及现有 `LocaleController` 字符串加载流程。
  - iOS：重点入口为 `Telegram/Telegram-iOS/*/Localizable.strings`、`PresentationStrings` 生成和各扩展资源。
  - macOS Debug 包当前来自 Desktop 仓库，Bundle 层还需要继续替换 `Info.plist` 生成结果、图标和签名配置。

## 第一轮开发建议 / First Sprint

第一轮只做最小闭环：

1. 本地启动 Teamgram 服务端。
2. 修改 PC/Mac 桌面端 DC 地址。
3. 验证 PC/Mac 能连到 Teamgram 登录流程。
4. 修改 Android DC 地址。
5. 验证 Android 能连到 Teamgram 登录流程。
6. 修改 iOS DC 地址。
7. 验证 iOS 能连到 Teamgram 登录流程。

以上完成后，再做品牌替换、正式密钥、生产部署。
