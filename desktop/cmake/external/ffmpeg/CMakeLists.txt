# This file is part of Desktop App Toolkit,
# a set of libraries for developing nice desktop applications.
#
# For license and copyright information please follow this link:
# https://github.com/desktop-app/legal/blob/master/LEGAL

add_library(external_ffmpeg INTERFACE IMPORTED GLOBAL)
add_library(desktop-app::external_ffmpeg ALIAS external_ffmpeg)

if (DESKTOP_APP_USE_PACKAGED OR LINUX)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(DESKTOP_APP_FFMPEG REQUIRED IMPORTED_TARGET
        libavcodec
        libavfilter
        libavformat
        libavutil
        libswresample
        libswscale
    )
    target_link_libraries(external_ffmpeg INTERFACE PkgConfig::DESKTOP_APP_FFMPEG)
    return()
endif()

set(ffmpeg_lib_loc ${libs_loc}/ffmpeg)
set(ffmpeg_include_loc ${CMAKE_CURRENT_BINARY_DIR}/ffmpeg_include)

file(MAKE_DIRECTORY ${ffmpeg_include_loc})

foreach(include_entry
        compat
        libavcodec
        libavdevice
        libavfilter
        libavformat
        libavutil
        libpostproc
        libswresample
        libswscale
        config.h
        config_components.h)
    if (EXISTS ${ffmpeg_lib_loc}/${include_entry}
            AND NOT EXISTS ${ffmpeg_include_loc}/${include_entry})
        file(CREATE_LINK
            ${ffmpeg_lib_loc}/${include_entry}
            ${ffmpeg_include_loc}/${include_entry}
            SYMBOLIC)
    endif()
endforeach()

target_include_directories(external_ffmpeg SYSTEM
INTERFACE
    ${ffmpeg_include_loc}
)

target_link_libraries(external_ffmpeg
INTERFACE
    ${ffmpeg_lib_loc}/libavfilter/libavfilter.a
    ${ffmpeg_lib_loc}/libavformat/libavformat.a
    ${ffmpeg_lib_loc}/libavcodec/libavcodec.a
    ${ffmpeg_lib_loc}/libswresample/libswresample.a
    ${ffmpeg_lib_loc}/libswscale/libswscale.a
    ${ffmpeg_lib_loc}/libavutil/libavutil.a
    $<LINK_ONLY:desktop-app::external_openh264>
    $<TARGET_FILE:desktop-app::external_openh264>
    $<LINK_ONLY:desktop-app::external_opus>
    $<TARGET_FILE:desktop-app::external_opus>
    $<LINK_ONLY:desktop-app::external_vpx>
    $<TARGET_FILE:desktop-app::external_vpx>
)

if (APPLE)
    target_link_libraries(external_ffmpeg INTERFACE bz2)
endif()
