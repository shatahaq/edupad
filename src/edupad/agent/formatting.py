"""Bentuk jawaban untuk EduPad: suara (TTS), layar LCD, dan detail (Markdown).

LLM diminta langsung menulis tiap bentuk; fungsi di sini adalah pengaman
terakhir bila model tetap menyelipkan Markdown atau menulis terlalu panjang.
"""

from __future__ import annotations

import re
import textwrap
import unicodedata

MAX_SPEECH_CHARS = 450   # ~30 detik bicara
SCREEN_COLS = 38         # LCD 2,4" 320x240, font 8x16 dengan margin
SCREEN_TITLE_COLS = 24   # judul memakai font 2x
SCREEN_MAX_LINES = 9

_ASCII_MAP = str.maketrans({
    "—": "-", "–": "-", "•": "-", "·": "-", "…": "...", "→": "->", "←": "<-", "≥": ">=",
    "≤": "<=", "≠": "!=", "×": "x", "“": '"', "”": '"', "‘": "'", "’": "'",
})


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)             # blok kode tidak dibacakan
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)          # [teks](url) -> teks
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*\|?\s*:?-{3,}.*$", "", text, flags=re.M)   # garis pemisah tabel
    text = text.replace("|", ", ")
    text = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+]|\d+[.)])\s+", "", text, flags=re.M)
    text = re.sub(r"(\*\*|\*|`|~~)", "", text)
    text = re.sub(r"(?<!\w)_{1,2}(?=\S)|(?<=\S)_{1,2}(?!\w)", "", text)  # read_csv tetap utuh
    return text


def _strip_symbols(text: str) -> str:
    """Emoji & simbol dekoratif dibuang; huruf, angka, dan tanda baca dipertahankan."""
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LNPZ" or ch in "+-=<>/%\n")


def clean_speech(text: str) -> str:
    text = _strip_symbols(strip_markdown(text).translate(_ASCII_MAP))
    text = re.sub(r"\s*\n+\s*", ". ", text.strip())
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"([.!?])[.,;:\s]+(?=\S)", r"\1 ", text)
    if len(text) > MAX_SPEECH_CHARS:
        cut = text[:MAX_SPEECH_CHARS]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        text = cut[:end + 1] if end > MAX_SPEECH_CHARS // 3 else cut.rsplit(" ", 1)[0] + "."
    return text.strip()


def to_display_text(text: str) -> str:
    """Teks yang aman untuk font ASCII di LCD."""
    text = strip_markdown(text).translate(_ASCII_MAP)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[ \t]+", " ", text).strip()


def fit_screen(title: str, lines: list[str]) -> dict:
    """Judul + baris yang sudah dibungkus sesuai lebar LCD dan dibatasi jumlahnya.

    Judul yang tidak muat di font besar ditampilkan dengan font normal (title_size).
    """
    title = to_display_text(title)
    title_size = "large" if len(title) <= SCREEN_TITLE_COLS else "normal"
    if len(title) > SCREEN_COLS:
        title = textwrap.shorten(title, SCREEN_COLS, placeholder="...")
    wrapped: list[str] = []
    for line in lines:
        line = to_display_text(line)
        if not line:
            continue
        parts = textwrap.wrap(line, SCREEN_COLS - 2) or [""]
        wrapped += [f"- {parts[0]}"] + [f"  {p}" for p in parts[1:]]
    if len(wrapped) > SCREEN_MAX_LINES:
        wrapped = wrapped[:SCREEN_MAX_LINES - 1] + ["  ..."]
    return {"title": title, "title_size": title_size, "lines": wrapped}


def fallback_answer(markdown: str) -> dict:
    """Bila model tidak memakai tool `answer`, turunkan ketiga bentuk dari teks biasa.

    Bagian berlabel "Layar:"/"Sumber:" tidak pernah ikut dibacakan.
    """
    parts = re.split(r"(?im)^\s*layar\s*:", markdown, maxsplit=1)
    spoken = re.split(r"(?im)^\s*sumber\s*:", parts[0], maxsplit=1)[0]
    if len(parts) == 1:
        plain = [ln for ln in (to_display_text(x) for x in strip_markdown(spoken).splitlines()) if ln]
        title, lines = (plain[0] if plain else "EduPad"), plain[1:SCREEN_MAX_LINES]
    else:
        screen_text = re.split(r"(?im)^\s*sumber\s*:", parts[1], maxsplit=1)[0]
        items = re.split(r"\n|\s\|\s|\.\s", screen_text)  # dipecah sebelum strip_markdown mengganti "|"
        lines = [ln for ln in (to_display_text(strip_markdown(x)) for x in items) if ln]
        title = "EduPad"
    return {
        "speech": clean_speech(spoken),
        "screen": fit_screen(title, lines),
        "detail": markdown.strip(),
    }
