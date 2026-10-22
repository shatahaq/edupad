"""Tools yang bisa dipanggil LLM: pencarian vektor, materi per pertemuan, tugas, presensi,
dan Google Classroom (bila pengguna menautkan akun Google di web EduPad).
Semuanya hanya membaca, kecuali fill_attendance yang mengisi presensi di portal SATU; itu
dipanggil hanya bila mahasiswa memintanya sendiri (aturannya di SYSTEM_PROMPT).
Fungsi tool keuangan (agent/finance.py) dan tutor (agent/tutor.py) ikut di TOOLS; schemanya
ditambahkan di assistant.ask()."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from edupad.agent import coach, finance, tutor
from edupad.collectors import attendance as attendance_portal
from edupad.config import (
    ASSIGNMENTS_DIR,
    CLASSROOM_DIR,
    CORPUS_DIR,
    SCHEDULE_DIR,
    WIB,
    get_settings,
)
from edupad.core.files import read_json
from edupad.core.supabase import SupabaseClient
from edupad.errors import EXIT_LOGIN_REQUIRED, EXIT_OK
from edupad.processing.embeddings import EmbeddingError, embed_query, rerank
from edupad.processing.summaries import get_summary
from edupad.voice import lang
from edupad.voice import mode as voice_mode

log = logging.getLogger(__name__)

CATALOG_FILE = CORPUS_DIR / "catalog.json"
ASSIGNMENTS_FILE = ASSIGNMENTS_DIR / "assignments.json"
ATTENDANCE_FILE = SCHEDULE_DIR / "attendance.json"
STALE_AFTER = timedelta(hours=3)  # cron presensi berjalan tiap 2 menit di jam kuliah
CLASSROOM_SOURCE = "Google Classroom"
# Status pengumpulan hanya sesegar cron yang mengambilnya: tugas kelas.usu tiap 15 menit,
# Classroom tiap 2 jam. Ambangnya diberi kelonggaran beberapa putaran supaya satu-dua kegagalan
# jaringan tidak langsung dianggap mati. Lewat ini, "belum dikumpulkan" tidak bisa dipercaya.
TASKS_STALE_AFTER = {None: timedelta(hours=1), CLASSROOM_SOURCE: timedelta(hours=3)}
MAX_MEETING_CHARS = 40_000
SNIPPET_CHARS = 1_800
CLASSROOM_SNIPPET_CHARS = 500
MAX_CLASSROOM_RESULTS = 20
# Kelas Classroom sering tidak diarsipkan guru, jadi tugas bertahun-tahun ikut "aktif".
# Agent hanya menerima yang relevan agar hasil tool tetap kecil (hemat token):
CLASSROOM_OVERDUE_WINDOW = timedelta(days=30)  # lewat deadline paling lama ini
CLASSROOM_UNDATED_WINDOW = timedelta(days=60)  # tanpa deadline, dibuat paling lama ini
CLASSROOM_ACTIVE_WINDOW = timedelta(days=180)  # kelas yang dicantumkan di system prompt
MAX_CLASSROOM_TASKS = 25
CLASSROOM_TASK_CHARS = 300
CANDIDATES = 20
RERANK_CHARS = 1_500
# Fusi peringkat hybrid (vektor+kata kunci) dan reranker; diuji pada evals/agent_cases.json:
# benar di peringkat 1 14/17 (hybrid 13, reranker 12), 4 teratas 17/17 (hybrid 16).
FUSION_K = 30
RERANK_WEIGHT = 2.0
USE_MEETING_SUMMARIES = True  # dimatikan evaluasi untuk membandingkan
STOPWORDS = {
    "apa",
    "yang",
    "dan",
    "di",
    "ke",
    "dari",
    "untuk",
    "dengan",
    "pada",
    "itu",
    "ini",
    "materi",
    "tentang",
    "jelaskan",
    "bagaimana",
    "cara",
    "adalah",
    "dalam",
    "the",
    "of",
}


def _catalog() -> list[dict]:
    return read_json(CATALOG_FILE).get("mata_kuliah", [])


def _classroom() -> list[dict]:
    """Data Google Classroom milik pengguna agent: satu entri per akun Google yang ditautkan
    ke user_id ini (hasil `python -m edupad classroom`)."""
    user_id = get_settings().user_id
    return [
        data
        for data in (read_json(path) for path in sorted(CLASSROOM_DIR.glob("*.json")))
        if data.get("user_id") == user_id
    ]


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
    matches = [
        c for c in courses if query in c["matkul"].lower() or any(query in a for a in c["alias"])
    ]
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
        lines.append(
            f"- {c['matkul']} ({c['kode']}{', ' + short.upper() if short else ''}); "
            f"dosen {', '.join(c['dosen']) or '-'}; jadwal {c['jadwal'] or '-'}; "
            f"materi pertemuan: {meetings}"
        )
    classes, old = _active_classroom_classes(datetime.now(WIB))
    for k in classes:
        section = f" ({k['bagian']})" if k.get("bagian") else ""
        lines.append(f"- {k['nama']}{section} (Google Classroom)")
    if classes or old:
        note = f"; {old} kelas lama tidak dicantumkan" if old else ""
        lines.append(
            "Kelas Google Classroom: tugas lewat list_assignments, materi & pengumuman lewat "
            f"get_classroom_materials{note}."
        )
    return "\n".join(lines)


def _active_classroom_classes(now: datetime) -> tuple[list[dict], int]:
    """Kelas Classroom dengan aktivitas (tugas/materi) dalam CLASSROOM_ACTIVE_WINDOW, dan
    jumlah kelas lama lainnya."""
    classes, old = [], 0
    for data in _classroom():
        latest: dict[str, str] = {}
        for item in data.get("tugas", []) + data.get("materi", []):
            stamp = item.get("diperbarui") or item.get("dibuat") or ""
            latest[item["course_id"]] = max(latest.get(item["course_id"], ""), stamp)
        cutoff = (now - CLASSROOM_ACTIVE_WINDOW).isoformat()
        for k in data.get("kelas", []):
            if latest.get(k["course_id"], "") >= cutoff:
                classes.append(k)
            else:
                old += 1
    return classes, old


# ------------------------------- tools ---------------------------------------
def fuse_rankings(rows: list[dict], scores: list[float]) -> list[dict]:
    """Gabungkan urutan hybrid (urutan rows) dengan urutan skor reranker (reciprocal rank fusion)."""
    by_score = sorted(range(len(rows)), key=lambda i: -scores[i])
    rerank_rank = {i: rank for rank, i in enumerate(by_score)}
    order = sorted(
        range(len(rows)),
        key=lambda i: -(1 / (FUSION_K + i) + RERANK_WEIGHT / (FUSION_K + rerank_rank[i])),
    )
    return [rows[i] for i in order]


def search_materials(
    query: str, course: str | None = None, meeting: int | None = None, limit: int = 4
) -> dict:
    target = resolve_course(course)
    if course and not target:
        return {
            "error": f"mata kuliah '{course}' tidak ditemukan",
            "pilihan": [c["matkul"] for c in _catalog()],
        }
    started = time.time()
    rows = SupabaseClient().rpc(
        "match_material_chunks",
        query_embedding=embed_query(query),
        query_text=_keyword_query(query),
        p_user_id=get_settings().user_id,
        match_count=CANDIDATES,
        p_course_id=target["course_id"] if target else None,
        p_meeting=meeting,
    )
    if len(rows) > 1:
        try:
            texts = [r["title"] + "\n" + r["content"][:RERANK_CHARS] for r in rows]
            rows = fuse_rankings(rows, rerank(query, texts))
        except EmbeddingError as e:
            log.warning("[!] reranker gagal, memakai urutan hybrid: %s", e)
    return {
        "hasil": [
            {
                "id": r["id"],
                "matkul": r["course_name"],
                "pertemuan": r["meetings"],
                "section": r["section"],
                "judul": r["title"],
                "lokasi": r["location"],
                "sumber": r["source_url"],
                "isi": r["content"][:SNIPPET_CHARS],
            }
            for r in rows[: max(1, min(limit, 8))]
        ],
        "waktu_ms": int((time.time() - started) * 1000),
    }


def get_meeting(course: str, meeting: int, full: bool = False) -> dict:
    target = resolve_course(course)
    if not target:
        return {
            "error": f"mata kuliah '{course}' tidak ditemukan",
            "pilihan": [c["matkul"] for c in _catalog()],
        }
    entry = target["pertemuan"].get(str(meeting))
    if not entry:
        return {
            "error": f"{target['matkul']} belum punya materi pertemuan {meeting}",
            "pertemuan_tersedia": list(target["pertemuan"]),
        }
    summary = (
        get_summary(target["course_id"], str(meeting))
        if USE_MEETING_SUMMARIES and not full
        else None
    )
    if summary:
        return {
            "matkul": target["matkul"],
            "pertemuan": meeting,
            "judul_section": entry["judul_section"],
            "ringkasan": summary["ringkasan"],
            "topik": summary["topik"],
            "ada_contoh_kode": summary["ada_contoh_kode"],
            "catatan": "Ini ringkasan. Untuk penjelasan rinci, contoh, atau kode: get_meeting full=true.",
        }
    text = (CORPUS_DIR / entry["file"]).read_text(encoding="utf-8")
    return {
        "matkul": target["matkul"],
        "pertemuan": meeting,
        "judul_section": entry["judul_section"],
        "terpotong": len(text) > MAX_MEETING_CHARS,
        "isi": text[:MAX_MEETING_CHARS],
    }


def _task_view(t: dict) -> dict:
    return {
        "matkul": t["matkul"],
        "jenis": t["jenis"],
        "judul": t["judul"],
        "pertemuan": t["pertemuan"],
        "deadline": t["deadline"],
        "status": t["status_ringkas"],
        "url": t["url"],
        "soal": (t.get("deskripsi") or "")[:600],
    }


def stale_task_sources(data: dict, now: datetime | None = None) -> set[str | None]:
    """Sumber tugas pada `data` yang datanya sudah lewat ambang segar, jadi status pengumpulannya
    tidak bisa dipercaya. Hanya sumber yang memang punya tugas di `data` yang dilaporkan."""
    now = now or datetime.now(WIB)
    updated = {None: data.get("diperbarui"), CLASSROOM_SOURCE: data.get("classroom_diperbarui")}
    return {
        source
        for source in {t.get("sumber") for t in data.get("tugas", [])}
        if not updated.get(source)
        or now - datetime.fromisoformat(updated[source])
        > TASKS_STALE_AFTER.get(source, timedelta(hours=1))
    }


def source_label(source: str | None) -> str:
    return source or "kelas.usu"


def list_assignments(only_pending: bool = False) -> dict:
    data = read_json(ASSIGNMENTS_FILE)
    tasks = [t for t in data.get("tugas", []) if not (only_pending and t["sudah_dikumpulkan"])]
    result = {"diperbarui": data.get("diperbarui"), "tugas": [_task_view(t) for t in tasks]}
    classroom = _classroom()
    if classroom:
        candidates = [
            t
            for d in classroom
            for t in d.get("tugas", [])
            if not (only_pending and t["sudah_dikumpulkan"])
        ]
        now = datetime.now(WIB)
        relevant = [t for t in candidates if _relevant_classroom_task(t, now)]
        relevant.sort(key=lambda t: _classroom_task_order(t, now.timestamp()))
        shown = relevant[:MAX_CLASSROOM_TASKS]
        result["tugas"] += [
            {
                **_task_view(t),
                "soal": (t.get("deskripsi") or "")[:CLASSROOM_TASK_CHARS],
                "sumber": "Google Classroom",
            }
            for t in shown
        ]
        result["classroom_diperbarui"] = max(d.get("diperbarui") or "" for d in classroom) or None
        hidden = len(candidates) - len(shown)
        if hidden:
            result["classroom_tidak_ditampilkan"] = (
                f"{hidden} tugas Classroom lama (deadline lewat lebih dari 30 hari, atau tanpa "
                "deadline dan dibuat lebih dari 60 hari lalu) tidak ditampilkan"
            )
    stale = stale_task_sources(result)
    if stale:
        names = ", ".join(sorted(source_label(s) for s in stale))
        result["peringatan"] = (
            f"data tugas {names} sudah lama tidak diperbarui, jadi status pengumpulannya mungkin "
            "sudah berubah; sebut ini bila mahasiswa menanyakan sudah dikumpulkan atau belum"
        )
    return result


def _classroom_task_order(task: dict, now_ts: float) -> tuple[int, float]:
    """Deadline mendatang (terdekat dulu), lalu yang baru lewat (terbaru dulu), lalu tanpa deadline."""
    due = task.get("deadline_ts")
    if not due:
        return (2, 0)
    return (0, due) if due >= now_ts else (1, -due)


def _relevant_classroom_task(task: dict, now: datetime) -> bool:
    if task.get("deadline"):
        return datetime.fromisoformat(task["deadline"]) >= now - CLASSROOM_OVERDUE_WINDOW
    created = task.get("dibuat")
    return bool(created) and datetime.fromisoformat(created) >= now - CLASSROOM_UNDATED_WINDOW


def get_classroom_materials(
    course: str | None = None, query: str | None = None, meeting: int | None = None, limit: int = 8
) -> dict:
    """Materi & pengumuman Google Classroom, terbaru dulu; `query` mengurutkan menurut kata kunci."""
    classroom = _classroom()
    if not classroom:
        return {"error": "belum ada data Google Classroom (login di web EduPad, lalu sinkronkan)"}
    courses = [k for d in classroom for k in d.get("kelas", [])]
    items = [m for d in classroom for m in d.get("materi", [])]
    if course:
        wanted = re.sub(r"\s+", " ", course.lower()).strip()
        ids = {
            k["course_id"]
            for k in courses
            if wanted == k["course_id"] or any(wanted in alias for alias in k.get("alias", []))
        }
        if not ids:
            return {
                "error": f"kelas Classroom '{course}' tidak ditemukan",
                "pilihan": [k["nama"] for k in courses],
            }
        items = [m for m in items if m["course_id"] in ids]
    if meeting is not None:
        items = [m for m in items if m.get("pertemuan") == meeting]
    items.sort(key=lambda m: m.get("dibuat") or "", reverse=True)
    if query:
        words = [
            w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS and len(w) > 1
        ]

        def score(m: dict) -> int:
            text = " ".join(
                [m["judul"], m.get("deskripsi") or "", m.get("topik") or ""]
                + [a.get("judul") or "" for a in m.get("lampiran", [])]
            ).lower()
            return sum(w in text for w in words)

        scored = [(score(m), m) for m in items]
        items = [m for s, m in sorted(scored, key=lambda x: -x[0]) if s > 0] if words else items
    return {
        "jumlah": len(items),
        "hasil": [
            {
                "matkul": m["matkul"],
                "jenis": m["jenis"],
                "judul": m["judul"],
                "topik": m.get("topik"),
                "pertemuan": m.get("pertemuan"),
                "tanggal": m.get("dibuat"),
                "isi": (m.get("deskripsi") or "")[:CLASSROOM_SNIPPET_CHARS],
                "lampiran": [
                    {"jenis": a["jenis"], "judul": a.get("judul"), "url": a.get("url")}
                    for a in m.get("lampiran", [])
                ],
                "url": m.get("url"),
            }
            for m in items[: max(1, min(limit, MAX_CLASSROOM_RESULTS))]
        ],
    }


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
    return (
        "sedang dibuka"
        if now <= datetime.fromisoformat(end)
        else "sudah tutup, tidak bisa diisi lagi"
    )


def get_attendance(course: str | None = None, date: str | None = None) -> dict:
    """Presensi per pertemuan pada satu tanggal (default hari ini) dan rekap kehadiran."""
    data = read_json(ATTENDANCE_FILE)
    if not data:
        return {"error": "data presensi belum ada (jalankan python -m edupad attendance)"}
    target = resolve_course(course) if course else None
    if course and not target:
        return {
            "error": f"mata kuliah '{course}' tidak ditemukan",
            "pilihan": [c["matkul"] for c in _catalog()],
        }
    now = datetime.now(WIB)
    day = date or now.date().isoformat()
    meetings, recap = [], []
    for c in data.get("mata_kuliah", []):
        if target and c["moodle_course_id"] != target["course_id"]:
            continue
        past = [m for m in c["pertemuan"] if m["mulai"] and m["mulai"][:10] <= day]
        recap.append(
            {
                "matkul": c["matkul"],
                "kelas": c["kelas"],
                "hadir": sum(m["status"] == "hadir" for m in past),
                "pertemuan_sampai_tanggal": len(past),
            }
        )
        meetings += [
            {
                "matkul": c["matkul"],
                "kelas": c["kelas"],
                "pertemuan": m["nama"],
                "topik": m["topik"],
                "mulai": m["mulai"][11:16],
                "selesai": (m["selesai"] or "")[11:16],
                "status": m["status"] or "belum diisi",
                "jendela_presensi": presence_window(m, now),
                "cara": m["cara"],
            }
            for m in c["pertemuan"]
            if (m["mulai"] or "")[:10] == day
        ]
    updated = data.get("diperbarui")
    result = {
        "diperbarui": updated,
        "tanggal": day,
        "pertemuan_pada_tanggal": meetings,
        "rekap": recap,
    }
    if updated and now - datetime.fromisoformat(updated) > STALE_AFTER:
        result["peringatan"] = "data presensi lebih dari 3 jam lalu; status terbaru mungkin berbeda"
    return result


def _filled_view(result: dict) -> dict:
    return {k: result[k] for k in ("matkul", "kelas", "pertemuan")}


def fill_attendance() -> dict:
    """Isi presensi yang sedang terbuka di portal SATU, jalur yang sama dengan cron
    `attendance --fill`. Hanya pertemuan bercara "langsung"; yang QR harus dipindai sendiri."""
    code, results = attendance_portal.fill_open()
    if code == EXIT_LOGIN_REQUIRED:
        return {
            "error": "sesi portal SATU sudah habis, presensi tidak bisa diisi sampai mahasiswa "
            "login ulang lewat dashboard EduPad"
        }
    if code != EXIT_OK:
        return {
            "error": "portal SATU tidak bisa dihubungi sekarang; sarankan mencoba lagi sebentar "
            "lagi atau mengisi sendiri di portal"
        }
    if not results:
        return {
            "terisi": [],
            "petunjuk": "Tidak ada presensi yang sedang terbuka, jadi tidak ada yang diisi. "
            "Sampaikan apa adanya.",
        }

    def pick(status: str) -> list[dict]:
        return [_filled_view(r) for r in results if r["status"] == status]

    terisi, harus_qr = pick(attendance_portal.FILLED), pick(attendance_portal.QR_ONLY)
    gagal = [
        _filled_view(r) | {"sebab": r.get("error", "")}
        for r in results
        if r["status"] == attendance_portal.ERROR
    ]
    petunjuk = []
    if terisi:
        petunjuk.append("Yang di 'terisi' sudah dicek ulang ke portal, jadi boleh dipastikan.")
    if harus_qr:
        petunjuk.append("'harus_qr' tidak bisa diisi dari jauh: QR-nya dipindai sendiri di kelas.")
    if gagal:
        petunjuk.append("Untuk 'gagal', sebut sebabnya singkat dan sarankan mengisi di portal.")
    return {"terisi": terisi, "harus_qr": harus_qr, "gagal": gagal, "petunjuk": " ".join(petunjuk)}


TOOLS: dict[str, Callable[..., dict]] = {
    "search_materials": search_materials,
    "get_meeting": get_meeting,
    "list_assignments": list_assignments,
    "get_attendance": get_attendance,
    "fill_attendance": fill_attendance,
    "get_classroom_materials": get_classroom_materials,
    **finance.TOOLS,
    **tutor.TOOLS,
    **coach.TOOLS,
    **voice_mode.TOOLS,
    **lang.TOOLS,
}

# Tool penutup: memaksa jawaban akhir terstruktur untuk suara, LCD, dan detail.
ANSWER_TOOL = "answer"


VOICE_SPEECH_DESCRIPTION = (
    "Dibacakan TTS; Mode Suara: SELURUH isi jawaban (maks ~120 kata) karena pengguna tidak "
    "melihat layar. Daftar dibacakan berurutan, angka & waktu seperti diucapkan, tanpa "
    "Markdown/simbol/kode/URL. Bila masih ada lanjutan, akhiri dengan 'Mau dilanjutkan?'."
)


def answer_schema(with_detail: bool, voice: bool = False) -> dict:
    """Tanpa detail, model tidak menulis jawaban Markdown panjang (token output paling mahal).
    `voice`: Mode Suara, speech memuat seluruh isi (pengguna tidak melihat layar)."""
    schema = json.loads(json.dumps(_ANSWER_SCHEMA))
    if voice:
        schema["function"]["parameters"]["properties"]["speech"]["description"] = (
            VOICE_SPEECH_DESCRIPTION
        )
    if not with_detail:
        params = schema["function"]["parameters"]
        del params["properties"]["detail"]
        params["required"].remove("detail")
    return schema


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_materials",
            "description": "Cari potongan materi kuliah yang relevan (pencarian semantik + kata kunci). "
            "Pakai untuk pertanyaan konsep/topik, atau bila nomor pertemuan tidak disebut.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "topik/pertanyaan dalam kalimat lengkap",
                    },
                    "course": {
                        "type": "string",
                        "description": "nama, singkatan, atau kode mata kuliah (opsional)",
                    },
                    "meeting": {"type": "integer", "description": "nomor pertemuan (opsional)"},
                    "limit": {"type": "integer", "description": "jumlah hasil, default 4"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meeting",
            "description": "Materi satu pertemuan. Pakai bila pengguna menyebut mata kuliah dan nomor pertemuan, "
            "mis. 'materi pertemuan 5 Pemrograman Visual'. Default: ringkasan + daftar topik.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course": {
                        "type": "string",
                        "description": "nama, singkatan, atau kode mata kuliah",
                    },
                    "meeting": {"type": "integer", "description": "nomor pertemuan"},
                    "full": {
                        "type": "boolean",
                        "description": "true = seluruh isi materi, untuk penjelasan rinci, "
                        "contoh, atau kode",
                    },
                },
                "required": ["course", "meeting"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_attendance",
            "description": "Presensi kuliah dari portal SATU: status tiap pertemuan pada satu tanggal "
            "(default hari ini) dan rekap jumlah hadir per mata kuliah.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course": {
                        "type": "string",
                        "description": "nama/singkatan mata kuliah (opsional)",
                    },
                    "date": {
                        "type": "string",
                        "description": "tanggal YYYY-MM-DD (opsional, default hari ini)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fill_attendance",
            "description": "Isikan presensi yang SEDANG terbuka di portal SATU untuk mahasiswa "
            "ini. Panggil hanya bila mahasiswa memang memintanya ('isikan presensi', 'absenkan "
            "aku'), tidak pernah atas inisiatif sendiri. Pertemuan yang hanya menyediakan QR "
            "tidak bisa diisi dari sini. Untuk sekadar melihat status, pakai get_attendance.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_assignments",
            "description": "Daftar tugas & kuis: deadline, status pengumpulan, dan ringkasan soal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "only_pending": {
                        "type": "boolean",
                        "description": "true = hanya yang belum dikumpulkan",
                    }
                },
            },
        },
    },
]

CLASSROOM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_classroom_materials",
        "description": "Materi dan pengumuman dari Google Classroom (judul, isi, lampiran, tautan), "
        "terbaru dulu. Tugas & deadline Classroom ada di list_assignments.",
        "parameters": {
            "type": "object",
            "properties": {
                "course": {"type": "string", "description": "nama kelas Classroom (opsional)"},
                "query": {"type": "string", "description": "kata kunci topik (opsional)"},
                "meeting": {"type": "integer", "description": "nomor pertemuan (opsional)"},
                "limit": {"type": "integer", "description": "jumlah hasil, default 8"},
            },
        },
    },
}


def tool_schemas() -> list[dict]:
    """Schema tool untuk LLM. Tool Classroom hanya ditawarkan bila pengguna punya datanya,
    agar prompt pengguna tanpa Classroom tidak bertambah panjang."""
    return [*SCHEMAS, CLASSROOM_SCHEMA] if _classroom() else list(SCHEMAS)


_ANSWER_SCHEMA = {
    "type": "function",
    "function": {
        "name": ANSWER_TOOL,
        "description": "WAJIB dipanggil sekali untuk memberikan jawaban akhir ke pengguna.",
        "parameters": {
            "type": "object",
            "properties": {
                "speech": {
                    "type": "string",
                    "description": "Dibacakan TTS. 2-4 kalimat lisan (maks ~60 kata), tanpa Markdown/simbol/kode/URL. "
                    "Tulis angka & waktu seperti diucapkan. Boleh akhiri dengan tawaran singkat.",
                },
                "screen_title": {"type": "string", "description": "Judul LCD, maks 24 karakter"},
                "screen_lines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Poin kunci untuk LCD: 3-6 poin, tiap poin maks 36 karakter, tanpa Markdown/emoji",
                },
                "detail": {
                    "type": "string",
                    "description": "Jawaban lengkap Markdown untuk dashboard/Telegram: penjelasan, tabel, kode, sumber",
                },
            },
            "required": ["speech", "screen_title", "screen_lines", "detail"],
        },
    },
}
