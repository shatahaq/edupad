"""Notifikasi Telegram. Tanpa token, pesan hanya dicatat di log."""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request

from edupad.config import get_settings

log = logging.getLogger(__name__)


def notify(message: str) -> bool:
    settings = get_settings()
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        log.info("[notif] (Telegram belum diatur) %s", message)
        return False
    data = urllib.parse.urlencode({"chat_id": settings.telegram_chat_id, "text": message}).encode()
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        urllib.request.urlopen(url, data=data, timeout=20)
        return True
    except OSError as e:
        log.warning("[notif] gagal kirim Telegram: %s", e)
        return False
