#!/usr/bin/env python3
import plistlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def record(checks, ok, message):
    checks.append((ok, message))


def contains_all(text, values):
    return all(value in text for value in values)


def read_lang_strings(relative_path):
    text = read_text(relative_path)
    pattern = re.compile(
        r'"(?P<key>[^"]+)"\s*=\s*"(?P<value>(?:\\.|[^"\\])*)";',
        re.MULTILINE,
    )
    return {match.group("key"): match.group("value") for match in pattern.finditer(text)}


def read_plist(path):
    with path.open("rb") as handle:
        return plistlib.load(handle)


def main():
    checks = []

    dc_path = "Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp"
    dc_text = read_text(dc_path)
    official_dc_pattern = re.compile(r"\b(149\.154|91\.108)\.\d+\.\d+\b")
    record(checks, '{ 1, "127.0.0.1", 10443 }' in dc_text, f"{dc_path}：IPv4 DC 1 应指向 127.0.0.1:10443")
    record(checks, '{ 1, "::1", 10443 }' in dc_text, f"{dc_path}：IPv6 DC 1 应指向 ::1:10443")
    record(checks, dc_text.count("-----BEGIN RSA PUBLIC KEY-----") >= 2, f"{dc_path}：生产和测试 RSA 公钥应存在")
    record(checks, official_dc_pattern.search(dc_text) is None, f"{dc_path}：不应保留官方 DC IP")

    instance_path = "Telegram/SourceFiles/mtproto/mtp_instance.h"
    instance_text = read_text(instance_path)
    default_dc_match = re.search(r"kDefaultMainDc\s*=\s*(\d+)", instance_text)
    default_dc = int(default_dc_match.group(1)) if default_dc_match else None
    for group in ("kBuiltInDcs", "kBuiltInDcsIPv6", "kBuiltInDcsTest", "kBuiltInDcsIPv6Test"):
        group_match = re.search(rf"{group}\[\]\s*=\s*\{{(.*?)\}};", dc_text, re.DOTALL)
        dc_ids = {int(value) for value in re.findall(r"\{\s*(\d+)\s*,", group_match.group(1))} if group_match else set()
        record(checks, default_dc in dc_ids, f"{instance_path}：默认主 DC {default_dc} 必须存在于 {group}，否则首次登录请求无法发送")

    plist_path = "Telegram/Telegram.plist"
    plist = read_plist(ROOT / plist_path)
    record(checks, plist.get("CFBundleGetInfoString") == "Private Chat Desktop messaging app", f"{plist_path}：CFBundleGetInfoString 应为 Private Chat Desktop")
    url_schemes = plist.get("CFBundleURLTypes", [{}])[0].get("CFBundleURLSchemes", [])
    record(checks, "privatechat" in url_schemes, f"{plist_path}：URL scheme 应注册 privatechat")
    record(checks, "tg" not in url_schemes, f"{plist_path}：不应继续注册 tg URL scheme")

    cmake_path = "Telegram/CMakeLists.txt"
    cmake_text = read_text(cmake_path)
    record(checks, 'set(bundle_identifier "com.privatechat.desktop")' in cmake_text, f"{cmake_path}：Release Bundle ID 应为 com.privatechat.desktop")
    record(checks, 'set(bundle_identifier "com.privatechat.desktop$<$<CONFIG:Debug>:.debug>")' in cmake_text, f"{cmake_path}：Xcode Debug Bundle ID 应为 com.privatechat.desktop.debug")
    record(checks, 'set(output_name "Private Chat")' in cmake_text, f"{cmake_path}：macOS 输出名称应为 Private Chat")

    built_plist_path = ROOT / "out/Debug/Private Chat.app/Contents/Info.plist"
    if built_plist_path.exists():
        built_plist = read_plist(built_plist_path)
        record(checks, built_plist.get("CFBundleIdentifier") == "com.privatechat.desktop.debug", f"{built_plist_path.relative_to(ROOT)}：Debug Bundle ID 应为 com.privatechat.desktop.debug")
        record(checks, built_plist.get("CFBundleName") == "Private Chat", f"{built_plist_path.relative_to(ROOT)}：CFBundleName 应为 Private Chat")
    else:
        record(checks, True, "out/Debug/Private Chat.app 尚未生成，跳过生成产物 Bundle 元数据检查")

    setup_path = "Telegram/build/setup.iss"
    setup_text = read_text(setup_path)
    record(checks, contains_all(setup_text, [
        '#define MyAppShortName "Private Chat"',
        '#define MyAppName "Private Chat Desktop"',
        '#define MyAppPublisher "Private Chat"',
        '#define MyAppURL "https://private-chat.local"',
    ]), f"{setup_path}：Windows 安装器显示信息应指向 Private Chat")

    for rc_path, expected in [
        ("Telegram/Resources/winrc/Telegram.rc", "Private Chat Desktop"),
        ("Telegram/Resources/winrc/Updater.rc", "Private Chat Desktop Updater"),
    ]:
        rc_text = read_text(rc_path)
        record(checks, 'VALUE "CompanyName", "Private Chat"' in rc_text, f"{rc_path}：CompanyName 应为 Private Chat")
        record(checks, f'VALUE "FileDescription", "{expected}"' in rc_text, f"{rc_path}：FileDescription 应为 {expected}")
        record(checks, 'VALUE "ProductName", "Private Chat Desktop"' in rc_text, f"{rc_path}：ProductName 应为 Private Chat Desktop")

    appx_path = "Telegram/Resources/uwp/AppX/AppxManifest.xml"
    appx_text = read_text(appx_path)
    appx_root = ET.fromstring(appx_text)
    ns = {
        "f": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
        "uap3": "http://schemas.microsoft.com/appx/manifest/uap/windows10/3",
        "desktop": "http://schemas.microsoft.com/appx/manifest/desktop/windows10",
    }
    identity = appx_root.find("f:Identity", ns)
    properties = appx_root.find("f:Properties", ns)
    visual = appx_root.find(".//uap:VisualElements", ns)
    startup = appx_root.find(".//desktop:StartupTask", ns)
    record(checks, identity is not None and identity.get("Name") == "PrivateChat.Desktop", f"{appx_path}：Identity Name 应为 PrivateChat.Desktop")
    record(checks, identity is not None and identity.get("Publisher") == "CN=Private Chat", f"{appx_path}：Publisher 应为 CN=Private Chat")
    record(checks, properties is not None and properties.findtext("f:DisplayName", namespaces=ns) == "Private Chat Desktop", f"{appx_path}：DisplayName 应为 Private Chat Desktop")
    record(checks, properties is not None and properties.findtext("f:PublisherDisplayName", namespaces=ns) == "Private Chat", f"{appx_path}：PublisherDisplayName 应为 Private Chat")
    record(checks, visual is not None and visual.get("DisplayName") == "Private Chat Desktop", f"{appx_path}：VisualElements DisplayName 应为 Private Chat Desktop")
    record(checks, startup is not None and startup.get("DisplayName") == "Private Chat Desktop", f"{appx_path}：StartupTask DisplayName 应为 Private Chat Desktop")
    record(checks, "Telegram Desktop official messenger" not in appx_text, f"{appx_path}：不应保留官方 UWP 描述")
    protocol_names = [node.get("Name") for node in appx_root.findall(".//uap3:Protocol", ns)]
    record(checks, "privatechat" in protocol_names, f"{appx_path}：UWP 协议应注册 privatechat")
    record(checks, "tg" not in protocol_names, f"{appx_path}：UWP 协议不应继续注册 tg")

    desktop_path = "lib/xdg/org.telegram.desktop.desktop"
    desktop_text = read_text(desktop_path)
    record(checks, "Name=Private Chat" in desktop_text, f"{desktop_path}：Name 应为 Private Chat")
    record(checks, "Icon=com.privatechat.desktop" in desktop_text, f"{desktop_path}：Icon 应为 com.privatechat.desktop")
    record(checks, "x-scheme-handler/privatechat" in desktop_text, f"{desktop_path}：Linux 协议应注册 privatechat")
    record(checks, "x-scheme-handler/tg" not in desktop_text, f"{desktop_path}：Linux 协议不应继续注册 tg")

    metainfo_path = "lib/xdg/org.telegram.desktop.metainfo.xml"
    metainfo_text = read_text(metainfo_path)
    metainfo_root = ET.fromstring(metainfo_text)
    record(checks, metainfo_root.findtext("id") == "com.privatechat.desktop", f"{metainfo_path}：应用 ID 应为 com.privatechat.desktop")
    record(checks, metainfo_root.findtext("name") == "Private Chat", f"{metainfo_path}：名称应为 Private Chat")
    record(checks, "Private Chat is a private instant messaging client" in metainfo_text, f"{metainfo_path}：简介应说明私有客户端")

    root_cmake_path = "CMakeLists.txt"
    root_cmake_text = read_text(root_cmake_path)
    record(checks, 'DESCRIPTION "Private Chat Desktop messenger"' in root_cmake_text, f"{root_cmake_path}：项目描述应为 Private Chat Desktop")
    record(checks, 'HOMEPAGE_URL "https://private-chat.local"' in root_cmake_text, f"{root_cmake_path}：主页应为私有占位地址")

    variables_path = "cmake/variables.cmake"
    variables_text = read_text(variables_path)
    record(checks, "set(disable_autoupdate 1)" in variables_text, f"{variables_path}：默认应关闭自动更新")
    record(checks, 'option(DESKTOP_APP_DISABLE_AUTOUPDATE "Disable autoupdate." ${disable_autoupdate})' in variables_text, f"{variables_path}：自动更新开关应保留可显式覆盖入口")
    record(checks, 'option(DESKTOP_APP_DISABLE_CRASH_REPORTS "Disable crash report generation." ON)' in variables_text, f"{variables_path}：默认应关闭崩溃上报")

    application_path = "Telegram/SourceFiles/core/application.cpp"
    application_text = read_text(application_path)
    record(checks, '.protocol = u"privatechat"_q' in application_text, f"{application_path}：运行时应注册 privatechat URL scheme")
    record(checks, '.protocol = u"tg"_q' not in application_text, f"{application_path}：运行时不应继续注册 tg URL scheme")
    record(checks, 'protocolName = u"Private Chat Link"_q' in application_text, f"{application_path}：运行时协议名称应为 Private Chat Link")
    record(checks, 'return u"https://private-chat.local/changelog/"_q;' in application_text, f"{application_path}：版本记录链接应指向私有占位地址")
    record(checks, "telegramdesktop.github.io" not in application_text, f"{application_path}：不应继续使用官方版本记录地址")

    local_url_handlers_path = "Telegram/SourceFiles/core/local_url_handlers.cpp"
    local_url_handlers_text = read_text(local_url_handlers_path)
    record(checks, 'url.startsWith(u"privatechat://"_q, Qt::CaseInsensitive)' in local_url_handlers_text, f"{local_url_handlers_path}：应支持 privatechat:// 本地深链")
    record(checks, 'return u"tg://"_q + url.mid(u"privatechat://"_q.size())' in local_url_handlers_text, f"{local_url_handlers_path}：privatechat:// 应映射到现有本地处理流程")

    main_menu_path = "Telegram/SourceFiles/window/window_main_menu.cpp"
    main_menu_text = read_text(main_menu_path)
    record(checks, 'u"Private Chat Desktop"_q' in main_menu_text, f"{main_menu_path}：主菜单底部应显示 Private Chat Desktop")
    record(checks, 'u"https://private-chat.local"_q' in main_menu_text, f"{main_menu_path}：主菜单底部链接应指向私有占位地址")
    record(checks, "desktop.telegram.org" not in main_menu_text, f"{main_menu_path}：不应继续使用官方桌面端主页")

    updater_win_path = "Telegram/SourceFiles/_other/updater_win.cpp"
    updater_win_text = read_text(updater_win_path)
    record(checks, 'L"Private Chat Desktop"' in updater_win_text, f"{updater_win_path}：Windows 更新器注册信息应显示 Private Chat Desktop")
    record(checks, 'L"Private Chat"' in updater_win_text, f"{updater_win_path}：Windows 更新器发布者应显示 Private Chat")
    record(checks, 'L"https://private-chat.local"' in updater_win_text, f"{updater_win_path}：Windows 更新器帮助链接应指向私有占位地址")
    record(checks, "desktop.telegram.org" not in updater_win_text, f"{updater_win_path}：Windows 更新器不应继续使用官方主页")

    readme_path = "README.md"
    readme_text = read_text(readme_path)
    record(checks, readme_text.startswith("# Private Chat Desktop 桌面端"), f"{readme_path}：应使用 Private Chat 中文优先说明")
    record(checks, "official Telegram Desktop distribution" in readme_text, f"{readme_path}：应包含英文摘要说明非官方 Telegram 发布")

    lang_path = "Telegram/Resources/langs/lang.strings"
    lang_values = read_lang_strings(lang_path)
    private_chat_lang_keys = [
        "lng_error_start_minimized_passcoded",
        "lng_proxy_unsupported",
        "lng_signin_sure_reset",
        "lng_settings_use_winhello_about",
        "lng_settings_use_touchid_about",
        "lng_settings_use_applewatch_about",
        "lng_settings_use_systempwd_about",
        "lng_settings_username_about",
        "lng_settings_peer_to_peer_about",
        "lng_settings_logged_in_title",
        "lng_settings_logged_in_description",
        "lng_settings_disconnect_all_sure",
        "lng_settings_suggestion_phone_number_about",
        "lng_settings_suggestion_phone_number_change",
        "lng_settings_cloud_password_start_about",
        "lng_settings_cloud_login_email_box_about",
        "lng_settings_cloud_login_email_about",
        "lng_local_storage_device_telegram",
        "lng_local_storage_device_usage",
        "lng_local_storage_about",
        "lng_passcode_about",
        "lng_passcode_about2",
        "lng_passcode_about3",
        "lng_passcode_winhello_unlock",
        "lng_cloud_password_create",
        "lng_cloud_password_about_recover",
        "lng_proxy_about",
        "lng_proxy_sponsor_about",
        "lng_proxy_sponsor_warning",
        "lng_settings_export_data",
        "lng_settings_ask_sure",
        "lng_settings_faq",
        "lng_settings_features",
        "lng_sessions_other_desc",
        "lng_sessions_about_apps",
        "lng_blocked_list_confirm_text",
        "lng_edit_privacy_phone_number_warning",
        "lng_edit_privacy_phone_number_contacts",
        "lng_change_phone_error",
        "lng_profile_unofficial_warning",
        "lng_clear_payment_info_confirm",
        "lng_settings_color_link_name",
        "lng_theme_no_desktop",
        "lng_download_path_default_radio",
        "lng_settings_passkeys_unsigned_error",
        "lng_profile_suggest_sure",
        "lng_profile_accept_photo_sure",
        "lng_profile_accept_video_sure",
        "lng_manage_peer_antispam_about",
        "lng_message_unsupported",
        "lng_action_user_registered",
        "lng_group_invite_about_permanent_group",
        "lng_group_invite_about_permanent_channel",
        "lng_group_invite_qr_about",
        "lng_bot_share_location_unavailable",
        "lng_chat_link_qr_about",
        "lng_verification_codes_about",
        "lng_about_text1_api",
        "lng_about_text3_faq",
        "lng_new_version_wrap",
        "lng_confirm_phone_about",
        "lng_payments_warning_body",
        "lng_call_status_group_invite",
        "lng_call_box_about",
        "lng_group_call_mac_access",
        "lng_group_call_mac_input",
        "lng_group_call_mac_accessibility",
        "lng_group_call_mac_screencast_access",
        "lng_group_call_mac_recording",
        "lng_group_call_no_stream_admin",
        "lng_group_call_no_stream",
        "lng_confcall_join_text",
        "lng_confcall_join_text_inviter",
        "lng_confcall_create_link_description",
        "lng_confcall_link_about",
        "lng_no_mic_permission",
        "lng_terms_signup_sorry",
        "lng_terms_update_sorry",
        "lng_terms_delete_warning",
        "lng_passport_title",
        "lng_passport_use_existing_phone",
        "lng_passport_use_existing_email",
        "lng_passport_restart_sure",
        "lng_passport_app_out_of_date",
        "lng_export_option_contacts_about",
        "lng_export_option_stories_about",
        "lng_export_progress",
        "lng_export_about_telegram",
        "lng_export_about_contacts",
        "lng_export_about_frequent",
        "lng_export_about_web_sessions",
        "lng_language_not_ready_about",
        "lng_outdated_soon",
        "lng_outdated_now",
        "lng_screen_reader_bar_text",
        "lng_screen_reader_confirm_text",
        "lng_filters_link_qr_about",
        "lng_mini_apps_disclaimer_text",
        "lng_stories_unsupported",
        "lng_frozen_text1",
        "lng_age_verify_mobile",
        "lng_age_verify_here",
        "lng_mac_menu_show",
        "lng_menu_not_contact",
        "lng_contact_not_joined",
        "lng_unconfirmed_auth_denied_warning",
        "lng_allow_bot_pass",
        "lng_bot_no_scan_qr",
        "lng_bot_no_share_story",
        "lng_cloud_password_passport_losing",
        "lng_action_suggested_photo_me",
        "lng_action_suggested_photo",
        "lng_action_suggested_video_me",
        "lng_action_suggested_video",
        "lng_theme_editor_need_unlock",
        "lng_posts_subtitle_empty",
    ]
    for key in private_chat_lang_keys:
        value = lang_values.get(key, "")
        record(checks, "Private Chat" in value, f"{lang_path}：{key} 应显示 Private Chat")
        record(checks, "Telegram" not in value, f"{lang_path}：{key} 不应继续显示 Telegram")

    private_url_lang_keys = {
        "lng_settings_suggestion_phone_number_about_link": "https://private-chat.local/faq/change-phone-number",
        "lng_settings_faq_link": "https://private-chat.local/faq#general-questions",
        "lng_profile_bot_privacy_url": "https://private-chat.local/privacy-tpa",
        "lng_mini_apps_tos_url": "https://private-chat.local/tos/mini-apps",
        "lng_telegram_features_url": "https://private-chat.local/features",
        "lng_popular_apps_info_url": "https://private-chat.local/docs/mini-apps",
    }
    for key, expected_url in private_url_lang_keys.items():
        value = lang_values.get(key, "")
        record(checks, value == expected_url, f"{lang_path}：{key} 应指向 {expected_url}")
        record(checks, "telegram.org" not in value and "t.me" not in value, f"{lang_path}：{key} 不应继续指向上游官方域名")

    private_link_example_lang_keys = [
        "lng_group_about3",
        "lng_factcheck_links",
    ]
    for key in private_link_example_lang_keys:
        value = lang_values.get(key, "")
        record(checks, "privatechat.local" in value, f"{lang_path}：{key} 应使用 privatechat.local 链接示例")
        record(checks, "t.me" not in value, f"{lang_path}：{key} 不应继续使用 t.me 链接示例")

    failed = [message for ok, message in checks if not ok]
    passed_count = len(checks) - len(failed)

    if failed:
        print(f"Desktop 私有化配置验证失败：{passed_count}/{len(checks)} 项通过")
        for message in failed:
            print(f"- {message}")
        return 1

    print(f"Desktop 私有化配置验证通过：{passed_count}/{len(checks)} 项通过")
    print("- 内置 DC 已指向 127.0.0.1:10443 / ::1:10443")
    print("- macOS、Windows、UWP、Linux 高可见入口已指向 Private Chat")
    print("- 默认构建已关闭自动更新和崩溃上报，可在接入自建服务后显式打开")
    print("- 当前验证是静态配置验证；登录、多端互通、发布签名和正式服务器入口仍需单独验证")
    return 0


if __name__ == "__main__":
    sys.exit(main())
