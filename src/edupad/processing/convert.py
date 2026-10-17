"""Konversi file materi (PDF, PPTX, DOCX, HTML) ke Markdown ber-metadata.

- PDF : pymupdf4llm per halaman; OCR lokal hanya untuk halaman berupa gambar.
- PPTX: dibaca per slide dari XML-nya, termasuk catatan dosen.
- DOCX dll.: anydoc.
anydoc tidak dipakai untuk PDF/PPTX karena mengacak urutan teks slide ke
tabel semu dan menghilangkan batas halaman/slide.
Semua proses lokal; tidak ada materi yang dikirim ke layanan luar.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import multiprocessing
import posixpath
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import anydoc

from edupad.config import MARKDOWN_DIR, MATERIALS_DIR
from edupad.core.academic import meeting_number
from edupad.core.files import read_json, write_json
from edupad.core.markdown import clean_markdown, html_to_markdown

log = logging.getLogger(__name__)

INDEX_FILE = MARKDOWN_DIR / "index.json"
MANIFEST_FILE = MATERIALS_DIR / "manifest.json"

# Naikkan bila cara konversi berubah: semua file akan dikonversi ulang.
CONVERTER_VERSION = 2

ANYDOC_EXTS = {".doc", ".docx", ".ppt", ".odt", ".odp", ".rtf", ".epub"}
TEXT_EXTS = {".md", ".txt"}
HTML_EXTS = {".html", ".htm"}
SUPPORTED_EXTS = ANYDOC_EXTS | TEXT_EXTS | HTML_EXTS | {".pdf", ".pptx"}

OCR_MIN_CHARS = 200  # halaman dengan teks sesedikit ini...
OCR_MIN_IMAGE_AREA = 0.15  # ...dan gambar >= 15% luas halaman di-OCR

_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


# ------------------------------ PDF ------------------------------------------
def _needs_ocr(page) -> bool:
    if len(page.get_text().strip()) >= OCR_MIN_CHARS:
        return False
    area = page.rect.width * page.rect.height
    return any(
        (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]) >= OCR_MIN_IMAGE_AREA * area
        for i in page.get_image_info()
    )


def pdf_to_markdown(path: Path) -> tuple[str, str]:
    import pymupdf
    import pymupdf4llm

    # Ditutup setelah dipakai: dokumen yang dibiarkan terbuka menumpuk memori selama run.
    with pymupdf.open(path) as doc, contextlib.redirect_stdout(io.StringIO()):
        # pymupdf4llm mencetak log ke stdout
        ocr_pages = [i for i, page in enumerate(doc) if _needs_ocr(page)]
        pages = {
            p["metadata"]["page_number"]: p["text"]
            for p in pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)
        }
        if ocr_pages:
            for p in pymupdf4llm.to_markdown(
                doc, pages=ocr_pages, page_chunks=True, force_ocr=True
            ):
                pages[p["metadata"]["page_number"]] = p["text"]
    ocr_numbers = {i + 1 for i in ocr_pages}
    parts = [
        f"<!-- halaman {n}{' (OCR)' if n in ocr_numbers else ''} -->\n\n{text}"
        for n, text in sorted(pages.items())
        if text.strip()
    ]
    converter = f"pymupdf4llm+ocr({len(ocr_pages)} hal)" if ocr_pages else "pymupdf4llm"
    return "\n\n".join(parts), converter


def pdf_to_markdown_isolated(path: Path) -> tuple[str, str]:
    """pdf_to_markdown di proses anak sekali pakai.

    Di server (Python 3.14) memori OCR menumpuk ratusan MB per file sampai convert dimatikan
    OOM killer; proses anak mengembalikan semuanya ke OS setelah tiap file. "spawn" (bukan
    fork) agar anak mulai bersih walau induk sedang punya thread.
    """
    with ProcessPoolExecutor(1, mp_context=multiprocessing.get_context("spawn")) as pool:
        return pool.submit(pdf_to_markdown, path).result()


# ------------------------------ PPTX -----------------------------------------
def _slide_text(root, skip_placeholders: tuple[str, ...] = ()) -> tuple[str | None, list[str]]:
    title, lines = None, []
    for shape in root.iter(f"{{{_NS['p']}}}sp"):
        ph = shape.find(".//p:nvPr/p:ph", _NS)
        ph_type = ph.get("type") if ph is not None else None
        if ph_type in skip_placeholders:
            continue
        for para in shape.iterfind(".//a:p", _NS):
            text = re.sub(
                r"\s+", " ", "".join(t.text or "" for t in para.iter(f"{{{_NS['a']}}}t"))
            ).strip()
            if not text:
                continue
            if ph_type in ("title", "ctrTitle") and title is None:
                title = text
                continue
            ppr = para.find("a:pPr", _NS)
            bullet = ppr is not None and (
                ppr.find("a:buChar", _NS) is not None or ppr.find("a:buAutoNum", _NS) is not None
            )
            level = int(ppr.get("lvl", 0)) if ppr is not None else 0
            lines.append(("  " * level + "- " if bullet else "") + text)
    for table in root.iter(f"{{{_NS['a']}}}tbl"):
        rows = [
            [
                "".join(t.text or "" for t in cell.iter(f"{{{_NS['a']}}}t"))
                .strip()
                .replace("|", "/")
                for cell in tr.iterfind("a:tc", _NS)
            ]
            for tr in table.iterfind("a:tr", _NS)
        ]
        if rows:
            lines += ["", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
            lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return title, lines


def pptx_to_markdown(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as z:
        presentation = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        slide_paths = [
            posixpath.normpath(posixpath.join("ppt", targets[s.get(f"{{{_NS['r']}}}id")]))
            for s in presentation.find("p:sldIdLst", _NS)
        ]
        names = set(z.namelist())
        parts = []
        for number, slide_path in enumerate(slide_paths, 1):
            title, lines = _slide_text(ET.fromstring(z.read(slide_path)))
            notes: list[str] = []
            rel_path = posixpath.join(
                posixpath.dirname(slide_path), "_rels", posixpath.basename(slide_path) + ".rels"
            )
            if rel_path in names:
                for rel in ET.fromstring(z.read(rel_path)):
                    if rel.get("Type", "").endswith("/notesSlide"):
                        notes_path = posixpath.normpath(
                            posixpath.join(posixpath.dirname(slide_path), rel.get("Target"))
                        )
                        _, notes = _slide_text(
                            ET.fromstring(z.read(notes_path)),
                            skip_placeholders=("sldImg", "sldNum"),
                        )
            if not (title or lines or notes):
                continue
            block = [f"<!-- slide {number} -->", "", f"## {title}" if title else "", *lines]
            if notes:
                block += ["", "**Catatan dosen:** " + " ".join(notes)]
            parts.append("\n".join(block))
    return "\n\n".join(parts), "pptx-slide"


# ------------------------------ dispatcher -----------------------------------
def convert_file(path: Path) -> tuple[str, str]:
    """(markdown bersih, nama konverter)."""
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        md, converter = path.read_text(encoding="utf-8"), "salin"
    elif ext in HTML_EXTS:
        md, converter = (
            html_to_markdown(path.read_text(encoding="utf-8", errors="replace")),
            "markdownify",
        )
    elif ext == ".pdf":
        md, converter = pdf_to_markdown_isolated(path)
    elif ext == ".pptx":
        md, converter = pptx_to_markdown(path)
    elif ext in ANYDOC_EXTS:
        md, converter = anydoc.to_markdown(path), "anydoc"
    else:
        raise ValueError(f"format {ext} belum didukung")
    return clean_markdown(md), converter


# ------------------------------ metadata -------------------------------------
def iter_sources(manifest: dict):
    """Satu entri per file materi di manifest scraper, lengkap dengan metadatanya."""
    for course in manifest.get("courses", {}).values():
        for section in course["sections"]:
            base = {
                "course_id": course["id"],
                "course": course["course"],
                "section": section["section"],
                "section_index": section["index"],
                "pertemuan": meeting_number(section["section"], section["index"]),
            }
            if section.get("summary"):
                yield {
                    **base,
                    "title": f"Deskripsi: {section['section']}",
                    "type": "deskripsi",
                    "activity_url": section.get("url"),
                    **_file_meta(section["summary"]),
                }
            for f in section.get("summary_files", []):
                yield {
                    **base,
                    "title": Path(f["path"]).stem,
                    "type": "lampiran-deskripsi",
                    "activity_url": section.get("url"),
                    **_file_meta(f),
                }
            for item in section["items"]:
                for f in item["files"]:
                    yield {
                        **base,
                        "title": item["title"],
                        "type": item["type"],
                        "activity_url": item["activity_url"],
                        **_file_meta(f),
                    }


def _file_meta(f: dict) -> dict:
    return {"source_file": f["path"], "source_url": f["source_url"], "sha256": f["sha256"]}


def _meta_hash(meta: dict) -> str:
    payload = json.dumps({**meta, "_converter": CONVERTER_VERSION}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def front_matter(meta: dict) -> str:
    # String JSON juga string YAML yang valid (aman untuk judul berisi ":").
    return (
        "---\n"
        + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items())
        + "\n---\n\n"
    )


def output_path(source_file: str) -> Path:
    src = Path(source_file)
    # "x.pdf" -> "x.pdf.md" agar tidak bentrok dengan "x.md" di folder yang sama
    name = src.name if src.suffix.lower() == ".md" else f"{src.name}.md"
    return MARKDOWN_DIR / src.parent / name


# ------------------------------ entry point ----------------------------------
FRONT_MATTER_KEYS = (
    "course_id",
    "course",
    "pertemuan",
    "section",
    "section_index",
    "title",
    "type",
    "source_file",
    "source_url",
    "activity_url",
)


def run(force: bool = False) -> int:
    manifest = read_json(MANIFEST_FILE)
    if not manifest.get("courses"):
        log.error("[x] %s belum ada. Jalankan scraper dulu.", MANIFEST_FILE)
        return 1
    old_index = {} if force else read_json(INDEX_FILE)
    index, failed = {}, []
    converted = unchanged = 0
    started = time.time()

    for meta in iter_sources(manifest):
        source = MATERIALS_DIR / meta["source_file"]
        out = output_path(meta["source_file"])
        meta_hash = _meta_hash(meta)
        previous = old_index.get(meta["source_file"])
        if previous and previous["meta_hash"] == meta_hash and out.exists():
            index[meta["source_file"]] = previous
            unchanged += 1
            continue

        log.info("[..] %s", meta["source_file"])
        t0 = time.time()
        try:
            if not source.exists():
                raise FileNotFoundError("file sumber tidak ada; jalankan ulang scraper")
            md, converter = convert_file(source)
            if not md:
                raise ValueError("hasil konversi kosong")
        except Exception as e:
            log.error("     [gagal] %s", e)
            failed.append((meta["source_file"], str(e)))
            continue

        fields = {k: meta[k] for k in FRONT_MATTER_KEYS} | {"converter": converter}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(front_matter(fields) + md + "\n", encoding="utf-8")
        index[meta["source_file"]] = {
            "output": out.relative_to(MARKDOWN_DIR).as_posix(),
            "converter": converter,
            "words": len(md.split()),
            "meta_hash": meta_hash,
            "converted_at": datetime.now().isoformat(timespec="seconds"),
        }
        converted += 1
        # Simpan kemajuan tiap file: bila proses dihentikan (mis. kehabisan memori di server),
        # run berikutnya melanjutkan, tidak mengulang file yang sama dari awal.
        write_json(INDEX_FILE, old_index | index)
        log.info("     [ok] %s, %d kata, %.1f dtk", converter, len(md.split()), time.time() - t0)

    for source_file, entry in old_index.items():  # sumber sudah dihapus dosen
        stale = MARKDOWN_DIR / entry["output"]
        if source_file not in index and stale.exists():
            stale.unlink()
            log.info("[hapus] %s", entry["output"])

    write_json(INDEX_FILE, index)
    log.info(
        "\n[selesai] %d dikonversi, %d tidak berubah, %d gagal (%.0f dtk).",
        converted,
        unchanged,
        len(failed),
        time.time() - started,
    )
    for source_file, error in failed:
        log.info("  gagal: %s -> %s", source_file, error)
    return 1 if failed else 0
