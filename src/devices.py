"""Discover physical devices and bind SDK controllers to their HID interfaces."""
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "3124": ("ROCCAT Magma", 5, "KEYBOARD"),
    "2c88": ("ROCCAT Kone Pro", 2, "MOUSE"),
}


@dataclass(frozen=True)
class Device:
    product: str
    port: str
    release: str
    address: str
    hid: tuple[str, ...]


def read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def inventory():
    hid_interfaces = tuple(Path("/sys/class/hidraw").glob("hidraw*"))
    result = []
    for usb in sorted(Path("/sys/bus/usb/devices").glob("*")):
        product = read(usb / "idProduct").lower()
        if product not in MODELS or read(usb / "idVendor").lower() != "1e7d":
            continue
        physical = usb.resolve()
        hid = tuple(str(Path("/dev") / interface.name) for interface in hid_interfaces
                    if physical in (interface / "device").resolve().parents)
        result.append(Device(product, usb.name, read(usb / "bcdDevice"),
                             read(usb / "devnum"), hid))
    return result


def library():
    # Use the verified, unmodified reference checkout supplied with the project.
    source = ROOT / "referenzen/original/openrgb-python"
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from openrgb import OpenRGBClient
    from openrgb.utils import DeviceType, ModeColors, ModeFlags, RGBColor
    return OpenRGBClient, DeviceType, ModeColors, ModeFlags, RGBColor


class BackendError(Exception):
    pass


def options(controller, protocol, colors, flags, limit):
    result = {}
    for mode in controller.modes:
        if mode.color_mode == colors.PER_LED:
            count = len(controller.leds)
        elif mode.color_mode == colors.MODE_SPECIFIC:
            count = len(mode.colors or ())
        else:
            count = 0
        if not 0 <= count <= limit:
            continue
        values = mode.colors if mode.color_mode == colors.MODE_SPECIFIC else controller.colors
        entries = [f"#{c.red:02x}{c.green:02x}{c.blue:02x}" for c in (values or ())[:count]]
        entries.extend(["#ffffff"] * (count - len(entries)))
        limits = {}
        for key, flag in (("speed", flags.HAS_SPEED), ("brightness", flags.HAS_BRIGHTNESS)):
            if not mode.flags & flag or (key == "brightness" and protocol < 3):
                continue
            lo, hi = sorted((getattr(mode, key + "_min"), getattr(mode, key + "_max")))
            limits[key] = (lo, hi, getattr(mode, key))
        result[mode.name] = (entries, limits)
    return result


def sdk_operation(device, settings=None):
    if device is not None and device not in inventory():
        raise BackendError("removed")
    try:
        client_type, device_type, colors, flags, rgb = library()
    except ImportError as error:
        raise BackendError("dependency") from error
    try:
        client = client_type(address="127.0.0.1", port=6742, name="roccat")
    except Exception as error:
        raise BackendError("offline") from error
    try:
        if device is None:
            return None
        name, limit, kind = MODELS[device.product]
        matches = [item for item in client.devices
                   if " ".join(item.name.casefold().split()) == name.casefold()
                   and item.type == getattr(device_type, kind)
                   and item.metadata.location.removeprefix("HID: ") in device.hid]
        if len(matches) != 1:
            raise BackendError("unmatched")
        controller = matches[0]
        capabilities = options(controller, client.protocol_version, colors, flags, limit)
        if settings is not None:
            mode_name = settings["mode"]
            if mode_name not in capabilities:
                raise BackendError("incompatible")
            entries, limits = capabilities[mode_name]
            requested = settings["colors"]
            parameters = settings["parameters"]
            if len(requested) != len(entries) or set(parameters) != set(limits):
                raise BackendError("incompatible")
            mode = next(mode for mode in controller.modes if mode.name == mode_name)
            for key, value in parameters.items():
                lo, hi, _ = limits[key]
                if not lo <= value <= hi:
                    raise BackendError("incompatible")
                setattr(mode, key, value)
            palette = [rgb(*(int(color[i:i + 2], 16) for i in (1, 3, 5))) for color in requested]
            if mode.color_mode == colors.MODE_SPECIFIC:
                mode.colors = palette
            if device not in inventory():
                raise BackendError("removed")
            controller.set_mode(mode, save=False)
            if controller.active_mode != mode.id:
                raise BackendError("failed")
            if palette and mode.color_mode == colors.PER_LED:
                from time import sleep
                sleep(0.15)
                if device not in inventory():
                    raise BackendError("removed")
                controller.set_colors(palette, fast=True)
        return capabilities, controller.modes[controller.active_mode].name if controller.modes else ""
    finally:
        client.disconnect()
