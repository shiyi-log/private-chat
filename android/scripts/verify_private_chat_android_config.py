#!/usr/bin/env python3
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def record(checks, ok, message):
    checks.append((ok, message))


def parse_properties(text):
    values = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_string_value(xml_text, name):
    root = ET.fromstring(xml_text)
    for item in root.findall("string"):
        if item.get("name") == name:
            return item.text or ""
    return ""


def google_package_names(relative_path):
    data = json.loads(read_text(relative_path))
    names = []
    for client in data.get("client", []):
        info = client.get("client_info", {}).get("android_client_info", {})
        package_name = info.get("package_name")
        if package_name:
            names.append(package_name)
    return names


def main():
    checks = []

    props_path = "gradle.properties"
    props = parse_properties(read_text(props_path))
    record(checks, props.get("APP_PACKAGE") == "com.privatechat.messenger", f"{props_path}：APP_PACKAGE 应为 com.privatechat.messenger")
    record(checks, props.get("APP_VERSION_NAME") == "12.7.3", f"{props_path}：APP_VERSION_NAME 应为当前基线 12.7.3")

    app_gradle_path = "TMessagesProj_App/build.gradle"
    app_gradle = read_text(app_gradle_path)
    record(checks, "defaultConfig.applicationId = APP_PACKAGE" in app_gradle, f"{app_gradle_path}：applicationId 应来自 APP_PACKAGE")
    record(checks, 'applicationIdSuffix ".beta"' in app_gradle, f"{app_gradle_path}：Debug/Beta 后缀应为 .beta")
    record(checks, 'applicationIdSuffix ".web"' in app_gradle, f"{app_gradle_path}：Standalone 后缀应为 .web")
    record(checks, 'namespace \'org.telegram.messenger.regular\'' in app_gradle, f"{app_gradle_path}：内部 namespace 暂保留以匹配源码包路径")

    expected_packages = {
        "com.privatechat.messenger",
        "com.privatechat.messenger.beta",
        "com.privatechat.messenger.web",
    }
    library_google_path = "TMessagesProj/google-services.json"
    library_packages = set(google_package_names(library_google_path))
    record(checks, expected_packages.issubset(library_packages), f"{library_google_path}：应包含 Private Chat 三个对外包名")
    record(checks, "org.telegram.messenger" in library_packages, f"{library_google_path}：库模块需保留 org.telegram.messenger 内部构建匹配项")

    app_google_path = "TMessagesProj_App/google-services.json"
    app_packages = set(google_package_names(app_google_path))
    record(checks, expected_packages.issubset(app_packages), f"{app_google_path}：应包含 Private Chat 三个对外包名")
    record(checks, "org.telegram.messenger" not in app_packages, f"{app_google_path}：不应保留旧 org.telegram.messenger 对外包名")

    strings_path = "TMessagesProj/src/main/res/values/strings.xml"
    strings_text = read_text(strings_path)
    record(checks, get_string_value(strings_text, "AppName") == "Private Chat", f"{strings_path}：AppName 应为 Private Chat")
    record(checks, get_string_value(strings_text, "AppNameBeta") == "Private Chat Beta", f"{strings_path}：AppNameBeta 应为 Private Chat Beta")
    for key in ("SentAppCode", "SentAppCodeWithPhone", "SentAppCodeTitle", "SentCallCode", "CallText", "OtherLoginCode", "AllowReadCall", "InviteToTelegram"):
        record(checks, "private chat" in get_string_value(strings_text, key).lower(), f"{strings_path}：{key} 应包含 Private Chat")
    high_visibility_private_keys = (
        "DidNotGetTheCodeInfo",
        "CancelAccountResetInfo2",
        "GotAQuestion",
        "ContactJoined",
        "LanguageUnknownCustomAlert",
        "AskAQuestionInfo",
        "TelegramFAQ",
        "TelegramFaq",
        "TelegramFeatures",
        "NotificationsServiceConnectionInfo",
        "AuthAnotherClientInfo1",
        "AuthAnotherClientInfo2",
        "AuthAnotherClientUrl",
        "QRCodePermissionNoCameraWithHint",
        "AppUpdate",
        "AppUpdateBeta",
        "NotificationContactJoined",
        "NotificationUnrecognizedDevice",
        "NotificationHiddenName",
        "NotificationHiddenChatName",
        "InviteText2",
    )
    for key in high_visibility_private_keys:
        value = get_string_value(strings_text, key)
        record(checks, "private chat" in value.lower(), f"{strings_path}：{key} 应包含 Private Chat")
        record(checks, "telegram" not in value.lower(), f"{strings_path}：{key} 不应继续显示 Telegram")
    system_entry_private_keys = (
        "SecretChatName",
        "ChangePasscodeInfo",
        "EnterYourPasscodeInfo",
        "EnterYourTelegramPasscode",
        "StorageUsageTelegram",
        "StorageUsageTelegramLess",
        "StorageCleared2",
        "StorageUsageInfo",
        "IncomingCallsSystemSettingDescription",
        "PermissionStorageWithHint",
        "PermissionNoAudioWithHint",
        "PermissionNoBluetoothWithHint",
        "PermissionNoAudioVideoWithHint",
        "PermissionNoCameraWithHint",
        "PermissionNoCameraMicVideo",
        "PermissionNoLocation",
        "PermissionNoLocationStory",
        "PermissionNoLocationFriends",
        "PermissionNoLocationNavigation",
        "PermissionNoContactsSharing",
        "PermissionNoContactsSaving",
        "PermissionNoStorageAvatar",
        "PermissionNoAudioStorageStory",
        "PermissionDrawAboveOtherApps",
        "PermissionDrawAboveOtherAppsGroupCall",
        "PermissionXiaomiLockscreen",
        "PermissionFSILockscreen",
        "PermissionBackgroundLocation",
        "UnlockToUse",
        "AppLocked",
    )
    for key in system_entry_private_keys:
        value = get_string_value(strings_text, key)
        record(checks, "private chat" in value.lower(), f"{strings_path}：{key} 应包含 Private Chat")
        record(checks, "telegram" not in value.lower(), f"{strings_path}：{key} 不应继续显示 Telegram")
    account_invite_private_keys = (
        "PhoneNumberHelp",
        "ChangePhoneNumberOccupied",
        "UseProxySponsorInfo",
        "UseProxyTelegramInfo2",
        "AddAnotherAccountInfo",
        "CheckPhoneNumberInfo",
        "UpdateTelegram",
        "UpdateAppAlert",
        "EmailLoginChangeMessage",
        "NoMailInstalled",
        "InviteUser",
        "AreYouSureLogout",
        "NoUsernameFound",
        "NoPhoneFound",
        "AuthAnotherClientInfo4",
        "AuthAnotherClientInfo5",
        "SessionsListInfo",
        "TelegramContacts_one",
        "TelegramContacts_other",
        "InviteTextNum_one",
        "InviteTextNum_other",
        "InviteToTelegramShort",
        "NoUsernameFound2",
    )
    for key in account_invite_private_keys:
        value = get_string_value(strings_text, key)
        record(checks, "private chat" in value.lower(), f"{strings_path}：{key} 应包含 Private Chat")
        record(checks, "telegram" not in value.lower(), f"{strings_path}：{key} 不应继续显示 Telegram")
    general_experience_private_keys = (
        "PaymentWarningText",
        "ImportImportingInfo",
        "ImportDoneInfo",
        "GroupUserLeftError",
        "ChannelAntiSpamUser",
        "ChannelAntiSpamInfo",
        "ChannelAntiSpamFalsePositiveReported",
        "ChannelLinkInfo",
        "ChannelUserLeftError",
        "BotPermissionGameAlert",
        "BlockUserAlert",
        "ReportSentInfo",
        "BlockUserMessage",
        "BlockUsersMessage",
        "EncryptionKeyDescription",
        "UsernameHelp",
        "ImportStickersDoneInfo",
        "CreateNewThemeAlert",
        "ProfilePopupNotificationInfo",
        "SecretWebPageInfo",
        "TelegramVersion",
        "LowDiskSpaceMessage",
        "EnableAllStreamingInfo",
        "ClearingCacheDescription",
        "LocalDatabaseInfo",
        "WebSessionsTitle",
        "TerminateWebSessionInfo",
        "AreYouSureWebSessions",
        "ClearOtherWebSessionsHelp",
        "ScreenCaptureAlert",
        "RecoveryEmailSubtitle",
        "YourEmailSkipWarningText",
        "EnabledPasswordText",
        "PrivacyPhoneInfo",
        "PrivacyPhoneInfo3",
        "PrivacyPaymentsClearAlert",
        "PrivacyBotsInfo",
        "PrivacyCallsP2PHelp",
        "SyncContactsDeleteText",
        "UnsupportedMedia2",
        "SecretLinkPreviewAlert",
        "ClearTelegramCache",
        "TelegramCacheSize",
        "LocalDatabaseSize",
        "VoipInCallBranding",
        "VoipInVideoCallBranding",
        "VoipInConferenceCallBranding",
        "VoipOutgoingCall",
        "VoipRingtoneInfo",
        "VoipPeerVideoOutdated",
        "VoipRateCallAlert",
        "VoipNeedMicPermissionWithHint",
        "VoipNeedMicCameraPermissionWithHint",
        "VoipNeedCameraPermission",
        "CallViaTelegram",
        "VideoCallViaTelegram",
        "VoiceCallViaTelegram",
        "CallReportSent",
        "VoipQuickRepliesExplain",
        "VoipInCallBrandingWithName",
        "VoipInVideoCallBrandingWithName",
        "VoipErrorUnknown",
        "PrimaryLinkHelp",
        "PrimaryLinkHelpChannel",
        "OptimizingTelegram",
        "MigrateOldFolderDescription",
        "AllowBackgroundActivityInfo",
        "AllowBackgroundActivityInfoOneUIBelowS",
        "AllowBackgroundActivityInfoOneUIAboveS",
        "DownloadedFilesMessage",
        "CreatePasscodeInfoPIN",
        "CreatePasscodeInfoPassword",
        "MapPreviewProviderTelegram",
        "TelegramPassport",
        "PassportInfoTitle",
        "PassportInfo2",
        "TelegramPassportCreatePasswordInfo",
        "TelegramPassportDelete",
        "TelegramPassportDeleteTitle",
        "TelegramPassportDeleteAlert",
        "PassportPhoneUseSameInfo",
        "PassportPhoneUseSameEmailInfo",
        "PassportRequestPasswordInfo",
        "TurnPasswordOffPassport",
        "PleaseLoginPassport",
        "VoipVideoNotAvailableAdmin",
        "VoipChannelVideoNotAvailableAdmin",
        "NoRtmpStreamFromAppOwner",
        "NoRtmpStreamFromAppViewer",
        "SessionsSettingsInfo",
        "LoginEmailResetMessage",
        "SdCardAlert",
        "SdCardErrorDescription",
        "StoryUnsupported",
        "UnconfirmedAuthDeniedWarning",
        "CallAvailableIn2",
        "OpenInTelegramBrowser",
        "BrowserSettingsCustomTabs",
        "BrowserSettingsNoCustomTabsInfo",
        "BrowserSettingsEnableInfo",
        "BrowserSettingsCookiesInfo",
        "BrowserSettingsNeverOpenInInfo",
        "BrowserExternalRestricted",
        "ProfileUnofficialSecurityRisk",
        "Reported2",
        "BotLocationPermissionRequestDeniedApp",
        "AccountFrozen1Text",
        "SMSFee1Text",
        "SMSFee1TextCountry",
        "SMSFee2Text",
        "GroupCallLinkText",
        "GroupCallCreatedLinkText",
        "BotRestoreStorageText",
        "AgeVerificationTextGB",
        "AgeVerificationNeedCameraPermission",
        "SearchPostsHeaderNews",
        "EmojiSuggestionsInfo",
        "StarRatingDescription",
        "StarRatingSelfDescription",
    )
    for key in general_experience_private_keys:
        value = get_string_value(strings_text, key)
        record(checks, "private chat" in value.lower(), f"{strings_path}：{key} 应包含 Private Chat")
        record(checks, "telegram" not in value.lower(), f"{strings_path}：{key} 不应继续显示 Telegram")
    private_url_keys = (
        "TelegramFeaturesUrl",
        "TelegramFaqUrl",
        "PrivacyPolicyUrl",
        "TermsOfServiceUrl",
        "WebAppDisclaimerUrl",
        "BotWebViewToSLink",
        "BotWebViewStartPermissionLink",
        "ProfileBotOpenAppInfoLink",
        "ProfileBotOpenAppInfoOwnerLink",
        "AuthAnotherClientDownloadClientUrl",
        "AuthAnotherWebClientUrl",
        "CheckPhoneNumberLearnMoreUrl",
        "EncryptionKeyLink",
        "PassportInfoUrl",
        "BotDefaultPrivacyPolicy",
        "EmojiSuggestionsUrl",
    )
    for key in private_url_keys:
        value = get_string_value(strings_text, key)
        record(checks, value.startswith("https://privatechat.local/"), f"{strings_path}：{key} 应指向 privatechat.local 占位域名")
        record(checks, "telegram.org" not in value and "t.me" not in value, f"{strings_path}：{key} 不应继续指向官方域名")
    private_link_example_keys = (
        "GroupDescription3",
        "PublicLinksLimitSubtitle",
    )
    for key in private_link_example_keys:
        value = get_string_value(strings_text, key)
        record(checks, "privatechat.local" in value, f"{strings_path}：{key} 应使用 privatechat.local 链接示例")
        record(checks, "t.me" not in value, f"{strings_path}：{key} 不应继续使用 t.me 链接示例")
    record(checks, get_string_value(strings_text, "NoChats") == "Welcome to Private Chat", f"{strings_path}：NoChats 应为 Welcome to Private Chat")
    policy_webapp_private_keys = (
        "TosDecline",
        "TosUpdateDecline",
        "TosDeclineDeleteAccount",
        "BotWebAppDisclaimerSubtitle",
        "ProfileBotOpenAppInfoOwner",
    )
    for key in policy_webapp_private_keys:
        value = get_string_value(strings_text, key)
        record(checks, "private chat" in value.lower(), f"{strings_path}：{key} 应包含 Private Chat")
        record(checks, "telegram" not in value.lower() and "telegram.org" not in value.lower(), f"{strings_path}：{key} 不应继续显示 Telegram 或官方链接")

    buildvars_path = "TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java"
    buildvars = read_text(buildvars_path)
    record(checks, "PUSH_SERVICES_ENABLED = false" in buildvars, f"{buildvars_path}：私有构建默认应禁用第三方推送 token 获取")
    record(checks, "SUPPORTS_PASSKEYS = false" in buildvars, f"{buildvars_path}：私有 API 身份不支持官方 Passkey 登录，应默认禁用")
    record(checks, '"com.privatechat.messenger.beta".equals' in buildvars, f"{buildvars_path}：Beta 包名判断应使用 com.privatechat.messenger.beta")
    record(checks, '"org.telegram.messenger.beta".equals' not in buildvars, f"{buildvars_path}：不应继续用旧 Beta 包名判断")

    application_loader_path = "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java"
    application_loader = read_text(application_loader_path)
    record(checks, "__PRIVATE_PUSH_DISABLED__" in application_loader, f"{application_loader_path}：启动时应写入私有推送禁用状态")
    record(checks, "!BuildVars.PUSH_SERVICES_ENABLED" in application_loader, f"{application_loader_path}：启动推送服务前应检查私有推送开关")
    record(checks, "Push services are disabled for Private Chat build." in application_loader, f"{application_loader_path}：应记录私有构建跳过推送初始化")

    notifications_controller_path = "TMessagesProj/src/main/java/org/telegram/messenger/NotificationsController.java"
    notifications_controller = read_text(notifications_controller_path)
    record(checks, '"Private Chat internal notifications"' in notifications_controller, f"{notifications_controller_path}：内部通知渠道名应使用 Private Chat")
    record(checks, '"Internal notifications"' not in notifications_controller, f"{notifications_controller_path}：内部通知渠道名不应继续使用通用默认名称")

    push_controller_path = "TMessagesProj/src/main/java/org/telegram/messenger/PushListenerController.java"
    push_controller = read_text(push_controller_path)
    record(checks, "FCM token request skipped for Private Chat build." in push_controller, f"{push_controller_path}：FCM token 获取应可被私有开关跳过")
    record(checks, "__PRIVATE_PUSH_DISABLED__" in push_controller, f"{push_controller_path}：FCM 跳过时应写入私有推送禁用状态")

    gcm_service_path = "TMessagesProj/src/main/java/org/telegram/messenger/GcmPushListenerService.java"
    gcm_service = read_text(gcm_service_path)
    record(checks, "FCM message ignored because push services are disabled." in gcm_service, f"{gcm_service_path}：私有构建应忽略 FCM 消息回调")
    record(checks, "FCM token ignored because push services are disabled." in gcm_service, f"{gcm_service_path}：私有构建应忽略 FCM token 回调")

    huawei_loader_path = "TMessagesProj_AppHuawei/src/main/java/org/telegram/messenger/HuaweiApplicationLoader.java"
    huawei_loader = read_text(huawei_loader_path)
    record(checks, "HmsMessaging.getInstance(this).setAutoInitEnabled(false)" in huawei_loader, f"{huawei_loader_path}：私有构建应关闭 HMS 自动初始化")
    record(checks, "FirebaseMessaging.getInstance().setAutoInitEnabled(false)" in huawei_loader, f"{huawei_loader_path}：私有构建应关闭 FCM 自动初始化")

    huawei_provider_path = "TMessagesProj_AppHuawei/src/main/java/org/telegram/messenger/HuaweiPushListenerProvider.java"
    huawei_provider = read_text(huawei_provider_path)
    record(checks, "HMS token request skipped for Private Chat build." in huawei_provider, f"{huawei_provider_path}：HMS token 获取应可被私有开关跳过")

    huawei_service_path = "TMessagesProj_AppHuawei/src/main/java/org/telegram/messenger/HuaweiPushListenerService.java"
    huawei_service = read_text(huawei_service_path)
    record(checks, "HCM message ignored because push services are disabled." in huawei_service, f"{huawei_service_path}：私有构建应忽略 HCM 消息回调")
    record(checks, "HCM token ignored because push services are disabled." in huawei_service, f"{huawei_service_path}：私有构建应忽略 HCM token 回调")

    conn_path = "TMessagesProj/jni/tgnet/ConnectionsManager.cpp"
    conn = read_text(conn_path)
    official_dc_pattern = re.compile(r"\b(149\.154|91\.108)\.\d+\.\d+\b")
    record(checks, conn.count('new Datacenter(instanceNum, 1)') >= 2, f"{conn_path}：生产和测试默认 DC 应收敛到 DC 1")
    record(checks, conn.count('addAddressAndPort("10.0.2.2", 10443, 0, "")') >= 2, f"{conn_path}：模拟器私有 DC 应指向 10.0.2.2:10443")
    record(checks, "currentDatacenterId = 1;" in conn, f"{conn_path}：未登录默认 DC 应初始化为 1")
    record(checks, "auto iter = datacenters.find(datacenterId);" in conn and "return iter != datacenters.end() ? iter->second : nullptr;" in conn, f"{conn_path}：DEFAULT_DATACENTER_ID 查询应避免 map[] 插入空指针")
    record(checks, "if (allDc.empty())" in conn and "no alternative dc" in conn, f"{conn_path}：单 DC 情况应跳过随机切换备用 DC")
    record(checks, official_dc_pattern.search(conn) is None, f"{conn_path}：不应保留官方 DC IP")

    handshake_path = "TMessagesProj/jni/tgnet/Handshake.cpp"
    handshake = read_text(handshake_path)
    datacenter_path = "TMessagesProj/jni/tgnet/Datacenter.cpp"
    datacenter = read_text(datacenter_path)
    record(checks, "-----BEGIN RSA PUBLIC KEY-----" in handshake, f"{handshake_path}：握手 RSA 公钥应存在")
    record(checks, "-----BEGIN RSA PUBLIC KEY-----" in datacenter, f"{datacenter_path}：simple config RSA 公钥应存在")

    readme_path = "README.md"
    readme = read_text(readme_path)
    record(checks, readme.startswith("# Private Chat Android 安卓端"), f"{readme_path}：应使用 Private Chat 中文优先说明")
    record(checks, "official Telegram Android distribution" in readme, f"{readme_path}：应包含英文摘要说明非官方 Telegram 发布")

    failed = [message for ok, message in checks if not ok]
    passed_count = len(checks) - len(failed)

    if failed:
        print(f"Android 私有化配置验证失败：{passed_count}/{len(checks)} 项通过")
        for message in failed:
            print(f"- {message}")
        return 1

    print(f"Android 私有化配置验证通过：{passed_count}/{len(checks)} 项通过")
    print("- 对外包名、应用名和默认英文登录入口已指向 Private Chat")
    print("- 默认英文帮助、通知、QR 登录和更新入口已纳入高可见品牌门禁")
    print("- 默认英文权限、锁屏、存储、Passcode 和通话通知渠道说明已纳入系统入口品牌门禁")
    print("- 默认英文账号、邀请、会话和版本更新入口已纳入品牌门禁")
    print("- 默认英文通用体验、隐私安全、缓存、通话和导入入口已纳入品牌门禁")
    print("- 私有构建默认禁用 Firebase/Huawei 推送 token 获取，避免未配置第三方服务时报错")
    print("- 库模块保留 org.telegram.messenger 内部构建匹配项，最终 App 模块不保留旧对外包名")
    print("- 模拟器私有 DC 已指向 10.0.2.2:10443，单 DC 防御逻辑存在")
    print("- 当前验证是静态配置验证；真机/公网测试仍需要替换服务端地址和发布证书")
    return 0


if __name__ == "__main__":
    sys.exit(main())
