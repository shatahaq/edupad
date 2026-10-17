"""Perintah setelan yang dijawab server sendiri, tanpa memanggil LLM maupun TTS.

"Aktifkan mode suara", "matikan mode suara", dan "bicara lebih cepat/lambat" selalu berakhir
pada salah satu dari beberapa kalimat yang sama. Menyusunnya lewat agent berarti membayar dua
panggilan LLM (satu memilih tool, satu menyusun `answer`) dan satu panggilan TTS untuk kalimat
yang sudah diketahui sejak awal. Di sini transkrip STT dicocokkan ke pola di bawah: yang cocok
langsung mengubah setelan lalu dijawab kalimat template, suaranya dibaca dari simpanan disk
(voice/clips.py). Yang tidak cocok diteruskan ke agent seperti biasa.

Polanya sengaja fullmatch dan daftar katanya pendek: "aktifkan mode suara" dilayani di sini,
tetapi "apa itu mode suara?" tetap dijawab agent. Lebih baik satu perintah lolos ke LLM
daripada satu pertanyaan dibalas template yang salah.

Kecepatan diubah relatif (satu tingkat dari setelan sekarang), jadi "lebih cepat" berturut-turut
menaik sampai batas, bukan melompat ke nilai yang ditebak model.
"""

from __future__ import annotations

import logging
import re

from edupad.agent.formatting import fit_screen
from edupad.voice import clips
from edupad.voice import mode as voice_mode

log = logging.getLogger(__name__)

URL_PREFIX = "/v1/voice/reply/"

# Kata sopan/sapaan yang boleh mengapit perintah tanpa mengubah maksudnya.
_FILLER = r"(?:tolong|coba|edupad|eduped|ya|dong|deh|sekarang|please)"
_PAD, _TAIL = rf"(?:{_FILLER}\s+)*", rf"(?:\s+{_FILLER})*"
_MODE = r"mode\s+(?:suara|tunanetra|bicara)"
_TALK = r"(?:bicara|berbicara|ngomong|baca|bacanya|suaranya|bicaranya)"

# (nama, pola) -> dicoba berurutan; yang pertama cocok dipakai.
PATTERNS = [
    ("on", rf"(?:aktifkan|aktifin|nyalakan|nyalain|hidupkan|mulai)\s+{_MODE}"),
    ("off", rf"(?:matikan|matiin|nonaktifkan|hentikan|keluar\s+dari)\s+{_MODE}"),
    ("faster", rf"(?:{_TALK}\s+)?lebih\s+cepat|percepat(?:\s+{_TALK})?"),
    ("slower", rf"(?:{_TALK}\s+)?lebih\s+(?:lambat|pelan)|perlambat(?:\s+{_TALK})?"),
]
_COMPILED = [(name, re.compile(rf"{_PAD}(?:{body}){_TAIL}")) for name, body in PATTERNS]

# Kalimat tetap per hasil. `lines` sudah dipotong lagi oleh fit_screen agar pas di LCD.
REPLIES = {
    "on": {
        "speech": "Mode suara aktif. Semua jawaban dan pemberitahuan sekarang dibacakan lengkap. "
        "Untuk mematikannya, ucapkan matikan mode suara.",
        "title": "Mode Suara aktif",
        "lines": ["Jawaban & pemberitahuan dibacakan penuh", "Matikan: 'matikan mode suara'"],
    },
    "off": {
        "speech": "Mode suara dimatikan. Jawaban tetap dibacakan singkat, rinciannya di layar.",
        "title": "Mode Suara mati",
        "lines": ["Jawaban dibacakan singkat", "Rinciannya tampil di layar"],
    },
    "lambat": {
        "speech": "Baik, aku bicara lebih lambat.",
        "title": "Kecepatan: lambat",
        "lines": ["Ucapkan 'bicara lebih cepat' untuk menaikkan"],
    },
    "normal": {
        "speech": "Baik, kecepatan bicaraku kembali normal.",
        "title": "Kecepatan: normal",
        "lines": ["Bisa diubah: 'bicara lebih cepat' / 'lebih lambat'"],
    },
    "cepat": {
        "speech": "Baik, aku bicara lebih cepat.",
        "title": "Kecepatan: cepat",
        "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
    },
    "sangat_cepat": {
        "speech": "Baik, ini kecepatan bicaraku yang paling cepat.",
        "title": "Kecepatan: sangat cepat",
        "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
    },
    "fastest": {
        "speech": "Ini sudah kecepatan paling cepat.",
        "title": "Sudah paling cepat",
        "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
    },
    "slowest": {
        "speech": "Ini sudah kecepatan paling lambat.",
        "title": "Sudah paling lambat",
        "lines": ["Ucapkan 'bicara lebih cepat' untuk menaikkan"],
    },
}

SPEED_ORDER = list(voice_mode.SPEEDS)  # lambat -> sangat_cepat


def _normalize(text: str) -> str:
    """Huruf kecil tanpa tanda baca, spasi dirapatkan: transkrip STT tidak selalu rapi."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", text.lower())).strip()


def _match(text: str) -> str | None:
    spoken = _normalize(text)
    return next((name for name, pattern in _COMPILED if pattern.fullmatch(spoken)), None)


def _step(up: bool) -> str:
    """Naik/turun satu tingkat kecepatan; nama balasan bila sudah di ujung."""
    at = SPEED_ORDER.index(voice_mode.load()["speed"])
    to = at + (1 if up else -1)
    if not 0 <= to < len(SPEED_ORDER):
        return "fastest" if up else "slowest"
    voice_mode.save(speed=SPEED_ORDER[to])
    return SPEED_ORDER[to]


def handle(text: str) -> dict | None:
    """Terapkan perintah setelan dalam `text` dan kembalikan jawaban siap kirim; None bila
    ucapan ini bukan perintah setelan dan harus diteruskan ke agent."""
    command = _match(text)
    if command is None:
        return None
    if command in ("on", "off"):
        voice_mode.save(enabled=command == "on")
        reply_name = command
    else:
        reply_name = _step(up=command == "faster")
    reply = REPLIES[reply_name]
    log.info("[mode suara] perintah %r dijawab template %s (tanpa LLM)", text, reply_name)
    return {
        "speech": reply["speech"],
        "screen": fit_screen(reply["title"], reply["lines"]),
        "detail": "",
        "reply": reply_name,
        "audio_url": f"{URL_PREFIX}{reply_name}?v={_audio_version(reply_name)}",
    }


def _audio_version(name: str) -> str:
    return clips.version(REPLIES[name]["speech"], voice_mode.speed_value())


def load(name: str) -> bytes:
    """PCM kalimat template `name`; KeyError bila tidak dikenal, tts.TTSError bila TTS gagal."""
    return clips.cached_pcm(f"reply-{name}", REPLIES[name]["speech"], voice_mode.speed_value())
