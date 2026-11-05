#!/usr/bin/env python3
import json
import plistlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def record(checks, ok, message):
    checks.append((ok, message))


def parse_xcconfig(text):
    values = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def has_placeholder(value):
    return isinstance(value, str) and value.startswith("{!") and value.endswith("!}")


def has_local_development_api_id(value):
    return isinstance(value, str) and value.isdigit()


def has_local_development_api_hash(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{32}", value))


def has_local_development_team_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z0-9]{10}", value))


def parse_strings_file(text):
    values = {}
    pattern = re.compile(r'"((?:\\.|[^"\\])*)"\s*=\s*"((?:\\.|[^"\\])*)";')
    for match in pattern.finditer(text):
        key = decode_apple_string(match.group(1))
        value = decode_apple_string(match.group(2))
        values[key] = value
    return values


def decode_apple_string(value):
    return (
        value.replace("\\n", "\n")
        .replace("\\\"", "\"")
        .replace("\\'", "'")
        .replace("\\\\", "\\")
    )


def main():
    checks = []

    xcodeproj_template_path = "build-system/bazel-rules/rules_xcodeproj/xcodeproj/internal/templates/xcodeproj.bazelrc"
    record(checks, (ROOT / xcodeproj_template_path).is_file(), f"{xcodeproj_template_path}：生成 Xcode 工程所需的依赖模板应存在")

    template_path = "build-system/template_minimal_development_configuration.json"
    template = json.loads(read_text(template_path))
    record(checks, template.get("bundle_id") == "com.privatechat.ios", f"{template_path}：bundle_id 应为 com.privatechat.ios")
    record(checks, template.get("app_specific_url_scheme") == "privatechat", f"{template_path}：app_specific_url_scheme 应为 privatechat")
    record(checks, has_local_development_api_id(template.get("api_id")), f"{template_path}：api_id 应为可生成工程的本地开发数字值")
    record(checks, has_local_development_api_hash(template.get("api_hash")), f"{template_path}：api_hash 应为可生成工程的本地开发 32 位十六进制值")
    record(checks, has_local_development_team_id(template.get("team_id")), f"{template_path}：team_id 应为可生成工程的本地开发 10 位团队标识")

    for release_config_path in (
        "build-system/appstore-configuration.json",
        "build-system/appcenter-configuration.json",
    ):
        release_config = json.loads(read_text(release_config_path))
        record(checks, release_config.get("bundle_id") == "com.privatechat.ios", f"{release_config_path}：bundle_id 应为 com.privatechat.ios")
        record(checks, release_config.get("app_specific_url_scheme") == "privatechat", f"{release_config_path}：URL Scheme 应为 privatechat")
        record(checks, release_config.get("appstore_id") == "0", f"{release_config_path}：App Store ID 应为私有占位值 0")
        record(checks, release_config.get("app_center_id") == "0", f"{release_config_path}：AppCenter ID 应为私有占位值 0")
        record(checks, release_config.get("premium_iap_product_id") == "", f"{release_config_path}：Premium IAP 产品 ID 应为空")
        record(checks, release_config.get("enable_siri") is False, f"{release_config_path}：未配置正式私有能力前应关闭 Siri")
        record(checks, release_config.get("enable_icloud") is False, f"{release_config_path}：未配置正式私有能力前应关闭 iCloud")
        release_config_text = read_text(release_config_path)
        record(checks, "ph.telegra.Telegraph" not in release_config_text, f"{release_config_path}：不应继续使用上游 Bundle ID")
        record(checks, "686449807" not in release_config_text, f"{release_config_path}：不应继续使用上游 App Store ID")
        record(checks, "org.telegram.telegramPremium" not in release_config_text, f"{release_config_path}：不应继续使用上游 Premium IAP ID")

    release_verify_path = "build-system/verify.sh"
    release_verify_text = read_text(release_verify_path)
    release_verify_expected_values = (
        'export BUNDLE_ID="com.privatechat.ios"',
        'export IS_INTERNAL_BUILD="true"',
        'export IS_APPSTORE_BUILD="false"',
        'export APPSTORE_ID="0"',
        'export APP_SPECIFIC_URL_SCHEME="privatechat"',
        'export PREMIUM_IAP_PRODUCT_ID=""',
        "match Development com.privatechat.ios",
        "match AppStore com.privatechat.ios",
    )
    for expected_value in release_verify_expected_values:
        record(checks, expected_value in release_verify_text, f"{release_verify_path}：应包含私有发布占位配置 {expected_value}")
    release_verify_forbidden_values = (
        "Digital Fortress",
        "C67CF9S4VU",
        "ph.telegra.Telegraph",
        "686449807",
        "tgapp",
        "org.telegram.telegramPremium",
    )
    for forbidden_value in release_verify_forbidden_values:
        record(checks, forbidden_value not in release_verify_text, f"{release_verify_path}：不应继续包含上游发布身份 {forbidden_value}")

    xcconfig_path = "Telegram/Telegram-iOS/Config-Fork.xcconfig"
    xcconfig = parse_xcconfig(read_text(xcconfig_path))
    record(checks, xcconfig.get("APP_NAME") == "Private Chat", f"{xcconfig_path}：APP_NAME 应为 Private Chat")
    record(checks, xcconfig.get("APP_BUNDLE_ID") == "com.privatechat.ios", f"{xcconfig_path}：APP_BUNDLE_ID 应为 com.privatechat.ios")
    record(checks, xcconfig.get("APP_SPECIFIC_URL_SCHEME") == "privatechat", f"{xcconfig_path}：APP_SPECIFIC_URL_SCHEME 应为 privatechat")

    info_plist_path = "Telegram/Telegram-iOS/Info.plist"
    with (ROOT / info_plist_path).open("rb") as handle:
        info = plistlib.load(handle)

    url_schemes = []
    for item in info.get("CFBundleURLTypes", []):
        url_schemes.extend(item.get("CFBundleURLSchemes", []))
    record(checks, "privatechat" in url_schemes, f"{info_plist_path}：URL Scheme 应包含 privatechat")
    record(checks, "telegram" not in url_schemes, f"{info_plist_path}：URL Scheme 不应再包含显式 telegram")

    permission_keys = [
        "NSContactsUsageDescription",
        "NSLocationAlwaysUsageDescription",
        "NSLocationWhenInUseUsageDescription",
        "NSMotionUsageDescription",
    ]
    for key in permission_keys:
        record(checks, "Private Chat" in info.get(key, ""), f"{info_plist_path}：{key} 应包含 Private Chat")

    theme_types = info.get("UTImportedTypeDeclarations", [])
    theme_identifiers = [item.get("UTTypeIdentifier") for item in theme_types]
    theme_descriptions = [item.get("UTTypeDescription", "") for item in theme_types]
    record(checks, "com.privatechat.ios.theme" in theme_identifiers, f"{info_plist_path}：主题 UTI 应为 com.privatechat.ios.theme")
    record(checks, any("Private Chat" in value for value in theme_descriptions), f"{info_plist_path}：主题文件说明应包含 Private Chat")

    build_path = "Telegram/BUILD"
    build_text = read_text(build_path)
    record(checks, "<string>Private Chat</string>" in build_text, f"{build_path}：实际构建用 Info.plist 片段应显示 Private Chat")
    record(checks, "<string>com.privatechat.ios.theme</string>" in build_text, f"{build_path}：实际构建用主题 UTI 应为 com.privatechat.ios.theme")
    record(checks, "Telegram stores your contacts" not in build_text, f"{build_path}：实际构建用权限说明不应继续显示 Telegram")
    record(checks, "<string>Telegram</string>" not in build_text, f"{build_path}：扩展构建用 CFBundleName 不应继续显示 Telegram")
    build_forbidden_release_values = (
        "merchant.ph.telegra.Telegraph",
        "org.telegram.Telegram-iOS",
        "ph.telegra.Telegraph",
        "merchant.org.telegram",
    )
    for forbidden_value in build_forbidden_release_values:
        record(checks, forbidden_value not in build_text, f"{build_path}：不应继续包含上游发布身份 {forbidden_value}")
    main_plist_match = re.search(
        r'name\s*=\s*"TelegramInfoPlist".*?<key>CFBundleDisplayName</key>\s*<string>Private Chat</string>.*?<key>CFBundleName</key>\s*<string>Private Chat</string>',
        build_text,
        re.S,
    )
    record(checks, main_plist_match is not None, f"{build_path}：主 App 产物显示名应为 Private Chat")

    share_path = "Telegram/Share/en.lproj/Localizable.strings"
    share_text = read_text(share_path)
    record(checks, 'Share.AuthTitle" = "Log in to Private Chat"' in share_text, f"{share_path}：分享扩展登录标题应包含 Private Chat")
    record(checks, 'Share.AuthDescription" = "Open Private Chat and log in to share."' in share_text, f"{share_path}：分享扩展登录说明应包含 Private Chat")

    strings_path = "Telegram/Telegram-iOS/en.lproj/Localizable.strings"
    strings = parse_strings_file(read_text(strings_path))
    default_english_private_keys = (
        "Tour.Title1",
        "Tour.Text1",
        "Tour.Text2",
        "Tour.Text3",
        "Tour.Text4",
        "Tour.Text5",
        "Tour.Text6",
        "Login.CodeSentInternal",
        "Login.WillCallYou",
        "Login.CallRequestState2",
        "Login.CallRequestState3",
        "Login.EmailCodeBody",
        "Login.InvalidPhoneEmailBody",
        "Login.PhoneBannedEmailBody",
        "Login.PhoneGenericEmailSubject",
        "Login.PhoneGenericEmailBody",
        "Contacts.AccessDeniedError",
        "Contacts.AccessDeniedHelpLandscape",
        "Contacts.AccessDeniedHelpPortrait",
        "Contacts.InviteToTelegram",
        "Conversation.UnsupportedMedia",
        "Notification.Joined",
        "Notification.NewAuthDetected",
        "Profile.CreateEncryptedChatOutdatedError",
        "UserInfo.Invite",
        "EncryptionKey.Description",
        "Settings.FAQ",
        "Settings.FAQ_Intro",
        "Cache.Help",
        "Settings.LogoutConfirmationText",
        "Login.PadPhoneHelp",
        "Compatibility.SecretMediaVersionTooLow",
        "Username.Help",
        "PhoneNumberHelp.Help",
        "PhoneNumberHelp.Alert",
        "ChangePhoneNumberCode.CallTimer",
        "ChangePhoneNumberCode.RequestingACall",
        "ChangePhoneNumberCode.Called",
        "ShareFileTip.Text",
        "Username.LinkHint",
        "PasscodeSettings.EncryptDataHelp",
        "EnterPasscode.EnterTitle",
        "EnterPasscode.EnterPasscode",
        "EnterPasscode.TouchId",
        "DialogList.PasscodeLockHelp",
        "AccessDenied.Contacts",
        "AccessDenied.VoiceMicrophone",
        "AccessDenied.VideoMicrophone",
        "AccessDenied.MicrophoneRestricted",
        "AccessDenied.Camera",
        "AccessDenied.CameraRestricted",
        "AccessDenied.PhotosAndVideos",
        "AccessDenied.SaveMedia",
        "AccessDenied.PhotosRestricted",
        "AccessDenied.LocationDenied",
        "AccessDenied.LocationDisabled",
        "AccessDenied.LocationTracking",
        "TwoStepAuth.GenericHelp",
        "TwoStepAuth.EmailSkipAlert",
        "Conversation.FileHowToText",
        "ChangePhone.ErrorOccupied",
        "AuthSessions.EmptyText",
        "GroupInfo.InviteLink.Help",
        "Watch.AppName",
        "Watch.Notification.Joined",
        "Watch.Location.Access",
        "Watch.AuthRequired",
        "Watch.Microphone.Access",
        "Conversation.SecretLinkPreviewAlert",
        "Conversation.BotInteractiveUrlAlert",
        "Widget.AuthRequired",
        "Widget.GalleryTitle",
        "AccessDenied.CallMicrophone",
        "Application.Name",
        "Calls.RatingTitle",
        "Call.StatusIncoming",
        "Call.StatusOngoing",
        "Call.PhoneCallInProgressMessage",
        "UserInfo.TelegramCall",
        "UserInfo.TelegramVideoCall",
        "AccessDenied.VideoMessageCamera",
        "AccessDenied.VideoMessageMicrophone",
        "Privacy.PaymentsClearInfoHelp",
        "Contacts.ShareTelegram",
        "Privacy.Calls.P2PHelp",
        "Privacy.Calls.IntegrationHelp",
        "Contacts.ImportersCount_1",
        "Contacts.ImportersCount_2",
        "Contacts.ImportersCount_3_10",
        "Contacts.ImportersCount_any",
        "Contacts.ImportersCount_many",
        "Contacts.ImportersCount_0",
        "InviteText.URL",
        "InviteText.SingleContact",
        "InviteText.ContactsCountText_1",
        "InviteText.ContactsCountText_2",
        "InviteText.ContactsCountText_3_10",
        "InviteText.ContactsCountText_any",
        "InviteText.ContactsCountText_many",
        "InviteText.ContactsCountText_0",
        "InfoPlist.NSContactsUsageDescription",
        "InfoPlist.NSLocationWhenInUseUsageDescription",
        "InfoPlist.NSLocationAlwaysAndWhenInUseUsageDescription",
        "InfoPlist.NSLocationAlwaysUsageDescription",
        "ClearCache.StorageCache",
        "ClearCache.StorageServiceFiles",
        "ClearCache.ClearCache",
        "AuthSessions.AddDeviceIntro.Text1",
        "AuthSessions.AddDeviceIntro.Text2",
        "Map.HomeAndWorkInfo",
        "AuthSessions.OtherDevices",
        "AuthSessions.AddDevice.UrlLoginHint",
        "AuthSessions.HeaderInfo",
        "AuthSessions.AddDevice.ScanInstallInfo",
        "ClearCache.ClearDescription",
        "AccessDenied.QrCode",
        "AccessDenied.QrCamera",
        "InviteLink.CreatePrivateLinkHelp",
        "InviteLink.CreatePrivateLinkHelpChannel",
        "InviteLink.QRCode.Info",
        "InviteLink.QRCode.InfoChannel",
        "ChatImportActivity.OpenApp",
        "Report.Succeed",
        "Intents.ErrorLockedText",
        "Channel.AddUserLeftError",
        "Checkout.PaymentLiabilityAlert",
        "Settings.Tips",
        "Settings.TipsUsername",
        "PrivacyPhoneNumberSettings.CustomPublicLink",
        "DownloadList.ClearAlertText",
        "Passport.Phone.UseTelegramNumberHelp",
        "Passport.Email.UseTelegramEmailHelp",
        "Notifications.TelegramTones",
        "Login.EnterCodeTelegramText",
        "Chat.Context.Phone.TelegramVoiceCall",
        "Chat.Context.Phone.TelegramVideoCall",
        "Chat.Context.Phone.InviteToTelegram",
        "Chat.Context.Phone.NotOnTelegram",
        "Chat.Context.Username.NotOnTelegram",
        "WebBrowser.Telegram",
        "PUSH_CONTACT_JOINED",
        "Login.EmailPhoneBody",
        "Login.BannedPhoneBody",
        "Channel.Username.Help",
        "Channel.Username.LinkHint",
        "Channel.Username.CreatePublicLinkHelp",
        "Group.Username.CreatePublicLinkHelp",
        "Cache.Indexing",
        "AccessDenied.LocationAlwaysDenied",
        "Conversation.ClearPrivateHistory",
        "Conversation.ClearGroupHistory",
        "Conversation.ClearSelfHistory",
        "AuthSessions.LogOutApplicationsHelp",
        "Privacy.SecretChatsLinkPreviewsHelp",
        "Privacy.ContactsResetConfirmation",
        "Settings.Passport",
        "Passport.InfoTitle",
        "Passport.InfoText",
        "Passport.DeletePassport",
        "Passport.DeletePassportConfirmation",
        "Passport.PasswordHelp",
        "Passport.UpdateRequiredError",
        "Passport.PasswordReset",
        "Passport.PasswordDescription",
        "TwoStepAuth.PasswordRemovePassportConfirmation",
        "Passport.NotLoggedInMessage",
        "PrivacySettings.DataSettingsHelp",
        "Share.AuthTitle",
        "Share.AuthDescription",
        "ApplyLanguage.UnsufficientDataText",
        "AuthCode.Alert",
        "Login.CheckOtherSessionMessages",
        "Passcode.AppLockedAlert",
        "Permissions.ContactsText.v0",
        "Permissions.CellularDataText.v0",
        "Contacts.PermissionsText",
        "Contacts.PermissionsSuppressWarningText",
        "Notifications.PermissionsSuppressWarningText",
        "NotificationSettings.ContactJoinedInfo",
        "EmptyGroupInfo.Line3",
        "AccessDenied.Wallpapers",
    )
    for key in default_english_private_keys:
        value = strings.get(key, "")
        record(checks, "Private Chat" in value or "PrivateChat" in value or "privatechat.local" in value, f"{strings_path}：{key} 应包含 Private Chat、PrivateChat 或 privatechat.local")
        record(checks, "Telegram" not in value and "telegram.org" not in value and "t.me" not in value and "desktop.telegram.org" not in value and "web.telegram.org" not in value, f"{strings_path}：{key} 不应继续显示上游品牌或官方链接")
    record(checks, strings.get("Settings.FAQ_URL") == "https://privatechat.local/faq", f"{strings_path}：Settings.FAQ_URL 应指向 privatechat.local")
    record(checks, strings.get("Passport.InfoFAQ_URL") == "https://privatechat.local/faq#passport", f"{strings_path}：Passport.InfoFAQ_URL 应指向 privatechat.local")
    default_english_policy_update_keys = (
        "Login.TermsOfServiceSignupDecline",
        "PrivacyPolicy.DeclineMessage",
        "PrivacyPolicy.DeclineLastWarning",
        "Update.Title",
        "Update.AppVersion",
        "Update.UpdateApp",
        "Conversation.UnsupportedMediaPlaceholder",
        "Conversation.UpdateTelegram",
        "Settings.Terms_URL",
        "Settings.PrivacyPolicy_URL",
        "WebApp.DisclaimerText",
        "WebApp.Disclaimer_URL",
    )
    for key in default_english_policy_update_keys:
        value = strings.get(key, "")
        record(checks, "Private Chat" in value or "privatechat.local" in value or "UPDATE PRIVATE CHAT" in value, f"{strings_path}：{key} 应指向 Private Chat 或 privatechat.local")
        record(checks, "Telegram" not in value and "telegram.org" not in value, f"{strings_path}：{key} 不应继续显示 Telegram 或官方条款链接")

    widget_strings_path = "Telegram/WidgetKitWidget/en.lproj/Localizable.strings"
    widget_strings = parse_strings_file(read_text(widget_strings_path))
    record(checks, widget_strings.get("Widget.AuthRequired") == "Open Private Chat and log in.", f"{widget_strings_path}：Widget.AuthRequired 应包含 Private Chat")

    network_path = "submodules/TelegramCore/Sources/Network/Network.swift"
    network_text = read_text(network_path)
    has_private_dc = bool(re.search(r"1:\s*\[\s*\"127\.0\.0\.1\"\s*\]", network_text))
    has_private_port = "port: 10443" in network_text
    official_dc_pattern = re.compile(r"\b(149\.154|91\.108)\.\d+\.\d+\b")
    record(checks, has_private_dc, f"{network_path}：DC 1 seed 地址应指向 127.0.0.1")
    record(checks, has_private_port, f"{network_path}：DC 端口应为 10443")
    record(checks, official_dc_pattern.search(network_text) is None, f"{network_path}：不应保留官方 DC IP")

    readme_path = "README.md"
    readme_text = read_text(readme_path)
    record(checks, readme_text.startswith("# Private Chat iOS 端"), f"{readme_path}：应使用 Private Chat 中文优先说明")
    record(checks, "官方 iOS 客户端发布" in readme_text, f"{readme_path}：应明确说明不作为上游官方 iOS 客户端发布")
    record(checks, "official Telegram iOS distribution" in readme_text, f"{readme_path}：应包含英文摘要说明非官方 Telegram 发布")

    failed = [message for ok, message in checks if not ok]
    passed_count = len(checks) - len(failed)

    if failed:
        print(f"iOS 私有化配置验证失败：{passed_count}/{len(checks)} 项通过")
        for message in failed:
            print(f"- {message}")
        return 1

    print(f"iOS 私有化配置验证通过：{passed_count}/{len(checks)} 项通过")
    print("- Bundle ID、应用名和 URL Scheme 已指向 Private Chat 私有配置")
    print("- 本地模板已使用可生成工程的开发凭据格式，生产发布前必须替换为私有正式凭据")
    print("- iOS 网络 seed DC 1 已指向 127.0.0.1:10443，本地模拟器可用于后续连接验证")
    print("- README 已改为中文优先的 Private Chat iOS 私有快照说明")
    print("- 默认英文 PresentationStrings 与 Widget 扩展高可见入口已纳入品牌门禁")
    print("- App Store / AppCenter 发布配置已收敛为私有占位，默认英文条款、隐私和更新入口已纳入门禁")
    print("- 旧发布校验脚本和扩展构建 plist 已收敛到私有占位身份")
    return 0


if __name__ == "__main__":
    sys.exit(main())
