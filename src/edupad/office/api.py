"""FastAPI adapter untuk dashboard EduPad AI Office.

Semua endpoint (kecuali /api/office/health) memerlukan sesi login Google pemilik dari web
EduPad (lihat office/auth.py). Di produksi Caddy meneruskan /api/office/* dan
/v1/dashboard/* ke proses ini, sehingga dashboard, login, dan API satu origin.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from edupad.config import BASE_DIR
from edupad.office.auth import Viewer, require_owner
from edupad.office.chat_history import list_recent_iot_chats
from edupad.office.dashboard_data import PANELS, panel
from edupad.office.events import build_snapshot, emit_status
from edupad.office.models import AgentState
from edupad.office.repository import get_repository

log = logging.getLogger(__name__)

# Hasil `npm run build` di dashboard/ (base /dashboard/); data tetap lewat endpoint berizin.
DASHBOARD_DIST = BASE_DIR / "dashboard" / "dist"

Owner = Annotated[Viewer, Depends(require_owner)]


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


class TransactionIn(BaseModel):
    kind: Literal["income", "expense"]
    amount: int = Field(gt=0, le=1_000_000_000)
    category: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=200)
    date: str | None = Field(default=None, max_length=10)


class BudgetIn(BaseModel):
    amount: int = Field(ge=0, le=1_000_000_000)


class FinanceImport(BaseModel):
    """Pindahan sekali dari localStorage dashboard lama ke Supabase."""

    transactions: list[TransactionIn] = Field(default_factory=list, max_length=2000)
    budgets: dict[str, int] = Field(default_factory=dict)


class DashboardFiles(StaticFiles):
    """index.html selalu dicek ulang agar deploy baru langsung terpakai; aset ber-hash tetap
    boleh di-cache browser."""

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        if str(full_path).endswith(".html"):
            response.headers["Cache-Control"] = "no-cache"
        return response


def _origins() -> list[str]:
    raw = os.environ.get(
        "EDUPAD_OFFICE_ORIGINS",
        "http://localhost:5174,http://127.0.0.1:5174",
    )
    return [value.strip() for value in raw.split(",") if value.strip()]


def _finance_store(viewer: Viewer):
    from edupad.agent.finance import FinanceStore, FinanceUnavailable

    try:
        return FinanceStore(viewer.user_id)
    except FinanceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _finance_call(fn, *args, **kwargs):
    from edupad.agent.finance import FinanceInputError, FinanceUnavailable

    try:
        return fn(*args, **kwargs)
    except FinanceInputError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except FinanceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _finance_event(message: str) -> None:
    emit_status(
        "finance",
        AgentState.SUCCEEDED,
        room="finance-office",
        job_type="finance",
        message=message,
        progress=100,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="EduPad AI Office API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )

    @app.get("/api/office/health")
    def health() -> dict:
        return {"status": "ok", "service": "edupad-office"}

    api = APIRouter(dependencies=[Depends(require_owner)])

    @api.get("/api/office/snapshot")
    def snapshot() -> dict:
        return build_snapshot()

    @api.get("/api/office/tasks")
    def list_tasks() -> list[dict]:
        return get_repository().list_tasks()

    @api.get("/api/office/chat-history")
    def chat_history(limit: int = Query(default=12, ge=1, le=50)) -> dict:
        """Riwayat jawaban agent dari perangkat IoT, tanpa payload internal LLM."""
        try:
            return {"source": "supabase", "items": list_recent_iot_chats(limit)}
        except Exception as exc:  # dashboard tetap hidup saat Supabase belum siap
            log.warning("Riwayat chat IoT tidak tersedia: %s", type(exc).__name__)
            return {"source": "unavailable", "items": []}

    @api.get("/v1/dashboard/{panel_name}")
    def dashboard_panel(panel_name: str) -> dict:
        """Data dashboard baca-saja dari sumber EduPad yang sudah tersedia."""
        if panel_name not in PANELS:
            raise HTTPException(status_code=404, detail="Panel dashboard tidak ditemukan")
        return panel(panel_name)

    @api.post("/api/office/tasks", status_code=201)
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

    @api.patch("/api/office/tasks/{task_id}")
    def update_task(task_id: str, update: TaskUpdate) -> dict:
        values = update.model_dump(exclude_none=True)
        row = get_repository().update_task(task_id, values)
        if row is None:
            raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
        return row

    # ------------------------------ keuangan ------------------------------
    @api.post("/api/office/finance/transactions", status_code=201)
    def add_transaction(body: TransactionIn, viewer: Owner) -> dict:
        store = _finance_store(viewer)
        row = _finance_call(
            store.add, body.kind, body.amount, body.category, body.note, body.date, "dashboard"
        )
        _finance_event("Transaksi baru dari dashboard dicatat")
        return row

    @api.delete("/api/office/finance/transactions/{transaction_id}", status_code=204)
    def delete_transaction(transaction_id: str, viewer: Owner) -> None:
        store = _finance_store(viewer)
        _finance_call(store.delete, transaction_id)

    @api.put("/api/office/finance/budgets/{category}")
    def put_budget(category: str, body: BudgetIn, viewer: Owner) -> dict:
        store = _finance_store(viewer)
        row = _finance_call(store.set_budget, category, body.amount)
        _finance_event(f"Anggaran {row['category']} diperbarui")
        return row

    @api.post("/api/office/finance/import")
    def import_finance(body: FinanceImport, viewer: Owner) -> dict:
        store = _finance_store(viewer)
        added = 0
        for item in body.transactions:
            _finance_call(
                store.add, item.kind, item.amount, item.category, item.note, item.date, "impor"
            )
            added += 1
        for category, amount in body.budgets.items():
            _finance_call(store.set_budget, category, amount)
        if added or body.budgets:
            _finance_event(f"{added} transaksi lama dipindahkan dari browser")
        return {"transactions": added, "budgets": len(body.budgets)}

    @api.get("/api/office/events")
    async def events(
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        after: str | None = Query(default=None),
    ) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            marker = after or last_event_id
            heartbeat = 0
            while True:
                # Query Supabase bersifat blocking: jalankan di thread agar event loop
                # (dan permintaan lain ke proses ini) tidak ikut menunggu.
                rows = await asyncio.to_thread(
                    get_repository().list_events, after=marker, limit=100
                )
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

    app.include_router(api)
    if DASHBOARD_DIST.is_dir():
        app.mount(
            "/dashboard", DashboardFiles(directory=DASHBOARD_DIST, html=True), name="dashboard"
        )
    return app


app = create_app()


def run(host: str = "127.0.0.1", port: int = 8001) -> int:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
