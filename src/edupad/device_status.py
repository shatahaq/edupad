"""Status perangkat ESP32 terakhir (dashboard: Monitoring -> Perangkat).

Firmware mengirim header di setiap permintaan /v1/*: X-Device-Id (MAC), X-Device-RSSI (dBm),
X-Device-Uptime (detik), X-Device-Heap (byte), X-Firmware. Server menyimpan nilai terakhir per
perangkat di data/device/status.json, paling sering sekali per WRITE_EVERY detik.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime

from edupad.config import DATA_DIR, WIB
from edupad.core.files import read_json, write_json

log = logging.getLogger(__name__)

STATUS_FILE = DATA_DIR / "device" / "status.json"
WRITE_EVERY = 30
_SAFE = re.compile(r"[^A-Za-z0-9:._ -]")
_state: dict[str, dict] = {}
_written_at = 0.0
_lock = threading.Lock()


def _int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def record(headers, path: str, latency_s: float | None = None) -> None:
    """Catat status dari header permintaan perangkat; tidak pernah melempar error."""
    global _written_at
    try:
        device_id = _SAFE.sub("", headers.get("X-Device-Id") or "")[:32] or "edupad"
        now = datetime.now(WIB).isoformat(timespec="seconds")
        with _lock:
            if not _state:
                _state.update(read_json(STATUS_FILE))
            row = _state.setdefault(device_id, {"id": device_id})
            row.update(
                last_seen=now,
                last_path=path,
                rssi_dbm=_int(headers.get("X-Device-RSSI")),
                uptime_s=_int(headers.get("X-Device-Uptime")),
                heap_free=_int(headers.get("X-Device-Heap")),
                firmware=_SAFE.sub("", headers.get("X-Firmware") or "")[:24] or None,
            )
            if latency_s is not None:
                recent = (row.get("latency_s") or [])[-19:] + [round(latency_s, 2)]
                row["latency_s"] = recent
            if time.monotonic() - _written_at >= WRITE_EVERY or latency_s is not None:
                write_json(STATUS_FILE, _state)
                _written_at = time.monotonic()
    except Exception as e:  # noqa: BLE001 - status perangkat hanya untuk dashboard
        log.debug("[device] status tidak tercatat: %s", e)


def devices() -> list[dict]:
    with _lock:
        state = dict(_state) if _state else read_json(STATUS_FILE)
    return list(state.values())
