"""Pipeline terjadwal: scrape -> assignments -> convert -> corpus -> summarize -> index.

Tiap langkah dijalankan sebagai proses terpisah agar memori Chromium/OCR
dilepas di antara langkah dan satu kegagalan tidak menghentikan yang lain.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time

from edupad.config import BASE_DIR
from edupad.core.notify import notify
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK

log = logging.getLogger(__name__)

STEP_TIMEOUT = 90 * 60


def _run_step(name: str, *args: str) -> int:
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "edupad", *args], cwd=BASE_DIR, timeout=STEP_TIMEOUT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # Windows Task Scheduler
        )
    except subprocess.TimeoutExpired:
        log.error("[x] %s melebihi %d menit", name, STEP_TIMEOUT // 60)
        return EXIT_ERROR
    for line in proc.stdout.splitlines():
        if "[selesai]" in line or "[x]" in line:
            log.info("    %s", line.strip())
    for line in proc.stderr.strip().splitlines()[-5:]:
        log.info("    %s", line.strip())
    log.info("[%s] %s selesai dalam %.0f detik (kode %d)",
             "ok" if proc.returncode == EXIT_OK else "!", name, time.time() - started, proc.returncode)
    return proc.returncode


def run() -> int:
    log.info("=== Pipeline dimulai ===")
    results = {"scrape": _run_step("scrape", "scrape", "--headless")}
    if results["scrape"] == EXIT_LOGIN_REQUIRED:
        results["assignments"] = EXIT_LOGIN_REQUIRED
    else:
        results["assignments"] = _run_step("assignments", "assignments")
    # Konversi & corpus tetap jalan: file yang sudah terunduh tetap valid.
    results["convert"] = _run_step("convert", "convert")
    results["corpus"] = _run_step("corpus", "corpus")
    results["summarize"] = _run_step("summarize", "summarize")
    results["index"] = _run_step("index", "index")

    if EXIT_LOGIN_REQUIRED in results.values():
        return EXIT_LOGIN_REQUIRED  # notifikasi sudah dikirim oleh langkah yang gagal
    if any(code != EXIT_OK for code in results.values()):
        summary = ", ".join(f"{k}={v}" for k, v in results.items())
        notify(f"⚠️ Pipeline bermasalah ({summary}). Cek logs/pipeline.log di server.")
        return EXIT_ERROR
    return EXIT_OK
