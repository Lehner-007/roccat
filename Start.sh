#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
/usr/bin/python3 - "$project_dir" <<'PY'
from pathlib import Path
import sys
import tempfile

root = Path(sys.argv[1])
logo = root / "bilder/Roccat.svg"
icon = str(logo if logo.is_file() else root / ".basisbilder/start.png").replace("\\", "\\\\")
content = r'''[Desktop Entry]
Type=Application
Name=roccat
Comment=Configure ROCCAT Magma and Kone Pro
Comment[de]=ROCCAT Magma und Kone Pro verwalten
Exec=/usr/bin/python3 -B @APP_PATH@
Terminal=false
Categories=Settings;HardwareSettings;
'''
app_path = str(root / "src/app.py")
for char in ("\\", '"', "`", "$"):
    app_path = app_path.replace(char, "\\" + char)
app_path = app_path.replace("\\", "\\\\").replace("%", "%%")
content = content.replace("@APP_PATH@", f'"{app_path}"')
with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as output:
    temporary = Path(output.name)
    output.write(content + f"Icon={icon}\n")
try:
    temporary.chmod(0o755)
    temporary.replace(root / "roccat.desktop")
finally:
    temporary.unlink(missing_ok=True)
PY
if [ "${1-}" != "--nur-starter" ]; then
    exec /usr/bin/python3 -B "$project_dir/src/app.py"
fi
