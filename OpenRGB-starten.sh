#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
image="$HOME/.cache/roccat/OpenRGB-1.1.AppImage"
if systemctl --user is-active --quiet roccat-openrgb.service; then
    exit 0
fi
if [ ! -x "$image" ]; then
    printf '%s\n' "OpenRGB AppImage fehlt / OpenRGB AppImage not found: $image" >&2
    exit 1
fi
mkdir -p "$project_dir/.openrgb"
exec systemd-run --user --unit=roccat-openrgb --collect --setenv=QT_QPA_PLATFORM=offscreen \
    "$image" --appimage-extract-and-run --config "$project_dir/.openrgb" \
    --noautoconnect --server --server-host 127.0.0.1
