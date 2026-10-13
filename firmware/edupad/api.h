// Klien API perangkat EduPad (deploy/DEVICE_API.md). Satu koneksi pada satu waktu; koneksi
// /v1/ask dibiarkan terbuka (keep-alive) agar audio jawaban diambil tanpa jabat tangan TLS lagi.
#pragma once

#include <Arduino.h>

namespace api {

struct Response {
  int status = 0;  // 0 = gagal di jaringan, lihat `error`
  String body;
  String error;
};

void begin();
Response health();

// POST /v1/ask dikirim sambil merekam: askOpen -> askWrite berulang -> askFinish.
bool askOpen(bool newSession, String &error);
bool askWrite(const uint8_t *pcm, size_t size);
// `waiting(ms)` dipanggil berkala selama menunggu jawaban (untuk layar).
Response askFinish(void (*waiting)(uint32_t elapsedMs));
// Setelah askWrite gagal: server mungkin sudah menjawab lebih dulu (mis. 401 token salah).
Response askSalvage();

struct AudioResult {
  int status = 0;     // 0 = gagal di jaringan
  bool complete = false;
  bool stopped = false;  // `sink` meminta berhenti (tombol ditekan)
  size_t bytes = 0;
  String error;
};
// GET audio (mis. audio_url atau /v1/audio/latest); setiap potongan PCM diberikan ke `sink`
// begitu tiba. `sink` mengembalikan false untuk berhenti.
AudioResult streamAudio(const char *path, bool (*sink)(const uint8_t *pcm, size_t size));

}  // namespace api
