"""Mode Suara: EduPad dipakai sepenuhnya tanpa melihat layar (dirancang untuk mahasiswa tunanetra).

Saat aktif:
- jawaban AI menyampaikan seluruh isi lewat suara, tidak merujuk ke layar, dan menawarkan
  "lanjut" untuk penjelasan panjang (VOICE_RULES di system prompt, agent/assistant.py);
- semua pemberitahuan di perangkat dibacakan (GET /v1/updates memberi `speech` + `audio_url`);
  presensi dibuka dan deadline tugas dibacakan walau mode ini mati (ALWAYS_SPOKEN);
- firmware 1.2 membunyikan penanda (mulai/selesai merekam, sedang berpikir) dan memutar pesan
  status yang disimpan di perangkat (voice/clips.py), sehingga tetap terdengar walau offline.
Kecepatan bicara berlaku untuk semua suara jawaban, Mode Suara aktif atau tidak.

Pengaturan di data/device/voice_mode.json; diubah lewat suara atau dashboard (Pengaturan).
Frasa yang umum ("aktifkan mode suara", "bicara lebih cepat") sudah ditangani voice/commands.py
sebelum LLM dipanggil; tool set_voice_mode tinggal menangani sisanya. Pemakaian dicatat di
data/device/voice_events.jsonl untuk Equity Radar.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta

from edupad.config import DATA_DIR, WIB
from edupad.core.files import now_iso, read_json, write_json

log = logging.getLogger(__name__)

SETTINGS_FILE = DATA_DIR / "device" / "voice_mode.json"
EVENTS_FILE = DATA_DIR / "device" / "voice_events.jsonl"
# Parameter `speed` ElevenLabs (0,7-1,2). Pengguna pembaca layar umumnya terbiasa lebih cepat.
SPEEDS = {"lambat": 0.9, "normal": 1.05, "cepat": 1.15, "sangat_cepat": 1.2}
DEFAULT = {"enabled": False, "speed": "normal"}
EVENTS = frozenset({"answer", "alert"})
# Dibacakan walau Mode Suara mati: dua pemberitahuan yang menuntut tindakan segera, dan mudah
# terlewat kalau mahasiswa tidak sedang melihat layar (server.py memberinya `audio_url`).
ALWAYS_SPOKEN = frozenset({"attendance", "deadline"})

_lock = threading.Lock()

# Aturan tambahan system prompt saat Mode Suara aktif (statis agar awalan prompt tetap ter-cache).
VOICE_RULES = """

MODE SUARA AKTIF: mahasiswa ini tidak melihat layar (tunanetra). Semua informasi lewat speech;
aturan speech di atas (maks 3 kalimat, arahkan ke layar) TIDAK berlaku.
- speech memuat seluruh isi jawaban, boleh sampai ~120 kata. Jangan pernah merujuk ke layar.
- Daftar disebut jumlahnya lalu dibacakan berurutan: "Ada tiga tugas. Pertama, ... Kedua, ...".
  Tanggal, jam, dan angka diucapkan lengkap (mis. "Kamis, pukul sembilan malam").
- Isi lebih dari ~120 kata: bagian terpenting dulu, lalu tawarkan "Mau dilanjutkan?". Bila
  mahasiswa menjawab "lanjut"/"terus"/"ya", lanjutkan bagian berikutnya tanpa mengulang.
- Tabel, simbol, dan kode diubah jadi kalimat; kode dibacakan hanya bila diminta.
- screen_title/screen_lines tetap diisi ringkas untuk pendamping yang melihat."""

# Selalu ada di system prompt: cara menyalakan Mode Suara lewat suara.
PROMPT_RULE = """
- "Aktifkan/matikan mode suara" (atau mode tunanetra), "bicara lebih cepat/lambat" ->
  set_voice_mode, lalu konfirmasi singkat apa yang berubah."""


def load() -> dict:
    data = {**DEFAULT, **read_json(SETTINGS_FILE)}
    if data["speed"] not in SPEEDS:
        data["speed"] = DEFAULT["speed"]
    return {"enabled": bool(data["enabled"]), "speed": data["speed"]}


def enabled() -> bool:
    return load()["enabled"]


def speed_value() -> float:
    return SPEEDS[load()["speed"]]


def save(enabled: bool | None = None, speed: str | None = None) -> dict:
    """Ubah sebagian pengaturan; ValueError bila kecepatan tidak dikenal."""
    if speed is not None and speed not in SPEEDS:
        raise ValueError(f"kecepatan harus salah satu dari: {', '.join(SPEEDS)}")
    with _lock:
        data = load()
        if enabled is not None:
            data["enabled"] = bool(enabled)
        if speed is not None:
            data["speed"] = speed
        write_json(SETTINGS_FILE, {**data, "updated_at": now_iso()})
    log.info("[mode suara] %s, kecepatan %s", "aktif" if data["enabled"] else "mati", data["speed"])
    return data


def record(event: str) -> None:
    """Catat satu suara yang diputar (jawaban/pemberitahuan) untuk statistik aksesibilitas."""
    if event not in EVENTS:
        return
    try:
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock, EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now_iso(), "event": event}) + "\n")
    except OSError as e:
        log.debug("[mode suara] pemakaian tidak tercatat: %s", e)


def usage(days: int = 30, now: datetime | None = None) -> dict[str, int]:
    """Jumlah suara jawaban & pemberitahuan yang diputar dalam `days` hari terakhir."""
    since = (now or datetime.now(WIB)) - timedelta(days=days)
    counts = dict.fromkeys(EVENTS, 0)
    try:
        lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        try:
            row = json.loads(line)
            if datetime.fromisoformat(row["at"]) >= since and row["event"] in counts:
                counts[row["event"]] += 1
        except (ValueError, KeyError, TypeError):
            continue
    return counts


# --------------------------------- tool -----------------------------------
def set_voice_mode(enabled: bool | None = None, speed: str | None = None) -> dict:
    """Tool agent: nyalakan/matikan Mode Suara dan/atau ubah kecepatan bicara."""
    if enabled is None and speed is None:
        return {"error": "sebutkan mau menyalakan/mematikan mode suara atau mengubah kecepatan"}
    try:
        data = save(enabled, speed)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "mode_suara": "aktif" if data["enabled"] else "mati",
        "kecepatan": data["speed"].replace("_", " "),
        "petunjuk": "Konfirmasi singkat. Bila baru diaktifkan: semua jawaban & pemberitahuan "
        "dibacakan lengkap, tunggu bunyi penanda sebelum bicara, dan cara mematikannya. Bila "
        "dimatikan: jawaban tetap dibacakan tapi singkat, rinciannya di layar.",
    }


TOOLS = {"set_voice_mode": set_voice_mode}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_voice_mode",
            "description": "Nyalakan/matikan Mode Suara (semua jawaban & pemberitahuan dibacakan, "
            "untuk pengguna yang tidak melihat layar) atau ubah kecepatan bicara EduPad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "true = aktifkan, false = matikan",
                    },
                    "speed": {"type": "string", "enum": list(SPEEDS)},
                },
            },
        },
    }
]
