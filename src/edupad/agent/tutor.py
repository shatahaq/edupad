"""Tutor belajar (SORA): kuis lisan dari materi asli, penguasaan per topik, dan pengulangan
berjarak. Dipakai lewat suara di perangkat dan ditampilkan di dashboard (Tutor & Equity Radar).

Alur kuis di perangkat (satu tekan tombol = satu giliran):
  "uji aku Basis Data pertemuan 5" -> start_quiz: soal dibuat dari materi pertemuan itu
  jawaban lisan -> agent menilai dengan kunci (konteks kuis aktif, lihat context_note) ->
  answer_quiz menyimpan nilai & memberi soal berikutnya -> ... -> penguasaan topik diperbarui
  dan topik dijadwalkan diulang (1/3/7/14/30 hari).

Data di Supabase: `tutor_quizzes`, `learning_checks`, `topic_mastery`
(supabase/migrations/20261017_finance_tutor.sql).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta

from edupad.config import WIB, get_settings
from edupad.core.supabase import SupabaseClient, SupabaseError

log = logging.getLogger(__name__)

QUIZZES = "tutor_quizzes"
CHECKS = "learning_checks"
MASTERY = "topic_mastery"
DEFAULT_QUESTIONS = 3
MAX_QUESTIONS = 5
QUIZ_SOURCE_CHARS = 9_000
QUIZ_EXPIRES = timedelta(hours=3)  # kuis yang ditinggal selama ini dianggap selesai
CACHE_SECONDS = 15 * 60
SCORES = {"benar": 1.0, "sebagian": 0.5, "salah": 0.0}
WEAK_BELOW = 0.6
MASTERED_FROM = 0.8
INTERVALS = (1, 3, 7, 14, 30)  # hari; naik satu tingkat tiap kuis dengan skor >= 0.8

# Aturan tambahan di system prompt agent (statis agar tetap ter-cache).
TUTOR_RULES = """

Tutor belajar (SORA):
- Mahasiswa bilang belum paham/bingung: jelaskan satu konsep dengan bahasa lebih sederhana dan
  analogi sehari-hari, lalu akhiri dengan SATU pertanyaan cek singkat. Bila jawabannya keliru,
  jelaskan lagi dengan tingkat yang lebih dasar.
- Soal TUGAS yang sedang dikerjakan (list_assignments/Classroom): mulai dengan konsep kunci dan
  petunjuk langkah pertama, lalu tawarkan "mau coba dulu atau dijelaskan lengkap?". Bila
  mahasiswa minta penjelasan lengkap atau sudah mencoba, beri penjelasan langkah demi langkah.
- Minta diuji/kuis/latihan soal -> start_quiz (sebut mata kuliah + pertemuan atau topik; tanpa
  itu, start_quiz memilih topik yang jatuh tempo diulang). Bacakan soal persis dari hasil tool.
- "Hari ini belajar apa", "progres belajarku", "apa yang perlu diulang" -> study_plan.
- Keuangan: transaksi yang jelas jenis & nominalnya -> record_transaction langsung, lalu ulangi
  nominal & kategori di jawaban. Nominal ambigu ("dua lima") -> tanya balik, jangan menebak.
  "Hapus yang tadi"/salah catat -> undo_last_transaction."""

QUIZ_PROMPT = """Kamu tutor EduPad untuk mahasiswa D3 Teknik Informatika. Buat {count} pertanyaan kuis
LISAN dari materi di bawah.
Aturan:
- Pertanyaan pendek (maks 25 kata), bisa dijawab lisan dalam 1-2 kalimat.
- Tanpa kode, simbol, rumus panjang, atau pilihan ganda.
- Uji pemahaman konsep (apa, mengapa, bagaimana, bedanya), bukan hafalan angka/tahun.
- Urut dari mudah ke sulit, hanya dari isi materi ini.
- kunci: jawaban ideal singkat (maks 40 kata) berisi poin yang wajib ada.
- konsep: nama konsep yang diuji (maks 5 kata).
Balas JSON: {{"judul": "topik singkat", "soal": [{{"pertanyaan": "...", "kunci": "...", "konsep": "..."}}]}}

