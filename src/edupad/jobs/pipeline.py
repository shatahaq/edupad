"""Pipeline terjadwal: scrape -> assignments -> convert -> corpus -> summarize -> index.

Tiap langkah dijalankan sebagai proses terpisah agar memori Chromium/OCR
dilepas di antara langkah dan satu kegagalan tidak menghentikan yang lain.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
import uuid

from edupad.config import BASE_DIR
from edupad.core.notify import notify
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK
from edupad.office.events import emit_status
from edupad.office.models import AgentState

log = logging.getLogger(__name__)

STEP_TIMEOUT = 90 * 60

STEP_AGENT = {
    "scrape": ("researcher", "research-lab"),
    "assignments": ("planner", "planning-hub"),
    "convert": ("researcher", "research-lab"),
    "corpus": ("keeper", "knowledge-server"),
    "summarize": ("researcher", "research-lab"),
    "index": ("keeper", "knowledge-server"),
}


def _run_step(name: str, *args: str, run_id: str | None = None, progress: int = 0) -> int:
    started = time.time()
    agent_id, room = STEP_AGENT.get(name, ("coordinator", "command-center"))
    emit_status(
        agent_id,
        AgentState.RUNNING,
        room=room,
        job_type=name,
        message=f"Menjalankan {name}",
        progress=progress,
        run_id=run_id,
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "edupad", *args],
            cwd=BASE_DIR,
            timeout=STEP_TIMEOUT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # Windows Task Scheduler
        )
    except subprocess.TimeoutExpired:
        log.error("[x] %s melebihi %d menit", name, STEP_TIMEOUT // 60)
        emit_status(
            agent_id,
            AgentState.FAILED,
            room=room,
            job_type=name,
            message=f"{name} melewati batas waktu",
            progress=progress,
            run_id=run_id,
        )
        return EXIT_ERROR
    for line in proc.stdout.splitlines():
        if "[selesai]" in line or "[x]" in line:
            log.info("    %s", line.strip())
    for line in proc.stderr.strip().splitlines()[-5:]:
        log.info("    %s", line.strip())
    log.info(
        "[%s] %s selesai dalam %.0f detik (kode %d)",
        "ok" if proc.returncode == EXIT_OK else "!",
        name,
        time.time() - started,
        proc.returncode,
    )
    emit_status(
        agent_id,
        AgentState.SUCCEEDED if proc.returncode == EXIT_OK else AgentState.FAILED,
        room=room,
        job_type=name,
        message=f"{name} {'selesai' if proc.returncode == EXIT_OK else 'bermasalah'}",
        progress=min(progress + 15, 100),
        run_id=run_id,
        metadata={"exit_code": proc.returncode, "seconds": round(time.time() - started, 1)},
    )
    return proc.returncode


def run() -> int:
    run_id = f"pipeline-{uuid.uuid4().hex[:12]}"
    log.info("=== Pipeline dimulai ===")
    emit_status(
        "coordinator",
        AgentState.RUNNING,
        room="command-center",
        job_type="pipeline",
        message="Pipeline pembaruan dimulai",
        progress=2,
        run_id=run_id,
    )
    results = {"scrape": _run_step("scrape", "scrape", "--headless", run_id=run_id, progress=5)}
    if results["scrape"] == EXIT_LOGIN_REQUIRED:
        results["assignments"] = EXIT_LOGIN_REQUIRED
    else:
        results["assignments"] = _run_step("assignments", "assignments", run_id=run_id, progress=20)
    # Konversi & corpus tetap jalan: file yang sudah terunduh tetap valid.
    results["convert"] = _run_step("convert", "convert", run_id=run_id, progress=35)
    results["corpus"] = _run_step("corpus", "corpus", run_id=run_id, progress=50)
    results["summarize"] = _run_step("summarize", "summarize", run_id=run_id, progress=65)
    results["index"] = _run_step("index", "index", run_id=run_id, progress=82)

    if EXIT_LOGIN_REQUIRED in results.values():
        emit_status(
            "coordinator",
            AgentState.WAITING,
            room="command-center",
            job_type="pipeline",
            message="Pipeline menunggu login ulang",
            progress=90,
            run_id=run_id,
        )
        return EXIT_LOGIN_REQUIRED  # notifikasi sudah dikirim oleh langkah yang gagal
    if any(code != EXIT_OK for code in results.values()):
        summary = ", ".join(f"{k}={v}" for k, v in results.items())
        notify(f"⚠️ Pipeline bermasalah ({summary}). Cek logs/pipeline.log di server.")
        emit_status(
            "coordinator",
            AgentState.FAILED,
            room="command-center",
            job_type="pipeline",
            message="Sebagian tahap pipeline gagal",
            progress=100,
            run_id=run_id,
            metadata={"results": results},
        )
        return EXIT_ERROR
    emit_status(
        "coordinator",
        AgentState.SUCCEEDED,
        room="command-center",
        job_type="pipeline",
        message="Seluruh pipeline selesai",
        progress=100,
        run_id=run_id,
        metadata={"results": results},
    )
    return EXIT_OK
