// Mode Suara (server: src/edupad/voice/mode.py): EduPad dipakai tanpa melihat layar, dirancang
// untuk mahasiswa tunanetra. Saat aktif: bunyi penanda (mulai/selesai merekam, sedang berpikir),
// pemberitahuan dibacakan, dan pesan status diputar dari PSRAM sehingga tetap terdengar walau
// Wi-Fi atau server sedang putus. Saat mati, semua fungsi di sini tidak berbuat apa-apa.
#pragma once

#include <ArduinoJson.h>

namespace voice {

enum class Cue { Listen, Sent, Thinking, Error, Wake };

// Status terakhir dari NVS, supaya penanda tetap berbunyi walau server belum terjangkau.
void begin();
// `voice_mode` dan `voice_clips` dari /v1/updates atau /v1/ask (field yang tidak ada diabaikan).
void update(JsonVariantConst doc);
bool enabled();
// Bunyi penanda.
void cue(Cue c);
// Putar pesan status tersimpan (nama dari server, mis. "wifi"); bila belum terunduh, bunyi
// penanda `fallback`. Berhenti bila tombol ditekan.
void say(const char *name, Cue fallback = Cue::Error);
// Unduh satu pesan yang belum ada atau sudah usang; dipanggil saat menganggur.
void loadPending();

}  // namespace voice