Mata kuliah: {course}, pertemuan {meeting}
Materi:
{text}"""


class TutorUnavailable(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(WIB)


def _parse(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=WIB)


def topic_key(course_id: str | None, course: str, meeting: int | None) -> str:
    return f"{course_id or course.lower()}:{meeting if meeting is not None else '-'}"


def next_interval(previous: int | None, score: float) -> int:
    """Hari sampai diulang: naik tingkat bila dikuasai, ulang besok bila lemah."""
    if score >= MASTERED_FROM:
        higher = [d for d in INTERVALS if d > (previous or 0)]
        return higher[0] if higher else INTERVALS[-1]
    if score >= 0.5:
        return 2
    return 1


class TutorStore:
    def __init__(self, user_id: str | None = None, db: SupabaseClient | None = None):
        self.user_id = user_id or get_settings().user_id
        try:
            self.db = db or SupabaseClient()
        except SupabaseError as e:
            raise TutorUnavailable(str(e)) from e

    def _run(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SupabaseError as e:
            text = str(e)
            if "PGRST205" in text or "42P01" in text or "does not exist" in text:
                raise TutorUnavailable(
                    "tabel tutor belum dibuat (supabase/migrations/20261017_finance_tutor.sql)"
                ) from e
            raise TutorUnavailable(f"Supabase: {text}") from e

    # -------------------------------- kuis ---------------------------------
    def active_quiz(self) -> dict | None:
        rows = self._run(
            self.db.select,
            QUIZZES,
            "id,course,course_id,meeting,title,questions,current,status,created_at,updated_at",
            user_id=f"eq.{self.user_id}",
            status="eq.active",
            order="created_at.desc",
            limit="1",
        )
        if not rows:
            return None
        quiz = rows[0]
        updated = _parse(quiz.get("updated_at") or quiz.get("created_at"))
        if updated and _now() - updated > QUIZ_EXPIRES:
            self.close_quiz(quiz["id"], "stopped")
            return None
        return quiz

    def create_quiz(
        self,
        course: str,
        course_id: str | None,
        meeting: int | None,
        title: str,
        questions: list[dict],
    ) -> dict:
        now = _now().isoformat()
        for row in self._run(
            self.db.select, QUIZZES, "id", user_id=f"eq.{self.user_id}", status="eq.active"
        ):
            self.close_quiz(row["id"], "stopped")
        return self._run(
            self.db.insert,
            QUIZZES,
            [
                {
                    "user_id": self.user_id,
                    "course": course,
                    "course_id": course_id,
                    "meeting": meeting,
                    "title": title,
                    "questions": questions,
                    "current": 0,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        )[0]

    def advance(self, quiz_id: str, current: int) -> None:
        self._run(
            self.db.update,
            QUIZZES,
            {"current": current, "updated_at": _now().isoformat()},
            id=f"eq.{quiz_id}",
        )

    def close_quiz(self, quiz_id: str, status: str) -> None:
        self._run(
            self.db.update,
            QUIZZES,
            {"status": status, "updated_at": _now().isoformat()},
            id=f"eq.{quiz_id}",
        )

    def add_check(self, row: dict) -> None:
        self._run(self.db.insert, CHECKS, [{"user_id": self.user_id, **row}])

    def checks(self, quiz_id: str | None = None, since: datetime | None = None) -> list[dict]:
        filters = {"user_id": f"eq.{self.user_id}", "order": "created_at.desc", "limit": "2000"}
        if quiz_id:
            filters["quiz_id"] = f"eq.{quiz_id}"
        rows = self._run(
            self.db.select,
            CHECKS,
            "quiz_id,topic_key,course,meeting,question,expected,answer,verdict,score,"
            "feedback,misconception,created_at",
            **filters,
        )
        if since:
            rows = [r for r in rows if (_parse(r.get("created_at")) or _now()) >= since]
        return rows

    # ----------------------------- penguasaan ------------------------------
    def mastery(self) -> list[dict]:
        return self._run(
            self.db.select,
            MASTERY,
            "topic_key,course,course_id,meeting,title,mastery,attempts,last_score,"
            "last_checked_at,next_review_at,interval_days",
            user_id=f"eq.{self.user_id}",
        )

    def update_mastery(self, quiz: dict, score: float) -> dict:
        key = topic_key(quiz.get("course_id"), quiz["course"], quiz.get("meeting"))
        old = next((m for m in self.mastery() if m["topic_key"] == key), None)
        previous = float(old["mastery"]) if old and old.get("mastery") is not None else None
        level = score if previous is None else 0.6 * score + 0.4 * previous
        interval = next_interval(old.get("interval_days") if old else None, score)
        now = _now()
        row = {
            "user_id": self.user_id,
            "topic_key": key,
            "course": quiz["course"],
            "course_id": quiz.get("course_id"),
            "meeting": quiz.get("meeting"),
            "title": quiz.get("title") or "",
            "mastery": round(level, 2),
            "attempts": (int(old["attempts"]) if old else 0) + 1,
            "last_score": round(score, 2),
            "last_checked_at": now.isoformat(),
            "next_review_at": (now + timedelta(days=interval)).isoformat(),
            "interval_days": interval,
        }
        self._run(self.db.upsert, MASTERY, [row], on_conflict="user_id,topic_key")
        return row


# ------------------------- cache kuis aktif (server) ------------------------
# Server memuat kuis aktif bersamaan dengan memory (server.Agent.prepare) agar ask() tidak
# menambah panggilan Supabase saat perangkat menunggu jawaban.
_cache: dict[str, tuple[float, dict | None]] = {}
_cache_lock = threading.Lock()


def _remember_quiz(user_id: str, quiz: dict | None) -> None:
    with _cache_lock:
        _cache[user_id] = (time.monotonic(), quiz)


def prefetch(user_id: str | None = None) -> dict | None:
    """Muat ulang kuis aktif dari Supabase (dipanggil paralel dengan rekaman perangkat)."""
    user_id = user_id or get_settings().user_id
    try:
        quiz = TutorStore(user_id).active_quiz()
    except TutorUnavailable as e:
        log.debug("[tutor] kuis aktif tidak bisa dimuat: %s", e)
        quiz = None
    _remember_quiz(user_id, quiz)
    return quiz


def cached_quiz(user_id: str | None = None) -> dict | None:
    user_id = user_id or get_settings().user_id
    with _cache_lock:
        entry = _cache.get(user_id)
    if entry and time.monotonic() - entry[0] < CACHE_SECONDS:
        return entry[1]
    return prefetch(user_id)


def context_note(user_id: str | None = None) -> str | None:
    """Pesan sistem untuk ask() selama kuis berjalan: soal yang ditunggu & kunci penilaiannya."""
    quiz = cached_quiz(user_id)
    if not quiz:
        return None
    questions = quiz.get("questions") or []
    index = int(quiz.get("current") or 0)
    if index >= len(questions):
        return None
    q = questions[index]
    where = f"{quiz['course']}" + (
        f" pertemuan {quiz['meeting']}" if quiz.get("meeting") is not None else ""
    )
    return (
        f"KUIS AKTIF: {where} ({quiz.get('title') or '-'}), soal {index + 1}/{len(questions)}.\n"
        f'Soal yang sedang ditunggu jawabannya: "{q["pertanyaan"]}"\n'
        f'Kunci penilaian (rahasia sampai mahasiswa menjawab): "{q["kunci"]}"\n'
        "- Bila pesan mahasiswa adalah jawaban soal ini: nilai benar/sebagian/salah berdasarkan "
        "kunci (maknanya, bukan kata per kata), lalu panggil answer_quiz. Di jawaban akhir: "
        "umpan balik singkat + soal berikutnya dari hasil tool (atau hasil akhir).\n"
        '- "Tidak tahu"/"lewati" = salah; jelaskan kuncinya singkat.\n'
        "- Minta berhenti -> stop_quiz. Pertanyaan lain -> jawab seperti biasa dan ingatkan "
        "kuis masih menunggu jawaban."
    )


# --------------------------------- tools -----------------------------------
def _quiz_source(course: str | None, meeting: int | None, topic: str | None) -> dict:
    """Materi asli untuk soal: satu pertemuan, atau hasil pencarian topik."""
    from edupad.agent import tools

    if course and meeting is not None:
        target = tools.resolve_course(course)
        full = tools.get_meeting(course, meeting, full=True)
        if "error" in full:
            return full
        summary = tools.get_meeting(course, meeting)
        intro = "" if "isi" in summary else f"Ringkasan: {summary.get('ringkasan', '')}\n\n"
        return {
            "course": full["matkul"],
            "course_id": target["course_id"] if target else None,
            "meeting": meeting,
            "title": full.get("judul_section") or "",
            "text": (intro + full["isi"])[:QUIZ_SOURCE_CHARS],
        }
    if topic:
        found = tools.search_materials(topic, course=course, limit=4)
        rows = found.get("hasil") or []
        if not rows:
            return {"error": found.get("error") or f"materi tentang '{topic}' tidak ditemukan"}
        top = rows[0]
        target = tools.resolve_course(top["matkul"])
        meetings = top["pertemuan"] if isinstance(top["pertemuan"], list) else [top["pertemuan"]]
        return {
            "course": top["matkul"],
            "course_id": target["course_id"] if target else None,
            "meeting": meetings[0] if meetings else None,
            "title": topic,
            "text": "\n\n".join(r.get("isi") or "" for r in rows)[:QUIZ_SOURCE_CHARS],
        }
    return {"error": "sebutkan mata kuliah dan pertemuan, atau topik yang ingin diuji"}


def _due_topic(store: TutorStore) -> dict | None:
    now = _now()
    due = [
        m
        for m in store.mastery()
        if m.get("meeting") is not None and (_parse(m.get("next_review_at")) or now) <= now
    ]
    due.sort(key=lambda m: float(m.get("mastery") or 0))
    return due[0] if due else None


def _generate(source: dict, count: int) -> tuple[str, list[dict]]:
    from edupad.agent.assistant import LLMError, _complete_json

    prompt = QUIZ_PROMPT.format(
        count=count,
        course=source["course"],
        meeting=source.get("meeting") if source.get("meeting") is not None else "-",
        text=source["text"],
    )
    try:
        data = json.loads(_complete_json(prompt))
    except (LLMError, ValueError, KeyError) as e:
        raise TutorUnavailable(f"soal kuis gagal dibuat: {e}") from e
    questions = [
        {
            "pertanyaan": " ".join(str(q.get("pertanyaan") or "").split()),
            "kunci": " ".join(str(q.get("kunci") or "").split()),
            "konsep": " ".join(str(q.get("konsep") or "").split()),
        }
        for q in data.get("soal") or []
        if q.get("pertanyaan") and q.get("kunci")
    ][:count]
    if not questions:
        raise TutorUnavailable("soal kuis gagal dibuat dari materi ini")
    return str(data.get("judul") or source.get("title") or "").strip(), questions


def start_quiz(
    course: str | None = None,
    meeting: int | None = None,
    topic: str | None = None,
    count: int = DEFAULT_QUESTIONS,
) -> dict:
    try:
        store = TutorStore()
        if not course and not topic:
            due = _due_topic(store)
            if not due:
                return {
                    "error": "belum ada topik yang jatuh tempo diulang; sebutkan mata kuliah dan "
                    "pertemuan atau topik"
                }
            course, meeting = due["course"], due["meeting"]
        source = _quiz_source(course, meeting, topic)
        if "error" in source:
            return source
        count = max(1, min(int(count or DEFAULT_QUESTIONS), MAX_QUESTIONS))
        title, questions = _generate(source, count)
        quiz = store.create_quiz(
            source["course"], source.get("course_id"), source.get("meeting"), title, questions
        )
        _remember_quiz(store.user_id, quiz)
        return {
            "kuis_dimulai": True,
            "matkul": source["course"],
            "pertemuan": source.get("meeting"),
            "judul": title,
            "jumlah_soal": len(questions),
            "soal_ke": 1,
            "pertanyaan": questions[0]["pertanyaan"],
            "petunjuk": "Sebut topik & jumlah soal singkat, lalu bacakan pertanyaan 1 persis. "
            "Jangan sebut kuncinya.",
        }
    except TutorUnavailable as e:
        return {"error": str(e)}


def _finish(store: TutorStore, quiz: dict, status: str) -> dict:
    checks = store.checks(quiz_id=quiz["id"])
    store.close_quiz(quiz["id"], status)
    _remember_quiz(store.user_id, None)
    if not checks:
        return {"selesai": True, "dinilai": 0}
    score = sum(float(c["score"]) for c in checks) / len(checks)
    concepts = {q["pertanyaan"]: q.get("konsep") for q in quiz.get("questions") or []}
    mastery = store.update_mastery(quiz, score)
    return {
        "selesai": True,
        "dinilai": len(checks),
        "benar": sum(c["verdict"] == "benar" for c in checks),
        "sebagian": sum(c["verdict"] == "sebagian" for c in checks),
        "skor_persen": round(score * 100),
        "penguasaan_topik_persen": round(float(mastery["mastery"]) * 100),
        "diulang_lagi_dalam_hari": mastery["interval_days"],
        "perlu_diperkuat": [
            concepts.get(c["question"]) or c["question"] for c in checks if c["verdict"] != "benar"
        ][:3],
    }


def answer_quiz(
    answer: str, verdict: str, feedback: str = "", misconception: str | None = None
) -> dict:
    """Simpan penilaian jawaban soal yang sedang berjalan, lalu kembalikan soal berikutnya."""
    verdict = (verdict or "").strip().lower()
    if verdict not in SCORES:
        return {"error": "verdict harus benar, sebagian, atau salah"}
    try:
        store = TutorStore()
        quiz = store.active_quiz()
        if not quiz:
            _remember_quiz(store.user_id, None)
            return {"error": "tidak ada kuis yang sedang berjalan"}
        questions = quiz.get("questions") or []
        index = int(quiz.get("current") or 0)
        if index >= len(questions):
            return _finish(store, quiz, "done")
        q = questions[index]
        store.add_check(
            {
                "quiz_id": quiz["id"],
                "topic_key": topic_key(quiz.get("course_id"), quiz["course"], quiz.get("meeting")),
                "course": quiz["course"],
                "course_id": quiz.get("course_id"),
                "meeting": quiz.get("meeting"),
                "question": q["pertanyaan"],
                "expected": q["kunci"],
                "answer": " ".join(str(answer or "").split())[:1000],
                "verdict": verdict,
                "score": SCORES[verdict],
                "feedback": " ".join(str(feedback or "").split())[:600],
                "misconception": (" ".join(str(misconception).split())[:200] or None)
                if misconception
                else None,
            }
        )
        result: dict = {"soal_ke": index + 1, "jumlah_soal": len(questions), "penilaian": verdict}
        if index + 1 < len(questions):
            store.advance(quiz["id"], index + 1)
            _remember_quiz(store.user_id, {**quiz, "current": index + 1})
            result["berikutnya"] = {
                "soal_ke": index + 2,
                "pertanyaan": questions[index + 1]["pertanyaan"],
            }
        else:
            result["hasil_akhir"] = _finish(store, quiz, "done")
        return result
    except TutorUnavailable as e:
        return {"error": str(e)}


def stop_quiz() -> dict:
    try:
        store = TutorStore()
        quiz = store.active_quiz()
        if not quiz:
            _remember_quiz(store.user_id, None)
            return {"error": "tidak ada kuis yang sedang berjalan"}
        return {"dihentikan": True, **_finish(store, quiz, "stopped")}
    except TutorUnavailable as e:
        return {"error": str(e)}


def study_plan() -> dict:
    """Rencana belajar hari ini: kuliah berikutnya, topik jatuh tempo, deadline, peringatan."""
    from edupad.agent import radar

    return radar.study_plan()


TOOLS = {
    "start_quiz": start_quiz,
    "answer_quiz": answer_quiz,
    "stop_quiz": stop_quiz,
    "study_plan": study_plan,
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "start_quiz",
            "description": "Mulai kuis lisan dari materi asli untuk cek pemahaman ('uji aku', 'kuis "
            "dong', 'latihan soal'). Tanpa course & topic: topik yang jatuh tempo diulang.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course": {"type": "string", "description": "mata kuliah (opsional)"},
                    "meeting": {"type": "integer", "description": "nomor pertemuan (opsional)"},
                    "topic": {"type": "string", "description": "topik/konsep (opsional)"},
                    "count": {"type": "integer", "description": "jumlah soal 1-5, default 3"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_quiz",
            "description": "Simpan penilaianmu atas jawaban mahasiswa untuk soal kuis yang sedang "
            "berjalan (lihat KUIS AKTIF); hasilnya soal berikutnya atau hasil akhir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "jawaban mahasiswa"},
                    "verdict": {"type": "string", "enum": ["benar", "sebagian", "salah"]},
                    "feedback": {"type": "string", "description": "umpan balik singkat"},
                    "misconception": {
                        "type": "string",
                        "description": "salah paham yang terlihat, maks 10 kata (opsional)",
                    },
                },
                "required": ["answer", "verdict", "feedback"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_quiz",
            "description": "Hentikan kuis yang sedang berjalan; jawaban yang sudah dinilai tetap dihitung.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "study_plan",
            "description": "Rencana & progres belajar: kuliah berikutnya + topiknya, topik yang perlu "
            "diulang, topik lemah, deadline dekat, dan peringatan dini (kehadiran, anggaran).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
