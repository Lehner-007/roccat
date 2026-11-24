"""User settings and coordination between the GUI and session service."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from gi.repository import Gio, GLib

import profiles
from devices import MODELS, sdk_operation

CONFIG = profiles.DIRECTORY.parent
RUNTIME = Path(os.environ["XDG_RUNTIME_DIR"]) / "roccat" if "XDG_RUNTIME_DIR" in os.environ else CONFIG
START_PROFILES = {"3124": "pc-tastatur", "2c88": "pc-maus"}


def idle_seconds():
    """Read elapsed activity time from Cinnamon without subscribing to input."""
    name = "org.cinnamon.Muffin.IdleMonitor"
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        result = bus.call_sync(
            name, "/org/cinnamon/Muffin/IdleMonitor/Core", name,
            "GetIdletime", None, GLib.VariantType.new("(t)"),
            Gio.DBusCallFlags.NO_AUTO_START, 800, None,
        )
        return result.unpack()[0] / 1000
    except GLib.Error:
        return None


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def locked():
    CONFIG.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (CONFIG / "lighting.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def preferences():
    data = read_json(CONFIG / "lighting.json", {"schema": 1, "devices": {}})
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("lighting schema")
    devices = data.get("devices")
    if not isinstance(devices, dict):
        raise ValueError("lighting devices")
    result = {}
    for model in MODELS:
        entry = devices.get(model, {"timed": False, "minutes": 10})
        if (not isinstance(entry, dict) or type(entry.get("timed")) is not bool
                or type(entry.get("minutes")) is not int or not 1 <= entry["minutes"] <= 240):
            raise ValueError("lighting duration")
        result[model] = entry
    return result


def save_preferences(devices):
    with locked():
        preferences()
        path = CONFIG / "lighting.json"
        backup = CONFIG / "lighting.json.bak"
        if path.exists() and not backup.exists():
            write_json(backup, read_json(path, None))
        write_json(path, {"schema": 1, "devices": devices})


def active_profile(model):
    try:
        profile = profiles.load(CONFIG / "active" / f"{model}.json")
    except FileNotFoundError:
        try:
            profile = profiles.load(profiles.DIRECTORY / f"{START_PROFILES[model]}.json")
        except FileNotFoundError:
            return None
    if profile["product"] != model:
        raise ValueError("active profile model")
    return profile


def apply_from_window(device, profile):
    with locked():
        result = sdk_operation(device, profile)
        profiles.save(CONFIG / "active" / f"{device.product}.json", profile, replace=True)
        return result


def status():
    return read_json(RUNTIME / "lighting-status.json", {})
