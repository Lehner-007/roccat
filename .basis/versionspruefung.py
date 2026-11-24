"""Schedule and read public GitHub releases without blocking GTK."""
from calendar import monthrange
from datetime import datetime, timedelta
from http.client import HTTPException
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

INTERVALS = ("daily", "weekly", "monthly")


def due(last, interval, now):
    if last is None or now < last:
        return True
    if interval == "monthly":
        year, month = (last.year + 1, 1) if last.month == 12 else (last.year, last.month + 1)
        deadline = last.replace(year=year, month=month,
                                day=min(last.day, monthrange(year, month)[1]))
    else:
        deadline = last + timedelta(days=1 if interval == "daily" else 7)
    return now >= deadline


def version_key(value):
    if not re.fullmatch(r"[vV]?[0-9]{1,9}(?:\.[0-9]{1,9}){0,7}", value):
        raise ValueError("invalid version")
    parts = tuple(map(int, value.lstrip("vV").split(".")))
    return parts + (0,) * (8 - len(parts))


def check(project_name, installed):
    if not project_name:
        return "unavailable", ""
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", project_name) or project_name in {".", ".."}:
        return "error", ""
    request = Request(
        f"https://api.github.com/repos/Lehner-007/{project_name}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "PythonBasis"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("release response too large")
        latest = json.loads(payload)["tag_name"]
        return ("new" if version_key(latest) > version_key(installed) else "current", latest)
    except HTTPError as error:
        return ("unavailable" if error.code == 404 else "error", "")
    except (OSError, ValueError, HTTPException, KeyError, TypeError):
        return "error", ""


def load(path, project_name):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        interval = data.get("interval")
        raw_last = data.get("last")
        last = datetime.fromisoformat(raw_last) if isinstance(raw_last, str) else None
        return (interval if interval in INTERVALS else "weekly",
                last if data.get("project") == project_name and last is not None
                and last.tzinfo is None else None)
    except (OSError, ValueError, AttributeError):
        return "weekly", None


def save(path, interval, project_name, last):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump({"interval": interval, "project": project_name,
                       "last": last.isoformat() if last else None}, stream)
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
