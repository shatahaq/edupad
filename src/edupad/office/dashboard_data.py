"""Adapter baca-saja untuk dashboard web EduPad.

Semua nilai berasal dari file/log EduPad atau tabel Supabase yang sudah ada.
Modul ini tidak menjalankan collector, model AI, migration, maupun probe API luar.
Jika sumber belum tersedia, koleksi dikembalikan kosong dan metrik yang tidak
dapat diukur dikembalikan sebagai ``None``.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from edupad.config import (
    ASSIGNMENTS_DIR,
    BASE_DIR,
    CORPUS_DIR,
    LOG_DIR,
    SCHEDULE_DIR,
    WIB,
    get_settings,
)
from edupad.core.supabase import SupabaseClient

STARTED_AT = time.monotonic()


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    except OSError:
        pass
    return rows


def _dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=WIB)
    except ValueError:
        return None


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 3) if values else 0.0


def _course_parts(value: str) -> tuple[str, str, str]:
    match = re.match(r"^\[([^]]+)]\s*(.*?)(?:\s*-\s*Kelas\s*(.*))?$", value.strip())
    if not match:
        return value.strip(), "", ""
    return match.group(2).strip(), match.group(1).strip(), (match.group(3) or "").strip()


def _overdue(flag: object, submitted: bool, deadline: object) -> bool:
    """Lewat deadline dihitung ulang terhadap waktu sekarang: data scraper bisa berumur jam/hari."""
    due = _dt(deadline)
    return bool(flag) or (not submitted and due is not None and due < datetime.now(WIB))


def assignments() -> dict:
    raw = _json(ASSIGNMENTS_DIR / "assignments.json", {})
    items = []
    for row in raw.get("tugas", []):
        course, code, _ = _course_parts(str(row.get("matkul") or ""))
        status = row.get("status") or {}
        submitted = bool(row.get("sudah_dikumpulkan"))
        grading = str(status.get("penilaian") or "").lower()
        timing = str(status.get("waktu") or "").lower()
        description = str(row.get("deskripsi") or "")
        attachments = row.get("lampiran") or []
        if not description and attachments:
            description = str(attachments[0].get("isi") or "")
        items.append(
            {
                "id": str(row.get("cmid") or row.get("id") or ""),
                "course": course,
                "kode": code,
                "jenis": "kuis" if row.get("jenis") == "kuis" else "tugas",
                "judul": str(row.get("judul") or "Tanpa judul"),
                "pertemuan": row.get("pertemuan"),
                "dibuka": row.get("dibuka"),
                "deadline": row.get("deadline"),
                "submitted": submitted,
                "late_submission": submitted and "terlambat" in timing,
                "overdue": _overdue(row.get("lewat_deadline"), submitted, row.get("deadline")),
                "graded": bool(grading and grading != "belum_dinilai"),
                "nilai": status.get("nilai"),
                "url": str(row.get("url") or ""),
                "soal": " ".join(description.split())[:600],
                "sumber": "kelas.usu",
            }
        )
    classroom = _classroom_tasks()
    items += classroom
    return {
        "updated_at": raw.get("diperbarui"),
        "tasks": items,
        "source": "local+classroom" if classroom else "local",
    }


def _classroom_tasks() -> list[dict]:
    """Tugas Google Classroom akun pemilik, disaring seperti yang diterima AI agent."""
    from edupad.agent.tools import _classroom, _relevant_classroom_task

    now = datetime.now(WIB)
    rows = []
    for data in _classroom():
        for task in data.get("tugas", []):
            if not _relevant_classroom_task(task, now):
                continue
            status = task.get("status") or {}
            grade = status.get("nilai")
            rows.append(
                {
                    "id": str(task.get("id") or task.get("url") or task.get("judul")),
                    "course": str(task.get("matkul") or ""),
                    "kode": "Classroom",
                    "jenis": "tugas",
                    "judul": str(task.get("judul") or "Tanpa judul"),
                    "pertemuan": task.get("pertemuan"),
                    "dibuka": task.get("dibuat"),
                    "deadline": task.get("deadline"),
                    "submitted": bool(task.get("sudah_dikumpulkan")),
                    "late_submission": bool(status.get("terlambat")),
                    "overdue": _overdue(
                        task.get("lewat_deadline"),
                        bool(task.get("sudah_dikumpulkan")),
                        task.get("deadline"),
                    ),
                    "graded": grade is not None,
                    "nilai": None if grade is None else str(grade),
                    "url": str(task.get("url") or ""),
                    "soal": " ".join(str(task.get("deskripsi") or "").split())[:600],
                    "sumber": "Google Classroom",
                }
            )
    return rows


def schedule() -> dict:
    raw = _json(SCHEDULE_DIR / "schedule.json", {})
    classes = []
    for row in raw.get("kelas", []):
        classes.append(
            {
                "hari": str(row.get("hari") or "senin").lower(),
                "mulai": str(row.get("mulai") or ""),
                "selesai": str(row.get("selesai") or ""),
                "kode": str(row.get("kode") or ""),
                "course": str(row.get("matkul") or ""),
                "jenis": "praktikum" if row.get("jenis") == "praktikum" else "teori",
                "kelas": str(row.get("kelas") or ""),
                "sks": int(row.get("sks") or 0),
                "ruang": str(row.get("ruang") or ""),
                "nama_ruang": str(row.get("nama_ruang") or ""),
                "dosen": list(row.get("dosen") or []),
            }
        )
    return {"updated_at": raw.get("diperbarui"), "classes": classes, "source": "local"}


def _presence_window(row: dict, now: datetime) -> str:
    if str(row.get("status") or "").lower() == "hadir":
        return "sudah_diisi"
    if row.get("dibuka") or row.get("perlu_diisi"):
        return "dibuka"
    start, end = _dt(row.get("mulai")), _dt(row.get("selesai"))
    if not start or not end:
        return "belum_dijadwalkan"
    if now < start:
        return "belum_dibuka"
    return "tutup"


def attendance() -> dict:
    raw = _json(SCHEDULE_DIR / "attendance.json", {})
    now = datetime.now(WIB)
    today: list[dict] = []
    upcoming: list[dict] = []
    recap: list[dict] = []
    for course in raw.get("mata_kuliah", []):
        meetings = list(course.get("pertemuan") or [])
        happened = [m for m in meetings if (_dt(m.get("mulai")) or now) <= now]
        recap.append(
            {
                "course": str(course.get("matkul") or ""),
                "kode": str(course.get("kode") or ""),
                "kelas": str(course.get("kelas") or ""),
                "hadir": sum(str(m.get("status") or "").lower() == "hadir" for m in happened),
                "pertemuan": len(happened),
            }
        )
        for meeting in meetings:
            start = _dt(meeting.get("mulai"))
            if not start:
                continue
            item = {
                "id": str(meeting.get("id") or ""),
                "course": str(course.get("matkul") or ""),
                "kode": str(course.get("kode") or ""),
                "kelas": str(course.get("kelas") or ""),
                "pertemuan": int(meeting.get("pertemuan") or 0),
                "topik": meeting.get("topik"),
                "mulai": meeting.get("mulai"),
                "selesai": meeting.get("selesai"),
                "status": "hadir" if str(meeting.get("status") or "").lower() == "hadir" else None,
                "window": _presence_window(meeting, now),
                "cara": [value for value in meeting.get("cara", []) if value in {"QR", "langsung"}],
            }
            delta = start.date() - now.date()
            if delta.days == 0:
                today.append(item)
            elif 0 < delta.days <= 7:
                upcoming.append(item)
    today.sort(key=lambda item: item.get("mulai") or "")
    upcoming.sort(key=lambda item: item.get("mulai") or "")
    updated = _dt(raw.get("diperbarui"))
    return {
        "updated_at": raw.get("diperbarui"),
        "stale": updated is None or now - updated.astimezone(WIB) > timedelta(hours=3),
        "today": today,
        "upcoming": upcoming,
        "recap": recap,
        "source": "local",
    }


def _supabase_turns(limit: int = 250, *, since: datetime | None = None) -> list[dict]:
    settings = get_settings()
    if not settings.supabase_key:
        return []
    filters = {
        "user_id": f"eq.{settings.user_id}",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    if since:
        filters["created_at"] = f"gte.{since.isoformat()}"
    try:
        return SupabaseClient().select(
            "agent_turns",
            "id,session_id,question,speech,screen,sources,usage,created_at",
            **filters,
        )
    except Exception:
        return []


def conversations() -> dict:
    settings = get_settings()
    if not settings.supabase_key:
        return {"sessions": [], "source": "unavailable"}
    try:
        client = SupabaseClient()
        sessions = client.select(
            "agent_sessions",
            "id,started_at,last_active,summary",
            user_id=f"eq.{settings.user_id}",
            order="last_active.desc",
            limit="20",
        )
        turns = _supabase_turns(300)
    except Exception:
        return {"sessions": [], "source": "unavailable"}
    grouped: dict[object, list[dict]] = defaultdict(list)
    for row in reversed(turns):
        usage = row.get("usage") or {}
        sources = []
        for source in row.get("sources") or []:
            sources.append(
                {
                    "matkul": str(source.get("matkul") or ""),
                    "pertemuan": list(source.get("pertemuan") or []),
                    "judul": source.get("judul"),
                }
            )
        grouped[row.get("session_id")].append(
            {
                "id": row.get("id"),
                "at": row.get("created_at"),
                "question": str(row.get("question") or ""),
                "speech": str(row.get("speech") or ""),
                "screen": list(row.get("screen") or []),
                "sources": sources,
                "tools": list(usage.get("tools") or []),
                "latency_s": usage.get("seconds"),
            }
        )
    return {
        "sessions": [
            {
                "id": row.get("id"),
                "started_at": row.get("started_at"),
                "last_active": row.get("last_active"),
                "summary": row.get("summary"),
                "turns": grouped.get(row.get("id"), []),
            }
            for row in sessions
        ],
        "source": "supabase",
    }


def learning() -> dict:
    now = datetime.now(WIB)
    turns = _supabase_turns(500, since=now - timedelta(days=30))
    daily = Counter()
    courses = Counter()
    meetings: dict[str, set[int]] = defaultdict(set)
    sources = Counter()
    source_titles: dict[tuple[str, int], str | None] = {}
    for row in turns:
        created = _dt(row.get("created_at"))
        if created:
            daily[created.astimezone(WIB).date().isoformat()] += 1
        for source in row.get("sources") or []:
            course = str(source.get("matkul") or "")
            if not course:
                continue
            courses[course] += 1
            for meeting in source.get("pertemuan") or []:
                if isinstance(meeting, int):
                    meetings[course].add(meeting)
                    sources[(course, meeting)] += 1
                    source_titles[(course, meeting)] = source.get("judul")
    facts: list[str] = []
    settings = get_settings()
    if settings.supabase_key:
        try:
            rows = SupabaseClient().select(
                "agent_memories", "content", user_id=f"eq.{settings.user_id}", limit="50"
            )
            facts = [str(row.get("content") or "") for row in rows if row.get("content")]
        except Exception:
            pass
    days = [(now.date() - timedelta(days=offset)).isoformat() for offset in range(29, -1, -1)]
    return {
        "window_days": 30,
        "questions_total": len(turns),
        "daily": [{"date": day, "questions": daily[day]} for day in days],
        "courses": [
            {"course": course, "questions": count, "meetings": sorted(meetings[course])}
            for course, count in courses.most_common()
        ],
        "sources_top": [
            {"course": key[0], "pertemuan": key[1], "judul": source_titles.get(key), "count": count}
            for key, count in sources.most_common(10)
        ],
        "facts": facts,
        "source": "supabase" if turns or facts else "unavailable",
    }


def knowledge() -> dict:
    rows = _jsonl(CORPUS_DIR / "chunks.jsonl")
    per_course: dict[str, dict[str, Any]] = {}
    for row in rows:
        course = str(row.get("matkul") or "Tanpa nama")
        current = per_course.setdefault(course, {"course": course, "chunks": 0, "meetings": set()})
        current["chunks"] += 1
        current["meetings"].update(
            value for value in row.get("pertemuan") or [] if isinstance(value, int)
        )
    worker_log = LOG_DIR / "office-worker.log"
    latest_ok: str | None = None
    try:
        matches = re.findall(
            r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d).*\[selesai]",
            worker_log.read_text(encoding="utf-8"),
            re.M,
        )
        if matches:
            latest_ok = datetime.fromisoformat(matches[-1]).replace(tzinfo=WIB).isoformat()
    except OSError:
        pass
    chunks_path = CORPUS_DIR / "chunks.jsonl"
    pending = 0
    if rows and (
        not latest_ok
        or chunks_path.stat().st_mtime
        > (_dt(latest_ok) or datetime.min.replace(tzinfo=WIB)).timestamp()
    ):
        pending = len(rows)
    return {
        "chunks_total": len(rows),
        "courses_total": len(per_course),
        "last_pipeline_at": latest_ok,
        "last_pipeline_ok": True if latest_ok else None,
        "new_materials_24h": sum(
            path.stat().st_mtime >= time.time() - 86400 for path in CORPUS_DIR.rglob("*.md")
        ),
        "pending_index": pending,
        "per_course": [
            {
                "course": value["course"],
                "chunks": value["chunks"],
                "meetings": len(value["meetings"]),
            }
            for value in sorted(per_course.values(), key=lambda item: item["chunks"], reverse=True)
        ],
        "source": "local",
    }


def _usage_rows(hours: int | None = None) -> list[dict]:
    rows = _jsonl(LOG_DIR / "agent_usage.jsonl")
    if hours is None:
        return rows
    cutoff = datetime.now(WIB) - timedelta(hours=hours)
    return [
        row for row in rows if (_dt(row.get("waktu")) or datetime.min.replace(tzinfo=WIB)) >= cutoff
    ]


ACCESS_LINE = re.compile(
    r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\S* INFO \S+ "(GET|POST) (/v1/\S*) HTTP/[\d.]+" (\d{3})'
)
DEVICE_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\S* INFO \[device\] (.*)$")
TIMING = re.compile(r"'(stt|agent)': ([\d.]+)")
SERVE_TAIL_BYTES = 3_000_000


def _tail_lines(path: Path, max_bytes: int = SERVE_TAIL_BYTES) -> list[str]:
    """Baris terakhir log (log server tidak dirotasi, jadi hanya bagian akhirnya dibaca)."""
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read()
    except OSError:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if size > max_bytes else lines


def device_requests(hours: int = 24) -> list[dict]:
    """Permintaan /v1/ask perangkat dari logs/serve.log: status, latensi stt+agent."""
    cutoff = datetime.now(WIB) - timedelta(hours=hours)
    asks: list[dict] = []
    pending: dict | None = None
    for line in _tail_lines(LOG_DIR / "serve.log"):
        device = DEVICE_LINE.match(line)
        if device:
            text = device.group(2)
            if text.startswith("tidak ada ucapan"):
                pending = {"no_speech": True, "latency_s": None}
            else:
                timing = dict(TIMING.findall(text))
                latency = sum(float(v) for v in timing.values()) if timing else None
                pending = {"no_speech": False, "latency_s": latency}
            continue
        access = ACCESS_LINE.match(line)
        if not access or access.group(2) != "POST" or not access.group(3).startswith("/v1/ask"):
            continue
        at = datetime.fromisoformat(access.group(1)).replace(tzinfo=WIB)
        code = int(access.group(4))
        info, pending = pending or {}, None
        if at < cutoff:
            continue
        if code >= 500:
            status = "server_error"
        elif code >= 400:
            status = "client_error"
        elif info.get("no_speech"):
            status = "no_speech"
        else:
            status = "ok"
        asks.append({"at": at, "status": status, "latency_s": info.get("latency_s")})
    return asks


def api_health() -> dict:
    now = datetime.now(WIB)
    asks = device_requests(24)
    buckets = []
    for offset in range(23, -1, -1):
        hour = (now - timedelta(hours=offset)).replace(minute=0, second=0, microsecond=0)
        rows = [a for a in asks if a["at"].replace(minute=0, second=0, microsecond=0) == hour]
        buckets.append(
            {
                "time": hour.isoformat(),
                "requests": len(rows),
                "errors": sum(a["status"] in {"client_error", "server_error"} for a in rows),
                "latency_avg_s": _mean([a["latency_s"] for a in rows if a["latency_s"]]),
            }
        )
    latency = sorted(a["latency_s"] for a in asks if a["latency_s"])
    p95 = latency[min(len(latency) - 1, math.ceil(len(latency) * 0.95) - 1)] if latency else 0
    status = Counter(a["status"] for a in asks)
    return {
        "window_hours": 24,
        "requests": len(asks),
        "by_status": {
            key: status.get(key, 0) for key in ("ok", "no_speech", "client_error", "server_error")
        },
        "latency_avg_s": _mean(latency),
        "latency_p95_s": round(p95, 3),
        "latency_goal_s": 6,
        "series": buckets,
        "source": "logs/serve.log",
    }


def agent() -> dict:
    rows = _usage_rows(24)
    tool_counts = Counter(tool for row in rows for tool in row.get("tools") or [])
    turns = _supabase_turns(250, since=datetime.now(WIB) - timedelta(hours=24))
    course_counts = Counter(
        str(source.get("matkul"))
        for row in turns
        for source in row.get("sources") or []
        if source.get("matkul")
    )
    sourced = sum(bool(row.get("sources")) for row in turns)
    eval_data = None
    results = sorted(
        (BASE_DIR / "evals" / "results").glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if results:
        raw = _json(results[0], {})
        summary = raw.get("ringkasan") or {}
        if raw:
            eval_data = {
                "label": str(raw.get("label") or results[0].stem),
                "score": float(summary.get("judge_ketepatan") or 0),
                "max_score": 5,
                "hallucinations": int(summary.get("halusinasi") or 0),
                "cases": int(summary.get("jawaban") or len(raw.get("jawaban") or [])),
            }
    return {
        "window_hours": 24,
        "answers": len(rows),
        "stage_avg_s": {
            "stt": None,
            "agent": _mean([float(row.get("detik") or 0) for row in rows]),
            "tts_first_audio": None,
        },
        "tokens_avg": round(_mean([float(row.get("total") or 0) for row in rows])),
        "llm_calls_avg": _mean([float(row.get("calls") or 0) for row in rows]),
        "with_source_pct": round(sourced / len(turns) * 100, 1) if turns else None,
        "eval": eval_data,
        "tools": [{"tool": name, "count": count} for name, count in tool_counts.most_common()],
        "top_courses": [
            {"course": name, "questions": count} for name, count in course_counts.most_common(8)
        ],
        "source": "local+supabase",
    }


def services() -> dict:
    settings = get_settings()
    configured = [
        ("deepseek", "DeepSeek", "Model jawaban dan ringkasan", bool(settings.llm_api_key)),
        (
            "cloudflare",
            "Cloudflare Workers AI",
            "Embedding dan reranking",
            bool(settings.cloudflare_account_id and settings.cloudflare_api_token),
        ),
        ("groq", "Groq Whisper", "Pengenalan suara", bool(settings.groq_api_key)),
        ("elevenlabs", "ElevenLabs", "Suara jawaban", bool(settings.elevenlabs_api_key)),
        ("supabase", "Supabase", "Memory dan indeks materi", bool(settings.supabase_key)),
    ]
    return {
        "services": [
            {
                "id": key,
                "name": name,
                "role": f"{'Terkonfigurasi' if ready else 'Belum dikonfigurasi'} · {role}",
                "state": "unknown" if ready else "down",
                "avg_latency_s": None,
                "errors_24h": 0,
                "quota": None,
            }
            for key, name, role, ready in configured
        ],
        "source": "configuration",
    }


def resources() -> dict:
    disk = shutil.disk_usage(BASE_DIR)
    result: dict[str, Any] = {
        "cpu_pct": None,
        "memory_pct": None,
        "disk_pct": round((disk.used / disk.total) * 100, 1) if disk.total else None,
        "memory_used_mb": None,
        "memory_total_mb": None,
        "active_sessions": 0,
        "uptime_s": round(time.monotonic() - STARTED_AT),
        "source": "local-process",
    }
    try:
        import psutil  # type: ignore[import-not-found]

        memory = psutil.virtual_memory()
        result.update(
            cpu_pct=psutil.cpu_percent(interval=None),
            memory_pct=memory.percent,
            memory_used_mb=round(memory.used / 1024 / 1024),
            memory_total_mb=round(memory.total / 1024 / 1024),
        )
    except ImportError:
        pass
    return result


def errors() -> dict:
    now = datetime.now(WIB)
    cutoff = now - timedelta(hours=24)
    events: list[tuple[datetime, str]] = []
    pattern = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d).*?(?:ERROR|WARNING)\s+(.*)$")
    for path in LOG_DIR.glob("*.log"):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            match = pattern.match(line)
            if not match:
                continue
            at = datetime.fromisoformat(match.group(1)).replace(tzinfo=WIB)
            if at >= cutoff:
                kind = match.group(2).split(":", 1)[0][:100]
                events.append((at, kind))
    counter = Counter(kind for _, kind in events)
    hours = [
        (now - timedelta(hours=value)).replace(minute=0, second=0, microsecond=0)
        for value in range(23, -1, -1)
    ]
    return {
        "by_hour": [
            {
                "time": hour.isoformat(),
                "count": sum(
                    at.replace(minute=0, second=0, microsecond=0) == hour for at, _ in events
                ),
            }
            for hour in hours
        ],
        "top": [
            {
                "kind": kind,
                "count": count,
                "last_at": max(at for at, value in events if value == kind).isoformat(),
            }
            for kind, count in counter.most_common(8)
        ],
        "source": "local-logs",
    }


def cost() -> dict:
    now = datetime.now(WIB)
    rows = [
        row
        for row in _usage_rows()
        if (_dt(row.get("waktu")) or now).astimezone(WIB).strftime("%Y-%m") == now.strftime("%Y-%m")
    ]
    daily = Counter()
    for row in rows:
        at = (_dt(row.get("waktu")) or now).astimezone(WIB)
        daily[at.date().isoformat()] += float(row.get("cost_usd") or 0)
    total = round(sum(daily.values()), 6)
    elapsed_days = max(1, now.day)
    forecast = round(total / elapsed_days * 30, 6)
    budget_raw = os.environ.get("EDUPAD_MONTHLY_BUDGET_USD", "").strip()
    try:
        budget = float(budget_raw) if budget_raw else None
    except ValueError:
        budget = None
    return {
        "month": now.strftime("%Y-%m"),
        "total_usd": total,
        "budget_month_usd": budget,
        "forecast_usd": forecast,
        "by_service": [{"service": "DeepSeek", "usd": total}],
        "daily": [{"date": day, "usd": round(value, 6)} for day, value in sorted(daily.items())],
        "source": "logs/agent_usage.jsonl",
    }


def activity() -> dict:
    now = datetime.now(WIB)
    turns = _supabase_turns(500, since=now - timedelta(days=7))
    matrix = [[0 for _ in range(24)] for _ in range(7)]
    questions = Counter()
    for row in turns:
        at = _dt(row.get("created_at"))
        if at:
            local = at.astimezone(WIB)
            matrix[local.weekday()][local.hour] += 1
        question = " ".join(str(row.get("question") or "").split())
        if question:
            questions[question] += 1
    return {
        "matrix": matrix,
        "top_questions": [
            {"text": text, "count": count} for text, count in questions.most_common(8)
        ],
        "source": "supabase" if turns else "unavailable",
    }


DEVICE_ONLINE = timedelta(minutes=5)  # perangkat menanyakan /v1/updates tiap 2 menit


def devices() -> dict:
    from edupad import device_status

    now = datetime.now(WIB)
    rows = []
    for row in device_status.devices():
        seen = _dt(row.get("last_seen"))
        latency = [float(v) for v in row.get("latency_s") or []]
        rows.append(
            {
                "id": row.get("id") or "edupad",
                "name": "EduPad " + str(row.get("id") or "")[-5:].replace(":", ""),
                "online": bool(seen and now - seen <= DEVICE_ONLINE),
                "last_seen": row.get("last_seen"),
                "battery_pct": None,  # perangkat memakai daya USB, tanpa baterai terukur
                "rssi_dbm": row.get("rssi_dbm"),
                "avg_latency_s": _mean(latency) if latency else None,
                "uptime_s": row.get("uptime_s"),
                "heap_free": row.get("heap_free"),
                "firmware": row.get("firmware"),
            }
        )
    return {"devices": rows, "source": "data/device/status.json" if rows else "unavailable"}


HISTORY_DAYS = 120


def tutor_panel() -> dict:
    """Penguasaan, kurva belajar per topik (skor tiap kuis), dan bantuan yang disiapkan SORA."""
    from edupad.agent import coach
    from edupad.agent.radar import mastery_overview
    from edupad.agent.tutor import TutorStore, TutorUnavailable, topic_key

    data = {**mastery_overview(), "history": [], "help": [], "source": "supabase"}
    if not data.get("available"):
        return data
    now = datetime.now(WIB)
    try:
        store = TutorStore()
        quizzes = store._run(
            store.db.select,
            "tutor_quizzes",
            "*",
            user_id=f"eq.{store.user_id}",
            order="created_at.asc",
            limit="500",
        )
        scores: dict[str, list[float]] = defaultdict(list)
        for c in store.checks(since=now - timedelta(days=HISTORY_DAYS)):
            scores[str(c.get("quiz_id"))].append(float(c["score"]))
        titles = {t["topic_key"]: t["title"] for t in store.mastery()}
        history: dict[str, dict] = {}
        for q in quizzes:
            got = scores.get(str(q["id"]))
            if not got:
                continue
            key = topic_key(q.get("course_id"), q["course"], q.get("meeting"))
            item = history.setdefault(
                key,
                {
                    "topic_key": key,
                    "matkul": q["course"],
                    "pertemuan": q.get("meeting"),
                    "judul": titles.get(key) or q.get("title") or "",
                    "titik": [],
                },
            )
            item["titik"].append(
                {
                    "waktu": q.get("created_at"),
                    "skor": round(sum(got) * 100 / len(got)),
                    "bantuan": bool(q.get("help_id")),
                }
            )
        data["history"] = sorted(history.values(), key=lambda h: -len(h["titik"]))
        data["help"] = [
            {
                "id": h["id"],
                "judul": h.get("title") or "",
                "matkul": h["course"],
                "pertemuan": h.get("meeting"),
                "status": h["status"],
                "alasan": list(h.get("reasons") or []),
                "masalah": h.get("problem") or "",
                "pelajaran": [part.get("ucapan") or "" for part in h.get("lesson") or []],
                "soal": len(h.get("questions") or []),
                "sebelum": None
                if h.get("mastery_before") is None
                else round(float(h["mastery_before"]) * 100),
                "sesudah": None
                if h.get("mastery_after") is None
                else round(float(h["mastery_after"]) * 100),
                "dibuat": h.get("created_at"),
                "selesai": h.get("finished_at"),
            }
            for h in coach.helps(store, 20)
        ]
    except TutorUnavailable as e:
        data["help_reason"] = str(e)
    return data


def equity() -> dict:
    """Learning Equity Radar pribadi: pemahaman, akses materi, peringatan dini, akses suara."""
    from edupad.agent.radar import access_audit, attendance_risk, early_warnings, mastery_overview

    now = datetime.now(WIB)
    audit = access_audit(now)
    mastery = mastery_overview(now)
    asks = device_requests(24 * 30)
    answered = [a for a in asks if a["status"] == "ok"]
    return {
        "access": audit,
        "attendance": attendance_risk(now),
        "warnings": early_warnings(now),
        "mastery": {k: v for k, v in mastery.items() if k not in {"checks"}},
        "voice": {
            "questions_30d": len(answered),
            "listenable_meetings": audit["bisa_didengar"],
            "meetings_with_material": audit["pertemuan_bermateri"],
        },
        "rules": dict(
            zip(("semester_meetings", "min_attendance"), _attendance_rules(), strict=True)
        ),
        "source": "local+supabase",
    }


def _attendance_rules() -> tuple[int, float]:
    from edupad.agent.radar import attendance_rules

    return attendance_rules()


def finance_panel() -> dict:
    from edupad.agent.finance import (
        EXPENSE_CATEGORIES,
        INCOME_CATEGORIES,
        FinanceStore,
        FinanceUnavailable,
    )

    base = {"expense_categories": EXPENSE_CATEGORIES, "income_categories": INCOME_CATEGORIES}
    try:
        store = FinanceStore()
        return {
            **base,
            "available": True,
            "transactions": store.transactions(),
            "budgets": store.budgets(),
            "source": "supabase",
        }
    except FinanceUnavailable as e:
        return {
            **base,
            "available": False,
            "reason": str(e),
            "transactions": [],
            "budgets": {},
            "source": "unavailable",
        }


PANELS = {
    "devices": devices,
    "api": api_health,
    "agent": agent,
    "services": services,
    "resources": resources,
    "knowledge": knowledge,
    "errors": errors,
    "cost": cost,
    "activity": activity,
    "attendance": attendance,
    "assignments": assignments,
    "schedule": schedule,
    "conversations": conversations,
    "learning": learning,
    "tutor": tutor_panel,
    "equity": equity,
    "finance": finance_panel,
}


def panel(name: str) -> dict:
    try:
        loader = PANELS[name]
    except KeyError as exc:
        raise KeyError(f"Panel dashboard tidak dikenal: {name}") from exc
    return loader()
