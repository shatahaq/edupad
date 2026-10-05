"""Konversi & pembersihan Markdown yang dipakai lintas modul."""

from __future__ import annotations

import re

from markdownify import markdownify

# Karakter CJK tidak pernah ada di materi kuliah ini: selalu sampah OCR dari ikon/logo.
_CJK = re.compile(r"[⺀-鿿豈-﫿　-〿＀-￯]+")


def html_to_markdown(html: str) -> str:
    """HTML (sering penuh inline CSS) -> Markdown; gaya dibuang, struktur dipertahankan."""
    md = markdownify(html, heading_style="ATX", bullets="-", strip=["span", "font"])
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def clean_markdown(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("​", "")
    md = re.sub(r"<!-- (Start|End) of picture text -->", "\n", md)  # penanda pymupdf4llm
    md = re.sub(r"<br\s*/?>", "\n", md)
    md = re.sub(r"</?su[bp]>", "", md)
    md = _CJK.sub("", md)
    md = re.sub(r"~~(.{1,2})~~", "", md)
    md = re.sub(r"^(#{1,6}) \*\*(.+?)\*\*\s*$", r"\1 \2", md, flags=re.M)
    md = re.sub(r"^#{1,6}\s*$", "", md, flags=re.M)
    md = re.sub(r"^\s*[^\w\s]{1,2}\s*$", "", md, flags=re.M)  # baris simbol tunggal: ×, •
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()
