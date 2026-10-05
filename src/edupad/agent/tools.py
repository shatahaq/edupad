"""Tools yang bisa dipanggil LLM: pencarian vektor, materi per pertemuan, tugas."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from edupad.config import ASSIGNMENTS_DIR, CORPUS_DIR, SCHEDULE_DIR, WIB, get_settings
from edupad.core.files import read_json
from edupad.core.supabase import SupabaseClient
from edupad.processing.embeddings import EmbeddingError, embed_query, rerank
from edupad.processing.summaries import get_summary

log = logging.getLogger(__name__)

CATALOG_FILE = CORPUS_DIR / "catalog.json"
ASSIGNMENTS_FILE = ASSIGNMENTS_DIR / "assignments.json"
ATTENDANCE_FILE = SCHEDULE_DIR / "attendance.json"
STALE_AFTER = timedelta(hours=3)  # cron presensi berjalan tiap 2 menit di jam kuliah
MAX_MEETING_CHARS = 40_000
SNIPPET_CHARS = 1_800
CANDIDATES = 20
RERANK_CHARS = 1_500
# Fusi peringkat hybrid (vektor+kata kunci) dan reranker; diuji pada evals/agent_cases.json:
# benar di peringkat 1 14/17 (hybrid 13, reranker 12), 4 teratas 17/17 (hybrid 16).
FUSION_K = 30
RERANK_WEIGHT = 2.0
USE_MEETING_SUMMARIES = True  # dimatikan evaluasi untuk membandingkan
STOPWORDS = {"apa", "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "itu", "ini",
             "materi", "tentang", "jelaskan", "bagaimana", "cara", "adalah", "dalam", "the", "of"}


def _catalog() -> list[dict]:
    return read_json(CATALOG_FILE).get("mata_kuliah", [])


def resolve_course(name: str | None) -> dict | None:
    """Nama/alias/kode/ID mata kuliah -> entri katalog.

    Nama tanpa kata 'praktikum' diarahkan ke kelas teori agar 'PV' tidak tertukar
    dengan 'Praktikum PV'.
    """
    if not name:
        return None
    query = re.sub(r"\s+", " ", name.lower()).strip()
    courses = _catalog()
    for course in courses:
        if query in (course["course_id"], *course["alias"]):
            return course
    matches = [c for c in courses if query in c["matkul"].lower() or any(query in a for a in c["alias"])]
    if len(matches) > 1 and "prak" not in query:
        matches = [c for c in matches if not c["matkul"].lower().startswith("praktikum")] or matches
    return matches[0] if matches else None


def _keyword_query(text: str) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 1]
    return " | ".join(dict.fromkeys(words))


def course_overview() -> str:
    """Ringkasan mata kuliah untuk system prompt, agar LLM tidak perlu memanggil tool."""
    lines = []
    for c in _catalog():
        meetings = ", ".join(k for k in c["pertemuan"] if k != "umum") or "-"
        short = min((a for a in c["alias"] if len(a) <= 6), key=len, default="")
        lines.append(f"- {c['matkul']} ({c['kode']}{', ' + short.upper() if short else ''}); "
                     f"dosen {', '.join(c['dosen']) or '-'}; jadwal {c['jadwal'] or '-'}; "
                     f"materi pertemuan: {meetings}")
    return "\n".join(lines)


# ------------------------------- tools ---------------------------------------
def fuse_rankings(rows: list[dict], scores: list[float]) -> list[dict]:
    """Gabungkan urutan hybrid (urutan rows) dengan urutan skor reranker (reciprocal rank fusion)."""
    by_score = sorted(range(len(rows)), key=lambda i: -scores[i])
    rerank_rank = {i: rank for rank, i in enumerate(by_score)}
    order = sorted(range(len(rows)),
                   key=lambda i: -(1 / (FUSION_K + i) + RERANK_WEIGHT / (FUSION_K + rerank_rank[i])))
    return [rows[i] for i in order]


def search_materials(query: str, course: str | None = None, meeting: int | None = None,
                     limit: int = 4) -> dict:
    target = resolve_course(course)
    if course and not target:
        return {"error": f"mata kuliah '{course}' tidak ditemukan", "pilihan": [c["matkul"] for c in _catalog()]}
    started = time.time()
    rows = SupabaseClient().rpc(
        "match_material_chunks",
        query_embedding=embed_query(query), query_text=_keyword_query(query),
        p_user_id=get_settings().user_id, match_count=CANDIDATES,
        p_course_id=target["course_id"] if target else None, p_meeting=meeting,
    )
    if len(rows) > 1:
        try:
            texts = [r["title"] + "\n" + r["content"][:RERANK_CHARS] for r in rows]
            rows = fuse_rankings(rows, rerank(query, texts))
        except EmbeddingError as e:
            log.warning("[!] reranker gagal, memakai urutan hybrid: %s", e)
    return {
        "hasil": [{
            "id": r["id"], "matkul": r["course_name"], "pertemuan": r["meetings"], "section": r["section"],
            "judul": r["title"], "lokasi": r["location"], "sumber": r["source_url"],
            "isi": r["content"][:SNIPPET_CHARS],
        } for r in rows[:max(1, min(limit, 8))]],
        "waktu_ms": int((time.time() - started) * 1000),
    }


def get_meeting(course: str, meeting: int, full: bool = False) -> dict:
    target = resolve_course(course)
    if not target:
        return {"error": f"mata kuliah '{course}' tidak ditemukan", "pilihan": [c["matkul"] for c in _catalog()]}
    entry = target["pertemuan"].get(str(meeting))
    if not entry:
        return {"error": f"{target['matkul']} belum punya materi pertemuan {meeting}",
                "pertemuan_tersedia": list(target["pertemuan"])}
    summary = get_summary(target["course_id"], str(meeting)) if USE_MEETING_SUMMARIES and not full else None
    if summary:
        return {"matkul": target["matkul"], "pertemuan": meeting, "judul_section": entry["judul_section"],
                "ringkasan": summary["ringkasan"], "topik": summary["topik"],
                "ada_contoh_kode": summary["ada_contoh_kode"],
                "catatan": "Ini ringkasan. Untuk penjelasan rinci, contoh, atau kode: get_meeting full=true."}
    text = (CORPUS_DIR / entry["file"]).read_text(encoding="utf-8")
    return {"matkul": target["matkul"], "pertemuan": meeting, "judul_section": entry["judul_section"],
            "terpotong": len(text) > MAX_MEETING_CHARS, "isi": text[:MAX_MEETING_CHARS]}


def list_assignments(only_pending: bool = False) -> dict:
    data = read_json(ASSIGNMENTS_FILE)
    tasks = [t for t in data.get("tugas", []) if not (only_pending and t["sudah_dikumpulkan"])]
    return {"diperbarui": data.get("diperbarui"), "tugas": [
        {"matkul": t["matkul"], "jenis": t["jenis"], "judul": t["judul"], "pertemuan": t["pertemuan"],
         "deadline": t["deadline"], "status": t["status_ringkas"], "url": t["url"],
         "soal": (t.get("deskripsi") or "")[:600]} for t in tasks]}


def presence_window(meeting: dict, now: datetime) -> str:
    """Status jendela presensi saat ini; model sering salah menyimpulkan dari jam mentah."""
    if meeting["status"]:
        return "sudah diisi"
    start, end = meeting["mulai"], meeting["selesai"]
    if meeting["dibuka"] and not end:
        return "sedang dibuka"
    if not (start and end):
        return "belum dijadwalkan"
    if now < datetime.fromisoformat(start):
        return "belum dibuka"
    return "sedang dibuka" if now <= datetime.fromisoformat(end) else "sudah tutup, tidak bisa diisi lagi"


def get_attendance(course: str | None = None, date: str | None = None) -> dict:
    """Presensi per pertemuan pada satu tanggal (default hari ini) dan rekap kehadiran."""
    data = read_json(ATTENDANCE_FILE)
    if not data:
        return {"error": "data presensi belum ada (jalankan python -m edupad attendance)"}
    target = resolve_course(course) if course else None
    if course and not target:
        return {"error": f"mata kuliah '{course}' tidak ditemukan", "pilihan": [c["matkul"] for c in _catalog()]}
    now = datetime.now(WIB)
    day = date or now.date().isoformat()
    meetings, recap = [], []
    for c in data.get("mata_kuliah", []):
        if target and c["moodle_course_id"] != target["course_id"]:
            continue
        past = [m for m in c["pertemuan"] if m["mulai"] and m["mulai"][:10] <= day]
        recap.append({"matkul": c["matkul"], "kelas": c["kelas"], "hadir": sum(m["status"] == "hadir" for m in past),
                      "pertemuan_sampai_tanggal": len(past)})
        meetings += [{"matkul": c["matkul"], "kelas": c["kelas"], "pertemuan": m["nama"], "topik": m["topik"],
                      "mulai": m["mulai"][11:16], "selesai": (m["selesai"] or "")[11:16],
                      "status": m["status"] or "belum diisi", "jendela_presensi": presence_window(m, now),
                      "cara": m["cara"]}
                     for m in c["pertemuan"] if (m["mulai"] or "")[:10] == day]
    updated = data.get("diperbarui")
    result = {"diperbarui": updated, "tanggal": day, "pertemuan_pada_tanggal": meetings, "rekap": recap}
    if updated and now - datetime.fromisoformat(updated) > STALE_AFTER:
        result["peringatan"] = "data presensi lebih dari 3 jam lalu; status terbaru mungkin berbeda"
    return result


TOOLS: dict[str, Callable[..., dict]] = {
    "search_materials": search_materials,
    "get_meeting": get_meeting,
    "list_assignments": list_assignments,
    "get_attendance": get_attendance,
}

# Tool penutup: memaksa jawaban akhir terstruktur untuk suara, LCD, dan detail.
ANSWER_TOOL = "answer"


def answer_schema(with_detail: bool) -> dict:
    """Tanpa detail, model tidak menulis jawaban Markdown panjang (token output paling mahal)."""
    schema = json.loads(json.dumps(_ANSWER_SCHEMA))
    if not with_detail:
        params = schema["function"]["parameters"]
        del params["properties"]["detail"]
        params["required"].remove("detail")
    return schema

SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_materials",
        "description": "Cari potongan materi kuliah yang relevan (pencarian semantik + kata kunci). "
                       "Pakai untuk pertanyaan konsep/topik, atau bila nomor pertemuan tidak disebut.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "topik/pertanyaan dalam kalimat lengkap"},
            "course": {"type": "string", "description": "nama, singkatan, atau kode mata kuliah (opsional)"},
            "meeting": {"type": "integer", "description": "nomor pertemuan (opsional)"},
            "limit": {"type": "integer", "description": "jumlah hasil, default 4"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "get_meeting",
        "description": "Materi satu pertemuan. Pakai bila pengguna menyebut mata kuliah dan nomor pertemuan, "
                       "mis. 'materi pertemuan 5 Pemrograman Visual'. Default: ringkasan + daftar topik.",
        "parameters": {"type": "object", "properties": {
            "course": {"type": "string", "description": "nama, singkatan, atau kode mata kuliah"},
            "meeting": {"type": "integer", "description": "nomor pertemuan"},
            "full": {"type": "boolean", "description": "true = seluruh isi materi, untuk penjelasan rinci, "
                                                       "contoh, atau kode"}},
            "required": ["course", "meeting"]}}},
    {"type": "function", "function": {
        "name": "get_attendance",
        "description": "Presensi kuliah dari portal SATU: status tiap pertemuan pada satu tanggal "
                       "(default hari ini) dan rekap jumlah hadir per mata kuliah.",
        "parameters": {"type": "object", "properties": {
            "course": {"type": "string", "description": "nama/singkatan mata kuliah (opsional)"},
            "date": {"type": "string", "description": "tanggal YYYY-MM-DD (opsional, default hari ini)"}}}}},
    {"type": "function", "function": {
        "name": "list_assignments",
        "description": "Daftar tugas & kuis: deadline, status pengumpulan, dan ringkasan soal.",
        "parameters": {"type": "object", "properties": {
            "only_pending": {"type": "boolean", "description": "true = hanya yang belum dikumpulkan"}}}}},
]

_ANSWER_SCHEMA = {"type": "function", "function": {
        "name": ANSWER_TOOL,
        "description": "WAJIB dipanggil sekali untuk memberikan jawaban akhir ke pengguna.",
        "parameters": {"type": "object", "properties": {
            "speech": {"type": "string", "description":
                       "Dibacakan TTS. 2-4 kalimat lisan (maks ~60 kata), tanpa Markdown/simbol/kode/URL. "
                       "Tulis angka & waktu seperti diucapkan. Boleh akhiri dengan tawaran singkat."},
            "screen_title": {"type": "string", "description": "Judul LCD, maks 24 karakter"},
            "screen_lines": {"type": "array", "items": {"type": "string"}, "description":
                             "Poin kunci untuk LCD: 3-6 poin, tiap poin maks 36 karakter, tanpa Markdown/emoji"},
            "detail": {"type": "string", "description":
                       "Jawaban lengkap Markdown untuk dashboard/Telegram: penjelasan, tabel, kode, sumber"}},
            "required": ["speech", "screen_title", "screen_lines", "detail"]}}}
