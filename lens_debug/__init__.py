"""Lens - send debug payloads to the Lens desktop app.

Usage:
    from lens_debug import lens

    lens("hello", user)                 # log any values
    lens([1, 2, 3]).label("my array")   # add a label
    lens("careful").red()               # colour the entry
    lens.exception(err)                 # send a caught exception
    lens.clear()                        # clear the Lens window

Debugging must never break your program, so every transmission runs on a
daemon thread and swallows all errors silently.
"""

import os
import atexit
import queue
import threading
import traceback
import uuid
import json
import time as _time
from urllib import request as _request

__version__ = "1.1.0"

_CONFIG = {
    "host": os.environ.get("LENS_HOST", "127.0.0.1"),
    "port": int(os.environ.get("LENS_PORT", "23600")),
    "cloud_url": os.environ.get("LENS_CLOUD_URL"),
    "key": os.environ.get("LENS_PROJECT_KEY"),
}


def _resolve_key():
    return _CONFIG.get("key") or os.environ.get("LENS_PROJECT_KEY")


def _resolve_cloud_url():
    u = _CONFIG.get("cloud_url") or os.environ.get("LENS_CLOUD_URL")
    return u.rstrip("/") if u else None

_THIS_FILE = os.path.abspath(__file__)
_COLORS = ("red", "green", "blue", "orange", "purple", "gray")

# A single worker drains this queue in order, so chained calls (.label(),
# .color()) always reach the app in the sequence they were made.
_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _worker():
    while True:
        url, body, headers = _queue.get()
        try:
            req = _request.Request(url, data=body, headers=headers, method="POST")
            _request.urlopen(req, timeout=3)  # noqa: S310
        except Exception:
            pass  # never let debugging crash the host program
        finally:
            _queue.task_done()


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True).start()
            _worker_started = True


def _drain(timeout=3.0):
    """Best-effort flush on interpreter exit so short scripts don't drop the tail."""
    end = _time.time() + timeout
    while not _queue.empty() and _time.time() < end:
        _time.sleep(0.02)


atexit.register(_drain)


def _detect_framework():
    """Best-effort framework detection; falls back to "Plain Python"."""
    import sys
    mods = sys.modules
    try:
        if "django" in mods:
            return "Django " + mods["django"].get_version()
        if "flask" in mods:
            return "Flask " + getattr(mods["flask"], "__version__", "")
        if "fastapi" in mods:
            return "FastAPI " + getattr(mods["fastapi"], "__version__", "")
    except Exception:
        pass
    return "Plain Python"


def _system_context():
    """Runtime info that helps debugging: Python version, OS, hostname, framework."""
    import platform
    import socket
    ctx = {
        "runtime": "Python " + platform.python_version(),
        "os": (platform.system() + " " + platform.release()).strip(),
    }
    try:
        ctx["hostname"] = socket.gethostname()
    except Exception:
        pass
    framework = _detect_framework()
    if framework:
        ctx["framework"] = framework
    return {k: v for k, v in ctx.items() if v}


def _transmit(payload):
    payload.setdefault("time", int(_time.time() * 1000))
    payload["meta"] = {"client": "python", "version": __version__}
    key = _resolve_key()
    if key:
        payload["key"] = key
    payload_type = payload.get("type", "log")
    if payload_type not in ("clear", "pause"):
        payload["context"] = _system_context()
    body = json.dumps(payload, default=_safe).encode("utf-8")

    _ensure_worker()

    # Local Lens desktop app.
    local_url = "http://%s:%d" % (_CONFIG["host"], _CONFIG["port"])
    _queue.put((local_url, body, {"Content-Type": "application/json"}))

    # Lens Cloud, straight from the client, no desktop required.
    cloud_url = _resolve_cloud_url()
    if cloud_url and key and payload_type not in ("clear", "pause"):
        _queue.put((
            cloud_url + "/api/ingest",
            body,
            {"Content-Type": "application/json", "x-lens-key": key},
        ))


def _safe(obj):
    """Fallback serializer for values json cannot handle natively."""
    try:
        return vars(obj)
    except Exception:
        return repr(obj)


def _resolve_origin():
    """Find the caller's file and line, skipping frames inside this package."""
    for frame in reversed(traceback.extract_stack()):
        if os.path.abspath(frame.filename) != _THIS_FILE:
            return {"file": frame.filename, "line": frame.lineno}
    return {"file": None, "line": None}


class Lens:
    def __init__(self, values):
        self.id = str(uuid.uuid4())
        self.values = list(values)
        self._label = None
        self._color = None
        self.origin = _resolve_origin()
        self._send()

    def label(self, label):
        self._label = label
        return self._send()

    def color(self, color):
        self._color = color
        return self._send()

    def _send(self):
        _transmit({
            "id": self.id,
            "type": "log",
            "label": self._label,
            "color": self._color,
            "origin": self.origin,
            "values": self.values,
        })
        return self


def _make_color(name):
    def _setter(self):
        return self.color(name)
    return _setter


for _c in _COLORS:
    setattr(Lens, _c, _make_color(_c))


def lens(*values):
    """Send any values to Lens and return a chainable handle."""
    return Lens(values)


def _clear():
    _transmit({"id": str(uuid.uuid4()), "type": "clear"})


def _exception(exc):
    """Send a caught exception so it shows up (and can be AI-summarized) in Lens."""
    tb = traceback.extract_tb(exc.__traceback__)
    last = tb[-1] if tb else None
    _transmit({
        "id": str(uuid.uuid4()),
        "type": "exception",
        "exception": {
            "class": type(exc).__name__,
            "message": str(exc),
            "file": last.filename if last else None,
            "line": last.lineno if last else None,
            "frames": [
                {"function": f.name, "file": f.filename, "line": f.lineno} for f in tb
            ],
        },
    })


def _configure(host=None, port=None, cloud_url=None, key=None):
    if host is not None:
        _CONFIG["host"] = host
    if port is not None:
        _CONFIG["port"] = int(port)
    if cloud_url is not None:
        _CONFIG["cloud_url"] = cloud_url.rstrip("/") if cloud_url else None
    if key is not None:
        _CONFIG["key"] = key or None


lens.clear = _clear
lens.exception = _exception
lens.configure = _configure

__all__ = ["lens", "Lens"]
