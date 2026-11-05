# 统一 CI、原生预览构建与发布

本仓库的源码根目录是 `server/`、`desktop/`、`android/`、`ios/` 和 `docs/`。根 `.github/workflows/` 是唯一生效的 GitHub Actions 工作流位置；各组件保留的 `.github` 目录仅作为原项目资料。五个组件的依赖源码已展平为普通文件，当前不需要初始化 Git 子模块。根 `repository-imports.json` 记录原仓库和导入提交。

本地导入工作区保留原始提交历史，供审计和恢复使用；公开的 `shiyi-log/private-chat` 首次发布采用经过筛选的无历史源码快照。这样可以公开五个组件和统一 CI/CD，而不会把导入历史中的服务端私钥一并公开。源码包和公开快照都会排除私钥、签名文件、环境文件、运行数据与本地构建输出；若未来需要公开原始历史，必须先完成密钥轮换和完整历史清理。

当前下一版本名为 `v0.2.0-preview.1`，仍是待验证候选版本。状态截点为 2026-11-05：公开快照提交 `21c76203ba0379bca3f1bf6ba823a0488bad1d89` 已推送到公开仓库 `shiyi-log/private-chat` 的 `main`。首次托管 CI run `42012475721` 的静态配置/契约和 server affected jobs 成功；Server complete Go suite 因 `server/pkg/goffmpeg/tests/transcoding_test 2.go` 重复声明测试函数而失败，Android job 因 `sdkmanager: command not found` 在 APK 构建前失败，Required suite gates 也失败。[查看该 run](https://github.com/shiyi-log/private-chat/actions/runs/42012475721)。这些 CI 修复仍待复验；尚无候选 Release artifact 或已发布 Release。本地检查结果不能替代后续线上成功记录。

## 自动检查

`CI` 工作流在指向本仓库的 pull request、`main` push 和手动触发时运行，也供发布工作流复用。没有路径过滤、`continue-on-error`、隐藏失败的管道或把未执行测试记作成功的处理。

| 检查 | 执行内容 | 成功含义 |
| --- | --- | --- |
| Static configuration and CI contracts | 三个客户端配置验证器、Docs 协议脚本测试、CI/打包契约测试 | 源码配置与离线脚本契约通过；没有原生产物时，组件验证器的产物检查不代表构建成功 |
| Server affected tests and both builds | 指定关联包在默认与 `privatechat_localtest` 模式下测试；两种模式分别 `go build ./...` | 改动关联范围和两种编译模式通过 |
| Server complete suite | 在一次性 MySQL 8.0 容器中验证存量 SQL migration 可重复执行，再执行 `go test -count=1 ./...` 与 `go test -count=1 -tags privatechat_localtest ./...` | 存量 schema 升级回归、默认与本地联调构建标签下的全仓库 Go 测试和默认 vet 检查通过 |
| Android ARM64 debug native build | 完整 Gradle/NDK 构建、ARM64 APK 内容与签名验证、产物 provenance | 生成可核对来源的 ARM64 debug APK；没有运行登录、消息或文件流程 |
| Required suite gates | 检查上述四项状态都为 `success` | 任意失败、取消或跳过均使该汇总检查失败 |

建议在 `main` 的分支规则中将 **Required suite gates** 设为必需检查。工作流提供检查名称；分支规则需要仓库管理员在 GitHub 设置中配置。GitHub Release 发布同样依赖完整门禁。

在仓库根目录执行相同的本地命令：

```sh
python3 -m venv toolchains/ci-python
. toolchains/ci-python/bin/activate
python -m pip install --requirement docs/scripts/local_mtproto_smoke_requirements.txt
bash scripts/ci/check-static.sh
bash scripts/ci/check-server.sh affected
bash scripts/ci/check-server.sh full
python3 -W error::ResourceWarning -m unittest discover -s scripts/ci/tests -v
# 如已安装 actionlint，校验工作流语法及表达式：
actionlint -config-file scripts/ci/actionlint.yaml .github/workflows/*.yml
```

静态检查会真实执行 Docs 的 RSA/MTProto 测试，因此 CI 与本地都先安装固定版本的协议脚本依赖；仅配置 Python 不能满足这些测试。完整 Go suite 的媒体集成测试要求 PATH 中有 `ffmpeg` 和 `ffprobe`，Ubuntu CI 在运行前安装 `ffmpeg` 包。本地可用系统包管理器安装同一工具后再执行 full 命令。

`bash scripts/ci/check-server.sh full` 还要求 Docker 可用，并会拉取或复用 `mysql:8.0` 镜像。存量 schema 回归只在无宿主机端口、使用 tmpfs 数据目录的临时容器中创建旧版 `chat_invite_participants` 表，应用 `migrate-20261105.sql` 两次后检查既有数据与新列默认值；`affected` 模式不启动 Docker。另可用 `bash server/scripts/local-dev/check-sql-init.sh` 验证完整初始化 SQL，这同样只使用临时 MySQL 容器。

Go 版本从 `server/go.mod` 读取，当前为 `1.23.0`。2026-11-05 的本地验证使用 `golang:1.23.0` 容器和 FFmpeg/FFprobe 5.1.9；全量默认及 `privatechat_localtest` 测试、两种 tag 模式的完整 build 均通过。独立的 `go vet -p 2 ./...` 仍报告生成 TL codec 的 unreachable-code 及 `bff_proxy_client.go` 中未调用 context cancel 函数告警；CI 使用 `go test` 默认 vet 行为，此项 standalone vet 不属于门禁。关联范围包含 `pkg/localconfig`、`pkg/code/...`、`pkg/mtprotocompat`、configuration 的 `core`/`svc`，以及 account/messages/chatinvites 的 gRPC service。

完整 Go 测试曾发现的 bot username 断言、格式 vet、JPEG fixture、status mock 接口和 goffmpeg 集成问题已修复或改为使用自包含 fixture，并在上述两个模式中通过。线上 GitHub Actions 和 Release 仍需以各自实际运行记录为准；本地成功不等于线上工作流已执行。

## 原生构建环境

`scripts/ci/native_build.py` 要求根 Git 仓库具有完整的五组件提交、工作区干净、输出目录位于仓库外且为空；它会在构建后再次检查源码状态。发现构建失败、缺少产物、来源不匹配或源文件被修改时，不生成成功的 `build.json`。构建命令失败会保留非零退出码和 `build.log`，不会继续把旧产物作为成功包导出。

包装器使用公开的本地开发 dummy API ID `100001` 和对应的占位 hash，Android debug 签名 key 在临时目录中新建。它不读取操作员 API 身份、不启动客户端、不请求 OTP、不复制运行目录，也不为 App Store 或公网分发签名。新生成的 debug key 不适合升级已使用另一 debug key 安装的应用。

Android 自动构建在 Ubuntu 24.04 上使用 JDK 17、仓库 Gradle 8.7 wrapper、Android API 35、build-tools 35.0.0、NDK 27.2.12479018 与 CMake 3.10.2.4988404。执行的是 `:TMessagesProj_App:assembleAfatDebug -Pandroid.injected.build.abi=arm64-v8a`，输出为 `android-debug.apk` 和 `build.json`。Gradle 下载缓存由 `setup-java` 管理；缓存只加速构建，不代替构建步骤。

```sh
# ANDROID_SDK_ROOT 或 ANDROID_HOME 必须指向已安装上述版本的 SDK；PATH 中需有 JDK17。
python3 scripts/ci/native_build.py android --jobs 2 --output /tmp/private-chat-android-preview
```

`Apple native preview` 只允许手动触发，可选择 `desktop`、`ios` 或顺序构建两者。它需要标签为 `self-hosted, macOS, ARM64, private-chat-native` 的专用 Apple Silicon runner；该 runner 只运行可信分支的手动任务，不用于执行 pull request 代码。GitHub runner 至少为 2.327.1，以支持本工作流使用的 Node 24 actions。

Runner 必须预装并接受完整 Xcode 许可、准备 Command Line/Metal 工具，以及 Python3、CMake >=3.31、Ninja、Meson、autoconf、automake、libtool、pkg-config、nasm、wget、Git。iOS runner 还需安装源代码 `ios/versions.json` 固定的 Xcode 26.2 和适用的 simulator SDK。应为原生依赖和编译输出预留足够磁盘；本地双架构 Desktop 依赖和 `out` 曾占用约 60 GB，iOS/Bazel 还会额外占用空间。

Desktop 依赖脚本以 monorepo 根目录的 `Libraries/`、`ThirdParty/` 为缓存位置，与原项目要求的 `desktop/../Libraries` 布局一致。工作流保留这些忽略目录，依赖脚本自身的 cache keys 检查阶段；不会把大型依赖树上传成源码或 Release 资产。iOS 使用 `toolchains/ios-bazel-cache` 的内容缓存，键包含系统、架构、版本文件和提交；即使命中缓存，仍运行 project generation 和实际编译。各次输出目录包含 workflow run ID 与 attempt，避免重跑覆盖旧包。

```sh
python3 scripts/ci/native_build.py desktop --jobs 2 --output /tmp/private-chat-desktop-preview
python3 scripts/ci/native_build.py ios --jobs 2 --output /tmp/private-chat-ios-simulator-preview
```

所有线上原生任务共用 `private-chat-native` concurrency group，Android、Desktop 和 iOS 不会相互并发运行。每个 checkout 的本地包装器另有进程锁。Desktop 与 iOS 两个步骤顺序执行；前一个失败会保留失败状态，后一个不会假装成功。GitHub 的 concurrency 仅保存一个待运行任务，密集触发可能替换更早的排队任务，需查看实际 run 状态。

Desktop 只构建 Debug app，并严格验证其代码签名；不构建 Release 或声称已 notarize。iOS 只生成禁用扩展/配置文件的 simulator Debug app，编译时 `CODE_SIGNING_ALLOWED=NO`，导出前验证 `CFBundleSupportedPlatforms` 包含 `iPhoneSimulator`。导出的 `.app.tar.gz` 不是 IPA，不适用于真机安装或 App Store 上传。

## Xcode 27 本地兼容性证据

本机的 Xcode 27.2 与源码固定的 26.2 存在版本差异。Desktop 已通过局部构建参数完成 macOS Debug 编译：dependency preparation 使用临时 `XCODE_XCCONFIG_FILE` 将 Breakpad 的最低系统设为 12.0，配置增加 `CMAKE_OSX_DEPLOYMENT_TARGET=12.0`、`CMAKE_CXX_FLAGS=-DMETA_NO_STD_FORWARD_DECLARATIONS` 和同样的 `CMAKE_OBJCXX_FLAGS`。包装器在检测到 Xcode 27 时自动使用这些已复现的局部参数，保留原源码。

iOS 本地成功编译使用 `Make.py --overrideXcodeVersion`、`IPHONEOS_DEPLOYMENT_TARGET=15.0`，以及只作用于本地生成 Bazel 配置的精确诊断选项。对应源文件还修复了新编译器暴露的作用域导入和显式丢弃 Task 值问题。完整本地命令和各次真实退出码保存在 `integration/ios-progress.md`；原生构建成功和后续运行检查以该文件及 `integration/ios-runtime-progress.md` 的最新记录为准。

CI 的 iOS 包装器继续严格要求 `ios/versions.json` 固定的 Xcode 26.2，版本不同直接失败。上述 Xcode 27 本地兼容性证据不能被解释为固定版本 CI 已绿；也没有把本地诊断覆盖自动写入线上签名或发布流程。若正式升级工具链，应先在独立变更中审查 `versions.json`、依赖和全部原生构建证据。

## 可复现的候选资产

打包与验证是两个独立操作。`scripts/ci/package_preview.py` 只从一次解析得到的已提交 Git revision 取源码，不声称其已通过测试；本地可提前生成可审查候选，线上发布准备则必须经过全部门禁。打包会检查五组件源文件存在，并拒绝尚未展开的 gitlink。输出目录必须为空，失败不会留下可误认为成功 Release 的部分资产。

```sh
python3 scripts/ci/package_preview.py \
  --version v0.2.0-preview.1 --revision HEAD \
  --output /tmp/private-chat-v0.2.0-preview.1-source
cd /tmp/private-chat-v0.2.0-preview.1-source
shasum -a 256 -c SHA256SUMS
```

源码包包含五组件、根 CI 脚本/工作流与明确允许的根说明文件（包括 `repository-imports.json`）。它保留 Desktop `Telegram/build` 等构建源码以及嵌套测试 fixture，排除本地 `Libraries`/`ThirdParty`/`toolchains`/`integration`、服务端 data 与二进制产物、客户端运行目录、生成工程/构建输出、本地环境配置、签名 key/store/profile。意外独立 PEM 私钥内容会使打包直接失败。服务端配置仍使用 `server_pkcs1.key` 的相对路径；公开快照不携带该运行时密钥，部署者必须自行生成并同步配置客户端公钥。

源码 tar 的文件排序、UID/GID、权限、时间戳和 gzip header 都规范化。相同提交与版本会得到相同源码包字节；manifest 记录来源 commit、SOURCE_DATE_EPOCH、每个资产的大小/校验和及限制，`SHA256SUMS` 另包含 manifest 自身的校验和。原生产品包含工具链/签名差异，不宣称可复现。

可选原生资产只接受本包装器输出的匹配证据。`--android-apk`、`--desktop-app` 或 `--ios-simulator-app` 必须分别配合对应 `--android-provenance`、`--desktop-provenance`、`--ios-provenance`；其 commit、组件、preview 类型、干净源码状态、构建成功状态及产品 SHA-256 必须全部匹配。Apple 参数接收原始 `.app` 目录；如从工作流下载了 `.app.tar.gz`，先验算 `build.json` 中的 SHA-256，再解压到空目录并传入 `.app`。打包器会再次规范化并核对最终 archive 的 SHA-256。

```sh
python3 scripts/ci/package_preview.py \
  --version v0.2.0-preview.1 --revision VERIFIED_COMMIT \
  --android-apk /tmp/private-chat-android-preview/android-debug.apk \
  --android-provenance /tmp/private-chat-android-preview/build.json \
  --output /tmp/private-chat-v0.2.0-preview.1-with-android
```

历史的预合仓工作区产物和仅有日志的本地构建不能生成干净 monorepo provenance。它们可作为集成检查证据，不能绕过匹配提交的资产要求。

## GitHub Release 流程

`Release preview` 仅手动触发，默认 `publish=false`。它复用相同提交的完整 `CI`，成功后生成源码候选、manifest、SHA256SUMS 和明确限制的 release notes，再保存为 GitHub Actions artifact。工作流不附加原生 app，单独的 Android 和 Apple 构建 artifact 具有各自的来源证据。

需要实际发布时，仓库管理员应创建 `preview-release` environment，仅允许 `main` 部署，并在该 environment 设置 `PRIVATE_CHAT_RELEASE_ENABLED=true`。缺少该变量时发布步骤失败。可按仓库协作需要配置 required reviewers；它不是本工作流的默认强制要求。检查候选 artifact 后，以 `publish=true` 触发；该请求只允许 `shiyi-log/private-chat` 的 `main`。通过完整门禁及已配置的 environment 规则后，发布 job 才取得 `contents: write` 并创建 GitHub prerelease。已有同名 tag 必须指向被验证的同一提交，已有 Release 不会被覆盖。

用户已授权向公开的 `shiyi-log/private-chat` 推送筛选后的统一源码快照并发布预览版；快照已推送，但完整 Actions 门禁尚未通过，候选 artifact 核验与 prerelease 发布尚未执行。修复后的 CI 结果和后续 Release 应以对应线上运行记录为准。源码候选发布的范围须与 release notes 一致；真实短信、生产部署、真机签名与公证需要各自验证。

工作流行为和管理员设置依据 GitHub 官方的 [reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)、[environment protection rules](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) 和 [concurrency](https://docs.github.com/en/actions/how-tos/choose-when-workflows-run/control-workflow-concurrency) 文档。各 action 使用 2026-11-05 核对的上游 tag 对应完整 commit SHA，升级时应同时检查其 runner 最低版本。
