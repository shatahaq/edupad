"""Tutor mandiri: SORA mengenali topik yang sulit bagi mahasiswa, lalu menyiapkan bantuan.

Lingkaran belajar adaptif:
  1. deteksi   sinyal per topik (mata kuliah + pertemuan) dari data yang sudah ada:
               jawaban kuis salah/sebagian & salah paham, penguasaan rendah, pengulangan yang
               terlewat, pertanyaan berulang ke perangkat, dan ucapan "belum paham/bingung".
               Topik baru dianggap perlu bantuan bila ada minimal DUA jenis sinyal.
  2. analisis  `python -m edupad tutor-coach` (cron sore) memilih 1-2 topik, mencatat
               kesulitannya sebagai ingatan agent (agent_memories).
  3. bantuan   pelajaran mini 3 bagian lewat suara yang menyasar salah pahamnya + kuis terarah,
               disimpan di Supabase `tutor_help`; ditawarkan lewat kartu sore di perangkat dan
               saat mahasiswa bicara ke EduPad (lihat context_note).
  4. ukur      skor penguasaan sebelum & sesudah bantuan (dashboard: Tutor Belajar).
Kehadiran sengaja TIDAK dipakai sebagai sinyal.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta

from edupad.agent.tutor import (
    MASTERED_FROM,
    WEAK_BELOW,
    TutorStore,
    TutorUnavailable,
    _now,
    _parse,
    _quiz_source,
    _remember_quiz,
    topic_key,
)
from edupad.config import get_settings

log = logging.getLogger(__name__)

HELPS = "tutor_help"
WINDOW = timedelta(days=21)  # sinyal yang dihitung
REPEAT_TURNS = 3  # pertanyaan ke pertemuan yang sama sebanyak ini, di >= 2 hari berbeda
OVERDUE = timedelta(days=2)  # pengulangan yang terlewat selama ini
COOLDOWN = timedelta(days=7)  # topik yang sudah dibantu tidak disiapkan lagi selama ini
DECLINED_PAUSE = timedelta(days=2)  # "nanti saja": tawarkan lagi setelah ini
READY_EXPIRES = timedelta(days=5)  # bantuan siap yang tak dimulai selama ini dianggap usang
MAX_PER_RUN = 2
LESSON_PARTS = 3
CACHE_SECONDS = 15 * 60
CONFUSION = re.compile(
    r"\b(belum|blm|gak|ga|nggak|enggak|tidak|kurang)\s+(paham|ngerti|mengerti|nangkep)\b"
    r"|\bbingung\b|\bjelas(in|kan)\s+(lagi|ulang)\b|\bulang(i|in)?\s+(lagi|penjelasan)\b",
    re.IGNORECASE,
)
SIGNAL_LABELS = {
    "kuis": "jawaban kuis belum tepat",
    "penguasaan": "penguasaan masih rendah",
    "terlewat": "pengulangan terlewat",
    "berulang": "pertanyaan berulang",
    "bingung": "menyatakan belum paham",
}

HELP_PROMPT = """Kamu SORA, tutor EduPad untuk mahasiswa D3 Teknik Informatika. Mahasiswa kesulitan
pada topik di bawah. Susun bantuan yang dibacakan lewat suara di perangkat kecil.

Tanda kesulitan: {reasons}
Salah paham / jawaban keliru yang tercatat:
{mistakes}

Aturan:
- "masalah": satu kalimat (maks 20 kata) tentang apa yang belum dipahami, tanpa menghakimi.
- "pelajaran": tepat {parts} bagian berurutan. Tiap "ucapan" maks 55 kata, bahasa santai,
  satu gagasan per bagian, pakai analogi sehari-hari, langsung meluruskan salah paham di atas.
  Tanpa Markdown, simbol, kode, atau URL. Bagian terakhir ditutup ajakan mencoba kuis.
  "layar_judul" maks 24 karakter; "layar" 2-4 poin, tiap poin maks 36 karakter.
- "soal": 3 soal kuis lisan yang menguji tepat salah paham itu (maks 25 kata, dijawab 1-2
  kalimat, tanpa pilihan ganda); "kunci" maks 40 kata; "level" dasar/menengah/lanjut.
