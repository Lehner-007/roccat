#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
image="$HOME/.cache/roccat/OpenRGB-1.1.AppImage"
if [ ! -x "$image" ]; then
    mkdir -p "$(dirname "$image")"
    download=$(mktemp "${image}.XXXXXX")
    trap 'rm -f -- "$download"' EXIT
    curl -fsSL --retry 2 -o "$download" \
        https://codeberg.org/OpenRGB/OpenRGB/releases/download/release_1.1/OpenRGB_1.1_x86_64_8e16de2.AppImage
    printf '%s  %s\n' d556c2273b0ef863dbee7ffdb438304b382add5d685c93c60758b42de3b0268d "$download" | sha256sum -c -
    chmod 755 "$download"
    mv -f -- "$download" "$image"
    trap - EXIT
fi
"$project_dir/Start.sh" --nur-starter
mkdir -p "$project_dir/.openrgb"
loginctl enable-linger "$(id -un)"

# A running transient unit must be released before its persistent replacement is loaded.
if [ "$(systemctl --user show roccat-openrgb.service -p UnitFileState --value)" = transient ]; then
    systemctl --user stop roccat-openrgb.service
fi
/usr/bin/python3 - "$project_dir" "$image" <<'PYCODE'
import os
from pathlib import Path
import sys
import tempfile

project, image = map(Path, sys.argv[1:])
unit_dir = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "systemd/user"
unit_dir.mkdir(parents=True, exist_ok=True)

def unit_argument(path):
    value = str(path).replace("\\", "\\\\").replace('"', '\\"')
    return '"' + value.replace("%", "%%").replace("$", "$$") + '"'

config = unit_argument(project / ".openrgb")
content = f"""[Unit]
Description=OpenRGB SDK for roccat

[Service]
Environment=QT_QPA_PLATFORM=offscreen
ExecStart={unit_argument(image)} --appimage-extract-and-run --config {config} --noautoconnect --server --server-host 127.0.0.1
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=unit_dir, delete=False) as output:
    temporary = Path(output.name)
    output.write(content)
try:
    temporary.chmod(0o644)
    temporary.replace(unit_dir / "roccat-openrgb.service")
finally:
    temporary.unlink(missing_ok=True)
PYCODE
systemctl --user daemon-reload
systemctl --user enable roccat-openrgb.service
systemctl --user restart roccat-openrgb.service
