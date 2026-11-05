# Private Chat iOS 端

这是 `Private Chat` 私有聊天系统的 iOS 客户端源码快照，用于连接我们自建的 `private-chat-server`。当前仓库不再作为 Telegram 官方 iOS 客户端发布，也不应使用 Telegram 品牌对外分发。

## 当前状态

- 默认应用显示名已改为 `Private Chat`。
- 默认 Bundle ID 已改为 `com.privatechat.ios`。
- 默认 URL Scheme 已改为 `privatechat`。
- iOS 模拟器默认连接宿主机私有服务端：`127.0.0.1:10443`。
- MTProto 认证公钥和备用配置解密公钥已替换为当前私有服务端公钥。
- 当前已完成本地静态配置验证、模拟器专用 Xcode 工程生成、iOS 26.5 模拟器 Debug 构建、安装和启动冒烟验证。
- 真机包和发布包仍未完成，需要真实 Apple 签名证书、provisioning profile、正式私有 API 凭据和可被设备访问的局域网 IP 或公网域名。

## 本地验证

运行 iOS 私有化配置验证：

```sh
python3 scripts/verify_private_chat_ios_config.py
```

验证覆盖：

- `build-system/template_minimal_development_configuration.json` 中的 Bundle ID、URL Scheme 和可生成工程的本地开发凭据格式。
- `Telegram/Telegram-iOS/Config-Fork.xcconfig` 中的应用名、Bundle ID 和 URL Scheme。
- `Telegram/Telegram-iOS/Info.plist` 中的 URL Scheme、权限文案和主题文件类型。
- `Telegram/BUILD` 中实际构建产物使用的主 App 显示名、权限文案和主题文件类型。
- 分享扩展登录提示。
- iOS 网络 seed DC 地址和端口。
- README 私有化说明。

## 构建前置条件

iOS 端本地模拟器构建已验证，真机和发布构建仍需要：

- 可用签名证书和 provisioning profile。
- 正式私有项目的 `api_id`、`api_hash` 和 Apple Developer Team ID。
- 真机测试时需要把 `127.0.0.1` 改为局域网 IP 或公网域名。

当前模板内的 `api_id`、`api_hash`、`team_id` 是为了让本地模拟器工程可生成的开发值，不是生产发布凭据。生产发布前必须替换：

```text
build-system/template_minimal_development_configuration.json
```

## 本地构建入口

生成无签名模拟器工程：

```sh
python3 build-system/Make/Make.py \
    --overrideXcodeVersion \
    --cacheDir="$HOME/private-chat-ios-bazel-cache" \
    generateProject \
    --configurationPath=build-system/template_minimal_development_configuration.json \
    --codesigningInformationPath=build-system/fake-codesigning \
    --disableProvisioningProfiles \
    --disableExtensions
```

构建 iOS 模拟器 Debug 包：

```sh
xcodebuild -project Telegram/Telegram.xcodeproj \
    -scheme Telegram \
    -configuration Debug \
    -destination 'platform=iOS Simulator,id=6884B260-4102-40AE-9507-FB1A0ED22725' \
    build
```

真机和发布包必须使用真实签名配置。

## 后续测试要求

- 使用私有服务端完成登录冒烟测试。
- 真机签名准备好后构建设备版本。
- 使用固定局域网 IP 或公网域名完成 Android / iOS / Desktop 多端互通测试。

## English Summary

This repository is a private iOS client snapshot for `Private Chat`, configured for a self-hosted `private-chat-server`. It is not an official Telegram iOS distribution and should not be shipped with Telegram branding.

## 开源许可与上游署名

本项目基于 [Telegram for iOS](https://github.com/TelegramMessenger/Telegram-iOS) 进行私有服务端适配。Telegram 派生应用代码及本项目相应改动按 **GPL-2.0-or-later**（GNU GPL 第 2 版或后续版本）提供；依据为 Telegram [官方源码说明](https://telegram.org/apps#source-code)。完整条款见 [LICENSE](LICENSE)，许可范围与上游署名见 [LICENSE.md](LICENSE.md)。第三方组件保留各自的许可证和版权声明。