- Hanya dari materi berikut; jangan mengarang di luar materi.
Balas JSON: {{"judul": "topik singkat", "masalah": "...", "pelajaran": [{{"ucapan": "...",
"layar_judul": "...", "layar": ["..."]}}], "soal": [{{"pertanyaan": "...", "kunci": "...",
"konsep": "...", "level": "dasar"}}]}}

Mata kuliah: {course}, pertemuan {meeting}
Materi:
{text}"""


# --------------------------------- deteksi ----------------------------------
def _turns(store: TutorStore, since: datetime) -> list[dict]:
    try:
        rows = store._run(
            store.db.select,
            "agent_turns",
            "question,sources,created_at",
            user_id=f"eq.{store.user_id}",
            order="created_at.desc",
            limit="600",
        )
    except TutorUnavailable:
        return []
    return [r for r in rows if (_parse(r.get("created_at")) or since) >= since]


def struggles(store: TutorStore, now: datetime | None = None) -> list[dict]:
    """Topik dengan minimal dua jenis sinyal kesulitan, paling mendesak dulu."""
    from edupad.agent.tools import resolve_course

    now = now or _now()
    since = now - WINDOW
    topics: dict[str, dict] = {}

    def topic(key: str, course: str, course_id: str | None, meeting: int | None) -> dict:
        return topics.setdefault(
            key,
            {
                "topic_key": key,
                "course": course,
                "course_id": course_id,
                "meeting": meeting,
                "title": "",
                "signals": defaultdict(int),
                "mistakes": [],
                "mastery": None,
            },
        )

    for c in store.checks(since=since):
        t = topic(c["topic_key"], c["course"], c.get("course_id"), c.get("meeting"))
        if c["verdict"] != "benar":
            t["signals"]["kuis"] += 1
            t["mistakes"].append(
                {
                    "soal": c["question"],
                    "jawaban": c.get("answer") or "",
                    "salah_paham": c.get("misconception"),
                }
            )
    for m in store.mastery():
        t = topic(m["topic_key"], m["course"], m.get("course_id"), m.get("meeting"))
        t["title"] = m.get("title") or t["title"]
        t["mastery"] = float(m["mastery"]) if m.get("mastery") is not None else None
        if t["mastery"] is not None and t["mastery"] < WEAK_BELOW:
            t["signals"]["penguasaan"] += 1
        due = _parse(m.get("next_review_at"))
        if due and now - due > OVERDUE and (t["mastery"] or 0) < MASTERED_FROM:
            t["signals"]["terlewat"] += 1

    repeats: dict[str, list[datetime]] = defaultdict(list)
    for turn in _turns(store, since):
        at = _parse(turn.get("created_at")) or now
        confused = bool(CONFUSION.search(turn.get("question") or ""))
        for source in turn.get("sources") or []:
            course = resolve_course(source.get("course_id") or source.get("matkul"))
            for meeting in source.get("pertemuan") or []:
                if not isinstance(meeting, int) or not course:
                    continue
                key = topic_key(course["course_id"], course["matkul"], meeting)
                t = topic(key, course["matkul"], course["course_id"], meeting)
                t["title"] = t["title"] or source.get("judul") or ""
                repeats[key].append(at)
                if confused:
                    t["signals"]["bingung"] += 1
    for key, times in repeats.items():
        if len(times) >= REPEAT_TURNS and len({x.date() for x in times}) >= 2:
            topics[key]["signals"]["berulang"] += 1

    result = []
    for t in topics.values():
        kinds = {k for k, n in t["signals"].items() if n}
        if len(kinds) < 2 and t["signals"].get("bingung", 0) < 2:
            continue
        if t["meeting"] is None:
            continue  # pelajaran mini butuh materi satu pertemuan
        t["kinds"] = sorted(kinds)
        t["score"] = (
            3 * t["signals"].get("bingung", 0)
            + 2 * t["signals"].get("kuis", 0)
            + 2 * t["signals"].get("penguasaan", 0)
            + t["signals"].get("berulang", 0)
            + t["signals"].get("terlewat", 0)
        )
        t["reasons"] = [_reason(k, t["signals"][k], t) for k in t["kinds"]]
        t["signals"] = dict(t["signals"])
        result.append(t)
    result.sort(key=lambda t: -t["score"])
    return result


def _reason(kind: str, count: int, topic: dict) -> str:
    if kind == "penguasaan" and topic.get("mastery") is not None:
        return f"penguasaan {round(topic['mastery'] * 100)}%"
    if kind == "kuis":
        return f"{count} jawaban kuis belum tepat"
    if kind == "bingung":
        return f"{count}x bilang belum paham"
    return SIGNAL_LABELS[kind]


# --------------------------------- bantuan ----------------------------------
def helps(store: TutorStore, limit: int = 30) -> list[dict]:
    return store._run(
        store.db.select,
        HELPS,
        "*",
        user_id=f"eq.{store.user_id}",
        order="created_at.desc",
        limit=str(limit),
    )


def _update(store: TutorStore, help_id: str, values: dict) -> None:
    store._run(store.db.update, HELPS, values, id=f"eq.{help_id}")


def _blocked(store: TutorStore, now: datetime) -> set[str]:
    """Topik yang sedang/baru dibantu atau baru ditolak."""
    blocked = set()
    for h in helps(store, 60):
        created = _parse(h.get("created_at")) or now
        declined = _parse(h.get("declined_at")) or created
        active = h["status"] in {"siap", "berjalan", "kuis"}
        paused = h["status"] == "ditolak" and now - declined < DECLINED_PAUSE
        recent = h["status"] == "selesai" and now - created < COOLDOWN
        if active or paused or recent:
            blocked.add(h["topic_key"])
    return blocked


def _clean(text: object, limit: int) -> str:
    return " ".join(str(text or "").split())[:limit]


def prepare_help(store: TutorStore, topic: dict) -> dict:
    """Buat pelajaran mini + kuis terarah untuk satu topik, simpan sebagai bantuan "siap"."""
    from edupad.agent.assistant import LLMError, _complete_json

    source = _quiz_source(topic["course"], topic["meeting"], None)
    if "error" in source:
        raise TutorUnavailable(source["error"])
    mistakes = topic.get("mistakes") or []
    lines = [
        f"- soal: {m['soal']} | jawaban: {m['jawaban'] or '-'}"
        + (f" | salah paham: {m['salah_paham']}" if m.get("salah_paham") else "")
        for m in mistakes[:6]
    ] or ["- (belum ada jawaban kuis; mahasiswa bertanya berulang/menyatakan belum paham)"]
    prompt = HELP_PROMPT.format(
        reasons=", ".join(topic.get("reasons") or ["diminta mahasiswa"]),
        mistakes="\n".join(lines),
        parts=LESSON_PARTS,
        course=source["course"],
        meeting=source.get("meeting"),
        text=source["text"],
    )
    try:
        data = json.loads(_complete_json(prompt))
    except (LLMError, ValueError, KeyError) as e:
        raise TutorUnavailable(f"bantuan gagal disiapkan: {e}") from e
    lesson = [
        {
            "ucapan": _clean(p.get("ucapan"), 600),
            "layar_judul": _clean(p.get("layar_judul"), 24) or "SORA",
            "layar": [_clean(x, 40) for x in (p.get("layar") or [])][:4],
        }
        for p in data.get("pelajaran") or []
        if p.get("ucapan")
    ][:LESSON_PARTS]
    questions = [
        {
            "pertanyaan": _clean(q.get("pertanyaan"), 300),
            "kunci": _clean(q.get("kunci"), 400),
            "konsep": _clean(q.get("konsep"), 60),
            "level": q.get("level")
            if q.get("level") in {"dasar", "menengah", "lanjut"}
            else "dasar",
        }
        for q in data.get("soal") or []
        if q.get("pertanyaan") and q.get("kunci")
    ][:3]
    if not lesson or not questions:
        raise TutorUnavailable("bantuan gagal disiapkan dari materi ini")
    row = store._run(
        store.db.insert,
        HELPS,
        [
            {
                "user_id": store.user_id,
                "topic_key": topic["topic_key"],
                "course": source["course"],
                "course_id": source.get("course_id") or topic.get("course_id"),
                "meeting": source.get("meeting"),
                "title": _clean(
                    data.get("judul") or topic.get("title") or source.get("title"), 120
                ),
                "problem": _clean(data.get("masalah"), 200),
                "reasons": topic.get("reasons") or ["diminta mahasiswa"],
                "lesson": lesson,
                "questions": questions,
                "status": "siap",
                "part": 0,
                "mastery_before": topic.get("mastery"),
                "created_at": _now().isoformat(),
            }
        ],
    )[0]
    _remember_difficulty(store, row)
    _remember_help(store.user_id, row)
    return row


def _remember_difficulty(store: TutorStore, row: dict) -> None:
    """Catat kesulitan sebagai ingatan agent, agar SORA menyesuaikan penjelasan di sesi lain."""
    if not row.get("problem"):
        return
    fact = (
        f"Kesulitan {row['title']} ({row['course']} pertemuan {row['meeting']}): {row['problem']}"
    )
    try:
        existing = store._run(
            store.db.select, "agent_memories", "content", user_id=f"eq.{store.user_id}"
        )
        if any(row["title"] and row["title"] in (m.get("content") or "") for m in existing):
            return
        store._run(store.db.insert, "agent_memories", [{"user_id": store.user_id, "content": fact}])
    except TutorUnavailable as e:
        log.warning("[coach] kesulitan tidak tersimpan ke memory: %s", e)


def on_quiz_finished(store: TutorStore, help_id: str, mastery: float) -> None:
    """Kuis terarah selesai: catat penguasaan sesudah bantuan (bukti dampak di dashboard)."""
    try:
        _update(
            store,
            help_id,
            {
                "status": "selesai",
                "mastery_after": round(mastery, 2),
                "finished_at": _now().isoformat(),
            },
        )
    except TutorUnavailable as e:
        log.warning("[coach] hasil bantuan tidak tersimpan: %s", e)
    _remember_help(store.user_id, None)


# ------------------------------ cache (server) ------------------------------
_cache: dict[str, tuple[float, dict | None]] = {}
_cache_lock = threading.Lock()


def _remember_help(user_id: str, row: dict | None) -> None:
    with _cache_lock:
        _cache[user_id] = (time.monotonic(), row)


def current_help(store: TutorStore) -> dict | None:
    """Bantuan yang sedang berjalan, atau yang siap ditawarkan (terbaru)."""
    now = _now()
    for h in helps(store, 10):
        if h["status"] in {"berjalan", "kuis"}:
            return h
    for h in helps(store, 10):
        created = _parse(h.get("created_at")) or now
        if h["status"] == "siap":
            if now - created > READY_EXPIRES:
                _update(store, h["id"], {"status": "kedaluwarsa"})
                continue
            return h
    return None


def prefetch(user_id: str | None = None) -> dict | None:
    user_id = user_id or get_settings().user_id
    try:
        row = current_help(TutorStore(user_id))
    except TutorUnavailable as e:
        log.debug("[coach] bantuan tidak bisa dimuat: %s", e)
        row = None
    _remember_help(user_id, row)
    return row


def cached_help(user_id: str | None = None) -> dict | None:
    user_id = user_id or get_settings().user_id
    with _cache_lock:
        entry = _cache.get(user_id)
    if entry and time.monotonic() - entry[0] < CACHE_SECONDS:
        return entry[1]
    return prefetch(user_id)


def context_note(user_id: str | None = None) -> str | None:
    """Pesan sistem untuk ask(): bantuan yang berjalan atau siap ditawarkan."""
    h = cached_help(user_id)
    if not h:
        return None
    where = f"{h['course']} pertemuan {h['meeting']}"
    if h["status"] == "berjalan":
        return (
            f"SESI BANTUAN SORA BERJALAN: {h['title']} ({where}), bagian {h['part']}/"
            f"{len(h.get('lesson') or [])} sudah dibacakan.\n"
            '- "lanjut"/"oke"/"ya"/"terus" -> continue_help. Pertanyaan tentang penjelasan -> '
            'jawab singkat lalu tawarkan lanjut. "nanti saja"/"berhenti" -> decline_help.'
        )
    if h["status"] != "siap":
        return None
    return (
        f"BANTUAN SIAP DARI SORA: {h['title']} ({where}). Alasan: {', '.join(h.get('reasons') or [])}."
        f" Masalah: {h.get('problem') or '-'}\n"
        "- Tawarkan SEKALI di sesi ini bila percakapan menyentuh topik ini atau mahasiswa tampak "
        'kesulitan: "SORA sudah siapkan pelajaran singkat tentang ..., mau mulai sekarang?" '
        "(jangan ulangi bila sudah ditawarkan di riwayat).\n"
        '- "mulai"/"ayo"/"mau"/"uji aku lagi" -> start_help. "nanti saja" -> decline_help.'
    )


# --------------------------------- tools ------------------------------------
def _part(h: dict, index: int) -> dict:
    lesson = h.get("lesson") or []
    part = lesson[index - 1]
    return {
        "bagian": index,
        "jumlah_bagian": len(lesson),
        "judul": h["title"],
        "ucapan": part["ucapan"],
        "layar_judul": part.get("layar_judul"),
        "layar": part.get("layar") or [],
        "petunjuk": "Bacakan 'ucapan' (boleh dirapikan, jangan ditambah materi lain), tampilkan "
        "'layar', akhiri dengan ajakan singkat lanjut."
        if index < len(lesson)
        else "Bacakan 'ucapan', lalu ajak mulai kuis singkat (ucapkan 'lanjut').",
    }


def start_help(
    course: str | None = None, meeting: int | None = None, topic: str | None = None
) -> dict:
    """Mulai bantuan SORA: yang sudah disiapkan, atau siapkan sekarang untuk topik yang diminta."""
    try:
        store = TutorStore()
        h = current_help(store)
        wanted = None
        if course or topic:
            source = _quiz_source(course, meeting, topic) if (meeting is None or topic) else None
            if source and "error" in source:
                return source
            from edupad.agent.tools import resolve_course

            target = resolve_course(source["course"] if source else course)
            m = source.get("meeting") if source else meeting
            if target and m is not None:
                wanted = topic_key(target["course_id"], target["matkul"], m)
            if wanted and (not h or h["topic_key"] != wanted):
                mastery = next((x for x in store.mastery() if x["topic_key"] == wanted), None)
                h = prepare_help(
                    store,
                    {
                        "topic_key": wanted,
                        "course": target["matkul"],
                        "course_id": target["course_id"],
                        "meeting": m,
                        "title": topic or "",
                        "reasons": ["diminta mahasiswa"],
                        "mistakes": [],
                        "mastery": float(mastery["mastery"]) if mastery else None,
                    },
                )
        if not h:
            return {"error": "belum ada bantuan yang disiapkan; sebutkan mata kuliah & pertemuan"}
        _update(store, h["id"], {"status": "berjalan", "part": 1, "started_at": _now().isoformat()})
        h = {**h, "status": "berjalan", "part": 1}
        _remember_help(store.user_id, h)
        return _part(h, 1)
    except TutorUnavailable as e:
        return {"error": str(e)}


def continue_help() -> dict:
    """Bagian berikutnya; setelah bagian terakhir, kuis terarah dimulai."""
    try:
        store = TutorStore()
        h = current_help(store)
        if not h or h["status"] != "berjalan":
            return {"error": "tidak ada sesi bantuan yang sedang berjalan"}
        nxt = int(h.get("part") or 0) + 1
        lesson = h.get("lesson") or []
        if nxt <= len(lesson):
            _update(store, h["id"], {"part": nxt})
            h = {**h, "part": nxt}
            _remember_help(store.user_id, h)
            return _part(h, nxt)
        questions = h.get("questions") or []
        quiz = store.create_quiz(
            h["course"],
            h.get("course_id"),
            h.get("meeting"),
            h["title"],
            questions,
            help_id=h["id"],
        )
        _remember_quiz(store.user_id, quiz)
        _update(store, h["id"], {"status": "kuis"})
        _remember_help(store.user_id, {**h, "status": "kuis"})
        return {
            "kuis_dimulai": True,
            "judul": h["title"],
            "jumlah_soal": len(questions),
            "soal_ke": 1,
            "pertanyaan": questions[0]["pertanyaan"],
            "petunjuk": "Bilang kuisnya singkat, lalu bacakan pertanyaan 1 persis. Jangan sebut kunci.",
        }
    except TutorUnavailable as e:
        return {"error": str(e)}


def decline_help() -> dict:
    try:
        store = TutorStore()
        h = current_help(store)
        if not h:
            return {"error": "tidak ada bantuan yang sedang ditawarkan"}
        _update(store, h["id"], {"status": "ditolak", "declined_at": _now().isoformat()})
        _remember_help(store.user_id, None)
        return {
            "ditunda": True,
            "judul": h["title"],
            "ditawarkan_lagi_dalam_hari": DECLINED_PAUSE.days,
        }
    except TutorUnavailable as e:
        return {"error": str(e)}


# ------------------------------- analisis harian -----------------------------
def run(prepare: bool = True, limit: int = MAX_PER_RUN) -> int:
    """Cron sore: analisis kesulitan, siapkan bantuan untuk 1-2 topik. Status owl di Office."""
    from edupad.errors import EXIT_ERROR, EXIT_OK
    from edupad.office.events import emit_status
    from edupad.office.models import AgentState

    emit_status(
        "analyst",
        AgentState.RUNNING,
        room="analytics-room",
        job_type="coach",
        message="Menganalisis topik yang sulit",
        progress=10,
    )
    try:
        store = TutorStore()
        now = _now()
        blocked = _blocked(store, now)
        found = struggles(store, now)
        todo = [t for t in found if t["topic_key"] not in blocked][:limit]
        log.info("[coach] %d topik sulit, %d disiapkan", len(found), len(todo) if prepare else 0)
        made = []
        if prepare:
            for t in todo:
                emit_status(
                    "tutor",
                    AgentState.RUNNING,
                    room="tutor-room",
                    job_type="coach",
                    message=f"Menyiapkan bantuan: {t['title'] or t['course']}",
                    progress=50,
                )
                try:
                    made.append(prepare_help(store, t))
                except TutorUnavailable as e:
                    log.warning("[coach] %s: %s", t["topic_key"], e)
        for row in made:
            log.info("[selesai] bantuan siap: %s (%s)", row["title"], ", ".join(row["reasons"]))
        emit_status(
            "analyst",
            AgentState.SUCCEEDED,
            room="analytics-room",
            job_type="coach",
            message=f"{len(found)} topik perlu perhatian, {len(made)} bantuan disiapkan",
            progress=100,
        )
        return EXIT_OK
    except TutorUnavailable as e:
        log.error("[x] tutor-coach: %s", e)
        emit_status(
            "analyst", AgentState.FAILED, room="analytics-room", job_type="coach", message=str(e)
        )
        return EXIT_ERROR


TOOLS = {"start_help": start_help, "continue_help": continue_help, "decline_help": decline_help}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "start_help",
            "description": "Mulai bantuan belajar SORA (pelajaran mini lewat suara lalu kuis terarah): "
            "yang sudah disiapkan (BANTUAN SIAP), atau untuk topik yang mahasiswa belum paham.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course": {"type": "string", "description": "mata kuliah (opsional)"},
                    "meeting": {"type": "integer", "description": "nomor pertemuan (opsional)"},
                    "topic": {"type": "string", "description": "topik/konsep (opsional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "continue_help",
            "description": "Lanjut ke bagian berikutnya dari sesi bantuan SORA yang berjalan; setelah "
            "bagian terakhir, kuis terarah dimulai.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decline_help",
            "description": 'Tunda bantuan yang ditawarkan SORA ("nanti saja").',
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
