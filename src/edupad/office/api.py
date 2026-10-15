"""FastAPI adapter untuk dashboard EduPad AI Office."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from edupad.office.chat_history import list_recent_iot_chats
from edupad.office.dashboard_data import PANELS, panel
from edupad.office.events import build_snapshot
from edupad.office.repository import get_repository

log = logging.getLogger(__name__)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    assigned_agent: str = "coordinator"
    job_type: Literal["manual", "index"] = "manual"
    due_at: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal["low", "medium", "high"] | None = None
    status: Literal["queued", "in_progress", "completed", "failed", "cancelled"] | None = None
    assigned_agent: str | None = None
    due_at: str | None = None


def _origins() -> list[str]:
    raw = os.environ.get(
        "EDUPAD_OFFICE_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    )
    return [value.strip() for value in raw.split(",") if value.strip()]


def create_app() -> FastAPI:
    app = FastAPI(title="EduPad AI Office API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )

    @app.get("/api/office/health")
    def health() -> dict:
        return {"status": "ok", "service": "edupad-office"}

    @app.get("/api/office/snapshot")
    def snapshot() -> dict:
        return build_snapshot()

    @app.get("/api/office/tasks")
    def list_tasks() -> list[dict]:
        return get_repository().list_tasks()

    @app.get("/api/office/chat-history")
    def chat_history(limit: int = Query(default=12, ge=1, le=50)) -> dict:
        """Riwayat jawaban agent dari perangkat IoT, tanpa payload internal LLM."""
        try:
            return {"source": "supabase", "items": list_recent_iot_chats(limit)}
        except Exception as exc:  # dashboard tetap hidup saat Supabase belum siap
            log.warning("Riwayat chat IoT tidak tersedia: %s", type(exc).__name__)
            return {"source": "unavailable", "items": []}

    @app.get("/v1/dashboard/{panel_name}")
    def dashboard_panel(panel_name: str) -> dict:
        """Data dashboard baca-saja dari sumber EduPad yang sudah tersedia."""
        if panel_name not in PANELS:
            raise HTTPException(status_code=404, detail="Panel dashboard tidak ditemukan")
        return panel(panel_name)

    @app.post("/api/office/tasks", status_code=201)
    def create_task(task: TaskCreate) -> dict:
        repository = get_repository()
        values = task.model_dump()
        if task.job_type == "index":
            if not repository.supports_claiming:
                raise HTTPException(
                    status_code=409,
                    detail="Worker Supabase belum diaktifkan: migration claiming belum disetujui",
                )
            values["assigned_agent"] = "researcher"
        return repository.create_task(values)

    @app.patch("/api/office/tasks/{task_id}")
    def update_task(task_id: str, update: TaskUpdate) -> dict:
        values = update.model_dump(exclude_none=True)
        row = get_repository().update_task(task_id, values)
        if row is None:
            raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
        return row

    @app.get("/api/office/events")
    async def events(
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        after: str | None = Query(default=None),
    ) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            marker = after or last_event_id
            heartbeat = 0
            while True:
                rows = get_repository().list_events(after=marker, limit=100)
                for row in rows:
                    marker = str(row["id"])
                    yield f"id: {marker}\nevent: office.status\ndata: {json.dumps(row, ensure_ascii=False)}\n\n"
                heartbeat += 1
                if heartbeat % 15 == 0:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()


def run(host: str = "127.0.0.1", port: int = 8001) -> int:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
