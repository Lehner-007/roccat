"""Read and write versioned, model-bound local lighting profiles."""
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from devices import MODELS

DIRECTORY = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "roccat/profiles"
NAME = re.compile(r"[\w -]{1,60}")


def validate(profile):
    if not isinstance(profile, dict) or type(profile.get("schema")) is not int or profile["schema"] != 1:
        raise ValueError("schema")
    model = profile.get("product")
    if not isinstance(model, str) or model not in MODELS or profile.get("vendor") != "1e7d":
        raise ValueError("device")
    if profile.get("backend") != "OpenRGB" or not NAME.fullmatch(str(profile.get("name", ""))):
        raise ValueError("metadata")
    if not isinstance(profile.get("name"), str) or not profile["name"].strip():
        raise ValueError("name")
    mode = profile.get("mode")
    colors = profile.get("colors")
    params = profile.get("parameters")
    if not isinstance(mode, str) or not mode.strip() or len(mode) > 120:
        raise ValueError("mode")
    if not isinstance(colors, list) or len(colors) > MODELS[model][1] or any(
        not isinstance(color, str) or not re.fullmatch(r"#[\da-fA-F]{6}", color, re.ASCII) for color in colors
    ):
        raise ValueError("colors")
    if not isinstance(params, dict) or any(
        key not in {"speed", "brightness"} or type(value) is not int or not 0 <= value <= 0xffffffff
        for key, value in params.items()
    ):
        raise ValueError("parameters")
    return profile


def load(path):
    with path.open("rb") as stream:
        data = stream.read(16385)
    if len(data) > 16384:
        raise ValueError("size")
    return validate(json.loads(data))


def save(path, profile, *, replace=False):
    validate(profile)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(profile, stream, ensure_ascii=False, indent=2)
            stream.flush()
            if replace:
                temporary.replace(path)
            else:
                os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
