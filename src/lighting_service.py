#!/usr/bin/python3
# roccat lighting service | Version from VERSION | Josef Lehner | 24.11.2026
# Applies the configured startup profiles and monitors Cinnamon session inactivity.
# Run as the logged-in user through roccat-profil-start.service.
# Reads user configuration and writes transient status under XDG_RUNTIME_DIR.
# Logs changes and errors to the user journal. Records no input events or contents.
# Returns 0 on normal stop and 1 on an unhandled service error.

from dataclasses import dataclass
import logging
import os
import signal
import subprocess
from threading import Event
import time

from devices import BackendError, Device, MODELS, inventory, sdk_operation
from lighting import RUNTIME, active_profile, idle_seconds, locked, preferences, write_json

LOG = logging.getLogger("roccat")
STATUS = RUNTIME / "lighting-status.json"


@dataclass
class State:
    device: Device | None = None
    applied: tuple | None = None
    dark_profile: dict | None = None
    retry_at: float = 0
    retry_delay: int = 2
    report: tuple | None = None


def report(state, model, profile, status, detail=""):
    current = (status, detail, profile["name"] if profile else "–")
    if current != state.report:
        level = logging.WARNING if detail or status in {"backend", "configuration"} else logging.INFO
        LOG.log(level, "device=%s profile=%s result=%s detail=%s",
                MODELS[model][0], current[2], status, detail or "–")
        state.report = current
    return status


def reconcile(model, state, matches, options, idle, now, refresh):
    if len(matches) != 1 or not matches[0].hid:
        state.device = state.applied = state.dark_profile = None
        state.retry_at, state.retry_delay = 0, 2
        return report(state, model, None, "disconnected" if not matches else "backend",
                      "ambiguous or missing HID" if matches else "")
    device = matches[0]
    if state.device != device or refresh:
        if state.device != device:
            state.dark_profile = None
        state.device, state.applied = device, None
        state.retry_at, state.retry_delay = 0, 2

    with locked():
        profile = active_profile(model)
        if profile is None:
            return report(state, model, None, "no_profile")
        direct = profile["mode"] == "Direct" and len(profile["colors"]) == MODELS[model][1]
        black = direct and not any(color.lower() != "#000000" for color in profile["colors"])
        black = black or profile["parameters"].get("brightness") == 0
        timed = options["timed"] and idle is not None
        dark = timed and direct and not black and idle >= options["minutes"] * 60
        target = (profile, dark)
        if state.applied != target and now >= state.retry_at:
            try:
                settings = dict(profile, colors=["#000000"] * len(profile["colors"])) if dark else profile
                sdk_operation(device, settings, volatile=direct, skip_if_current=True)
            except Exception as error:
                state.retry_at = now + state.retry_delay
                state.retry_delay = min(60, state.retry_delay * 2)
                return report(state, model, profile, "backend", str(error))
            state.applied = target
            state.dark_profile = profile if dark else None
            state.retry_at, state.retry_delay = 0, 2
        if state.applied != target:
            return "backend"

    if black:
        return report(state, model, profile, "manual_off")
    if options["timed"] and idle is None:
        return report(state, model, profile, "idle_unavailable")
    if timed and not direct:
        return report(state, model, profile, "timer_unsupported")
    return report(state, model, profile, "idle_off" if dark else "on")


def restore(states):
    for model, state in states.items():
        if state.dark_profile is None:
            continue
        try:
            with locked():
                if active_profile(model) == state.dark_profile:
                    sdk_operation(state.device, state.dark_profile, volatile=True)
                    report(state, model, state.dark_profile, "on")
        except Exception as error:
            report(state, model, state.dark_profile, "backend", str(error))


def main():
    if os.geteuid() == 0:
        return 1
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    states = {model: State() for model in MODELS}
    last = None
    suspension = None
    next_probe = 0
    server = None
    try:
        while not stop.is_set():
            now = time.monotonic()
            elapsed_sleep = time.clock_gettime(time.CLOCK_BOOTTIME) - now
            refresh = suspension is not None and elapsed_sleep - suspension > 0.75
            suspension = elapsed_sleep
            if now >= next_probe:
                next_probe = now + 5
                try:
                    unit = subprocess.run(
                        ["systemctl", "show", "roccat-openrgb.service", "--property=InvocationID",
                         "--property=ActiveState", "--value"],
                        capture_output=True, text=True, timeout=1, check=False,
                    ).stdout
                except (OSError, subprocess.TimeoutExpired):
                    unit = ""
                refresh = refresh or (server is not None and server != unit)
                server = unit
            devices = inventory()
            idle = idle_seconds()
            try:
                options = preferences()
            except (OSError, ValueError):
                options = None
            current = {}
            for model, state in states.items():
                try:
                    if options is None:
                        raise ValueError("lighting settings are unreadable")
                    current[model] = reconcile(
                        model, state, [device for device in devices if device.product == model],
                        options[model], idle, now, refresh,
                    )
                except (OSError, ValueError) as error:
                    current[model] = report(state, model, None, "configuration", str(error))
            if current != last:
                write_json(STATUS, current)
                last = current
            stop.wait(1)
    finally:
        restore(states)
        STATUS.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
