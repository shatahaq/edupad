"""Utilitas file: JSON atomik, nama file aman, hash."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from edupad.config import WIB

NAME_MAXLEN = 60  # path Windows dibatasi 260 karakter

_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                 *(f"LPT{i}" for i in range(1, 10))}


def now_iso() -> str:
    return datetime.now(WIB).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    """Isi file JSON, atau {} bila tidak ada / rusak."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_text_atomic(path: Path, text: str, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    if private and sys.platform != "win32":
        os.chmod(tmp, 0o600)
    tmp.replace(path)


def write_json(path: Path, data: object, private: bool = False) -> None:
    write_text_atomic(path, json.dumps(data, indent=2, ensure_ascii=False), private)


def write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    write_text_atomic(path, text)
    return True


def safe_name(text: str, maxlen: int = NAME_MAXLEN) -> str:
    """Teks bebas -> nama file/folder yang valid di Windows & Linux."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = text[:maxlen].rstrip(" .")
    if text.split(".")[0].upper() in _WIN_RESERVED:
        text = f"_{text}"
    return text or "untitled"


def safe_filename(name: str, maxlen: int = NAME_MAXLEN) -> str:
    """Seperti safe_name, tapi ekstensi tidak ikut terpotong."""
    stem, dot, ext = name.rpartition(".")
    if not dot or len(ext) > 6:
        return safe_name(name, maxlen)
    return f"{safe_name(stem, maxlen - len(ext) - 1)}.{ext.lower()}"
