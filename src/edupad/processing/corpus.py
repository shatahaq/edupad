"""Markdown hasil konversi -> corpus bersih untuk AI agent.

Output di data/corpus/:
  catalog.json               mata kuliah di KRS, alias, dan daftar pertemuan
  meetings/<course>/pNN.md   seluruh materi satu pertemuan (tool get_pertemuan)
  chunks.jsonl               potongan ~350 kata + metadata (untuk embedding)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edupad.config import CORPUS_DIR, MARKDOWN_DIR, MATERIALS_DIR, WIB
from edupad.core.academic import krs_classes
from edupad.core.files import read_json, write_text_if_changed

log = logging.getLogger(__name__)

CATALOG_FILE = CORPUS_DIR / "catalog.json"
CHUNKS_FILE = CORPUS_DIR / "chunks.jsonl"
MEETINGS_DIR = CORPUS_DIR / "meetings"

TARGET_WORDS = 350
MAX_WORDS = 550
MIN_CHUNK_WORDS = 15
BOILERPLATE_RATIO = 0.5  # baris yang muncul di >= 50% halaman/slide = footer/header
MIN_SEGMENTS_FOR_BOILERPLATE = 4
MAX_MEETING_RANGE = 3  # "Pertemuan 1–2" wajar; "2024-2025" bukan rentang pertemuan
TYPE_ORDER = {"deskripsi": 0, "page": 1, "book": 1, "label": 2}

SEGMENT_MARK = re.compile(r"<!-- (halaman|slide) (\d+)( \(OCR\))? -->")
STOPWORDS = {"dan", "di", "ke", "untuk", "dengan", "pada", "the", "of"}


# ------------------------------ reading --------------------------------------
def read_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(": ")
        try:
            meta[key] = json.loads(value)
        except json.JSONDecodeError:
            meta[key] = value
    return meta, text[m.end() :]


def source_hashes() -> dict[str, str]:
    """source_file -> sha256 file asli, untuk mendeteksi materi yang sama persis."""
    hashes = {}
    for course in read_json(MATERIALS_DIR / "manifest.json").get("courses", {}).values():
        for section in course["sections"]:
            files = ([section["summary"]] if section.get("summary") else []) + section.get(
                "summary_files", []
            )
            for item in section["items"]:
                files += item["files"]
            hashes.update({f["path"]: f["sha256"] for f in files})
    return hashes


# ------------------------------ cleaning -------------------------------------
def split_segments(body: str) -> list[dict]:
    marks = list(SEGMENT_MARK.finditer(body))
    if not marks:
        return [{"kind": None, "number": None, "ocr": False, "text": body}]
    segments = []
    head = body[: marks[0].start()].strip()
    if head:
        segments.append({"kind": None, "number": None, "ocr": False, "text": head})
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        segments.append(
            {
                "kind": m.group(1),
                "number": int(m.group(2)),
                "ocr": bool(m.group(3)),
                "text": body[m.end() : end],
            }
        )
    return segments


_PAGE_COUNTER = re.compile(r"\b\d+\s*/\s*\d+\b|\b(?:hal(?:aman)?|page|slide)\s*\.?\s*\d+\b", re.I)


def boilerplate_key(line: str) -> str:
    """Kunci pembanding baris berulang.

    Angka hanya diabaikan pada baris berpenomoran halaman ('2/27' ~ '3/27');
    baris lain harus sama persis, agar 'Langkah 1' dan 'Langkah 2' tidak dianggap footer.
    """
    key = re.sub(r"\s+", " ", re.sub(r"[*_#>`~|-]", "", line)).strip().lower()
    return re.sub(r"\d+", "#", key) if _PAGE_COUNTER.search(key) else key


def find_boilerplate(segments: list[dict]) -> set[str]:
    if len(segments) < MIN_SEGMENTS_FOR_BOILERPLATE:
        return set()
    counts = Counter()
    for seg in segments:
        counts.update({key for line in seg["text"].splitlines() if (key := boilerplate_key(line))})
    limit = max(3, BOILERPLATE_RATIO * len(segments))
    return {key for key, n in counts.items() if n >= limit and len(key) <= 150}


def clean_text(text: str, boilerplate: set[str]) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    lines = []
    for raw in text.splitlines():
        if boilerplate and boilerplate_key(raw) in boilerplate:
            continue
        line = re.sub(r"^(\s*)\*\*(.+?)\*\*\s*$", r"\1\2", raw.rstrip())  # baris tebal penuh
        lines.append(re.sub(r"\s+([.,;:!?])", r"\1", line))

    # nomor yang berdiri sendiri + baris berikutnya -> "1. teks" (pola umum di slide)
    merged, i = [], 0
    is_number = re.compile(r"\d{1,2}[.)]?")
    while i < len(lines):
        current = lines[i].strip()
        nxt = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
        if (
            is_number.fullmatch(current)
            and nxt is not None
            and not is_number.fullmatch(lines[nxt].strip())
        ):
            merged.append(f"{current.rstrip('.)')}. {lines[nxt].strip()}")
            i = nxt + 1
            continue
        merged.append(lines[i])
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(merged)).strip()


def strip_scraper_header(body: str) -> str:
    """Materi HTML diawali '# judul' + 'Sumber: url' yang sudah ada di metadata."""
    return re.sub(r"\A\s*#[^\n]*\n+Sumber: \S+\n+", "", body)


def detect_meetings(meta: dict, body: str) -> list[int]:
    """Nomor pertemuan dokumen.

    Judul section bernomor dipakai langsung. Bila tidak bernomor, nomor yang
    ditulis di materi lebih dipercaya daripada urutan section Moodle. Rentang
    "Pertemuan 1–2" / nama file "6-7 Praktik" menghasilkan semua nomornya.
    """
    section = meta.get("section") or ""
    explicit = re.search(r"pertemuan\s*(\d{1,2})", section, re.I) or re.match(
        r"\s*(\d{1,2})\b", section
    )
    base = int(explicit.group(1)) if explicit else meta.get("section_index") or None
    filename = Path(meta.get("source_file", "")).name
    head = filename + "\n" + body[:1500]
    span = re.search(
        r"pertemuan\s*(\d{1,2})\s*(?:[-–—]|s/d|sampai|dan|&)\s*(\d{1,2})", head, re.I
    ) or re.match(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\b", filename)
    numbers: set[int] = set()
    if span and int(span.group(1)) < int(span.group(2)) <= int(span.group(1)) + MAX_MEETING_RANGE:
        numbers = set(range(int(span.group(1)), int(span.group(2)) + 1))
    elif not explicit and (single := re.search(r"pertemuan\s*(\d{1,2})\b", head, re.I)):
        numbers = {int(single.group(1))}
    if (explicit or not numbers) and base:
        numbers.add(base)
    return sorted(numbers)


# ------------------------------ catalog --------------------------------------
def course_aliases(name: str, code: str | None) -> list[str]:
    """'Pemrograman Visual' -> ['pemrograman visual', 'pv', 'tif 3 031', ...].

    Alias praktikum selalu diawali 'prak'/'praktikum' agar tidak bentrok dengan kelas teori.
    """
    is_lab = name.lower().startswith("praktikum")
    base_name = re.sub(r"^praktikum\s+", "", name, flags=re.I).strip()
    base = base_name.lower()
    words = [w for w in re.findall(r"[A-Za-z0-9]+", base_name) if w.lower() not in STOPWORDS]
    initials = "".join(
        w.lower() if w.isupper() and len(w) <= 3 else w[0].lower()
        for w in words
        if not w[0].isdigit()
    )
    aliases = {name.lower()}
    if is_lab:
        aliases |= {f"praktikum {base}", f"prak {base}"}
        if len(initials) >= 2:
            aliases |= {f"praktikum {initials}", f"prak {initials}"}
    else:
        aliases.add(base)
        if len(initials) >= 2:
            aliases.add(initials)
        if code:
            aliases |= {code.lower(), code.lower().replace(" ", "")}
    return sorted(aliases)


def build_catalog(classes: list[dict]) -> dict[str, dict]:
    catalog = {}
    for k in classes:
        course_id = k.get("moodle_course_id")
        if not course_id:
            continue
        schedule = (
            f"{k['hari']} {k['mulai']}-{k['selesai']} di {k['ruang']}"
            if k.get("hari") and k.get("mulai")
            else None
        )
        catalog[course_id] = {
            "course_id": course_id,
            "matkul": k["matkul"],
            "kode": k["kode"],
            "kelas": k["kelas"],
            "jenis": k["jenis"],
            "sks": k["sks"],
            "dosen": k["dosen"],
            "jadwal": schedule,
            "alias": course_aliases(k["matkul"], k["kode"]),
            "pertemuan": {},
        }
    return catalog


# ------------------------------ chunking -------------------------------------
def _location(segments: list[dict]) -> str | None:
    numbers = [s["number"] for s in segments if s["number"] is not None]
    if not numbers:
        return None
    kind = segments[0]["kind"]
    return (
        f"{kind} {numbers[0]}"
        if numbers[0] == numbers[-1]
        else f"{kind} {numbers[0]}-{numbers[-1]}"
    )


def _split_long(text: str) -> list[str]:
    pieces, current = [], []
    for para in re.split(r"\n\s*\n", text):
        units = [para] if len(para.split()) <= MAX_WORDS else re.split(r"(?<=[.!?])\s+", para)
        for unit in units:
            if current and len(" ".join(current).split()) + len(unit.split()) > TARGET_WORDS:
                pieces.append("\n\n".join(current))
                current = []
            current.append(unit)
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def make_chunks(doc: dict) -> list[dict]:
    """Gabungkan halaman/slide berurutan sampai ~TARGET_WORDS tanpa memotong di tengah slide."""
    groups, current = [], []
    for seg in doc["segments"]:
        if (
            current
            and sum(len(s["text"].split()) for s in current) + len(seg["text"].split())
            > TARGET_WORDS
        ):
            groups.append(current)
            current = []
        current.append(seg)
    if current:
        groups.append(current)

    pieces = []
    for group in groups:
        text = "\n\n".join(s["text"] for s in group)
        for piece in _split_long(text) if len(text.split()) > MAX_WORDS else [text]:
            if len(piece.split()) >= MIN_CHUNK_WORDS:
                pieces.append((piece, _location(group), any(s["ocr"] for s in group)))

    meetings = ", ".join(map(str, doc["pertemuan"])) or "umum"
    chunks = []
    for i, (text, location, ocr) in enumerate(pieces):
        header = f"{doc['matkul']} | Pertemuan {meetings} | {doc['section']}\n{doc['judul']}"
        if location:
            header += f" ({location})"
        chunks.append(
            {
                "id": hashlib.sha1(f"{doc['sha256']}:{i}".encode()).hexdigest()[:16],
                "course_id": doc["course_id"],
                "matkul": doc["matkul"],
                "kode": doc["kode"],
                "pertemuan": doc["pertemuan"],
                "section": doc["section"],
                "judul": doc["judul"],
                "jenis": doc["jenis"],
                "lokasi": location,
                "ocr": ocr,
                "sumber_file": doc["source_file"],
                "sumber_url": doc["source_url"],
                "juga_di": doc["juga_di"],
                "kata": len(text.split()),
                "teks": text,
                "teks_embedding": f"{header}\n\n{text}",  # konteks ikut di-embed agar pencarian tepat
            }
        )
    return chunks


# ------------------------------ output ---------------------------------------
def meeting_markdown(course: dict, number: int | None, docs: list[dict]) -> str:
    title = f"Pertemuan {number}" if number else "Informasi umum"
    lines = [f"# {course['matkul']} ({course['kode']}, kelas {course['kelas']}) — {title}", ""]
    if course.get("dosen"):
        lines += [f"Dosen: {', '.join(course['dosen'])}", ""]
    for doc in docs:
        note = " · berisi teks hasil OCR" if doc["ocr"] else ""
        lines += [f"## {doc['judul']}", "", f"*Sumber: {doc['source_url']}{note}*", ""]
        for seg in doc["segments"]:
            if seg["number"] is not None:
                lines.append(f"<!-- {seg['kind']} {seg['number']} -->")
            lines += [seg["text"], ""]
    return "\n".join(lines).rstrip() + "\n"


def load_documents(catalog: dict[str, dict], stats: Counter) -> list[dict]:
    hashes = source_hashes()
    docs, by_hash = [], {}
    for path in sorted(MARKDOWN_DIR.rglob("*.md")):
        meta, body = read_markdown(path)
        if not meta.get("course_id"):
            continue
        stats["read"] += 1
        course_id = str(meta["course_id"])
        if course_id not in catalog:
            stats["outside_krs"] += 1
            continue
        digest = hashes.get(meta.get("source_file")) or hashlib.sha256(body.encode()).hexdigest()
        if digest in by_hash:
            first = by_hash[digest]
            if course_id != first["course_id"] and course_id not in first["juga_di"]:
                first["juga_di"].append(course_id)
            stats["duplicates"] += 1
            continue

        body = strip_scraper_header(body)
        segments = split_segments(body)
        boilerplate = find_boilerplate(segments)
        stats["boilerplate"] += len(boilerplate)
        for seg in segments:
            seg["text"] = clean_text(seg["text"], boilerplate)
        segments = [s for s in segments if s["text"]]
        if not segments:
            stats["empty"] += 1
            continue
        doc = {
            "course_id": course_id,
            "matkul": catalog[course_id]["matkul"],
            "kode": catalog[course_id]["kode"],
            "section": meta.get("section"),
            "judul": meta.get("title") or path.stem,
            "jenis": meta.get("type"),
            "pertemuan": detect_meetings(meta, body),
            "source_file": meta.get("source_file"),
            "source_url": meta.get("source_url"),
            "sha256": digest,
            "juga_di": [],
            "segments": segments,
            "ocr": any(s["ocr"] for s in segments),
        }
        docs.append(doc)
        by_hash[digest] = doc
    return docs


def write_meetings(catalog: dict[str, dict], docs: list[dict], stats: Counter) -> None:
    grouped = defaultdict(list)
    for doc in docs:
        for number in doc["pertemuan"] or [None]:
            grouped[(doc["course_id"], number)].append(doc)

    written = set()
    for (course_id, number), group in sorted(
        grouped.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)
    ):
        group.sort(key=lambda d: (TYPE_ORDER.get(d["jenis"], 3), d["judul"]))
        path = MEETINGS_DIR / course_id / (f"p{number:02d}.md" if number else "p00_umum.md")
        if write_text_if_changed(path, meeting_markdown(catalog[course_id], number, group)):
            stats["meetings_updated"] += 1
        written.add(path)
        catalog[course_id]["pertemuan"][str(number) if number else "umum"] = {
            "judul_section": group[0]["section"],
            "file": path.relative_to(CORPUS_DIR).as_posix(),
            "materi": [
                {
                    "judul": d["judul"],
                    "jenis": d["jenis"],
                    "ocr": d["ocr"],
                    "sumber_url": d["source_url"],
                }
                for d in group
            ],
            "kata": sum(len(s["text"].split()) for d in group for s in d["segments"]),
        }
    if MEETINGS_DIR.exists():
        for old in MEETINGS_DIR.rglob("*.md"):
            if old not in written:  # materi pertemuan itu sudah dihapus dosen
                old.unlink()
    stats["meetings"] = len(written)


def run() -> int:
    classes = krs_classes()
    if not classes:
        log.error(
            "[x] Jadwal belum ada. Jalankan `python -m edupad schedule` dulu (KRS dipakai "
            "untuk menyaring mata kuliah)."
        )
        return 1
    catalog = build_catalog(classes)
    stats = Counter()
    docs = load_documents(catalog, stats)
    write_meetings(catalog, docs, stats)

    chunks = [chunk for doc in docs for chunk in make_chunks(doc)]
    write_text_if_changed(
        CHUNKS_FILE, "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks)
    )
    write_text_if_changed(
        CATALOG_FILE,
        json.dumps(
            {
                "diperbarui": datetime.now(WIB).isoformat(timespec="minutes"),
                "mata_kuliah": list(catalog.values()),
            },
            indent=2,
            ensure_ascii=False,
        ),
    )

    words = [c["kata"] for c in chunks] or [0]
    log.info(
        "[selesai] %d dokumen dibaca: %d di luar KRS, %d duplikat, %d kosong -> %d dokumen bersih",
        stats["read"],
        stats["outside_krs"],
        stats["duplicates"],
        stats["empty"],
        len(docs),
    )
    log.info(
        "          %d pola footer/header dibuang; %d file pertemuan (%d diperbarui); "
        "%d chunk (rata-rata %d kata, maks %d, %d dari OCR)",
        stats["boilerplate"],
        stats["meetings"],
        stats["meetings_updated"],
        len(chunks),
        sum(words) // len(words),
        max(words),
        sum(c["ocr"] for c in chunks),
    )
    return 0
