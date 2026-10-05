"""Logging ke logs/<nama>.log dan konsol."""

from __future__ import annotations

import contextlib
import logging
import sys

from edupad.config import LOG_DIR


def setup_logging(name: str) -> logging.Logger:
    """Pasang handler sekali per proses. Aman untuk cron & pythonw (tanpa konsol)."""
    root = logging.getLogger()
    if not root.handlers:
        LOG_DIR.mkdir(exist_ok=True)
        root.setLevel(logging.INFO)
        file_handler = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        root.addHandler(file_handler)
        if sys.stdout:
            with contextlib.suppress(AttributeError):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(logging.Formatter("%(message)s"))
            root.addHandler(console)
    return logging.getLogger(name)
