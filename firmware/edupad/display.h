// Tampilan LCD 480x320 (landscape). Semua layar punya bilah status di atas.
#pragma once

#include <ArduinoJson.h>

namespace display {

void begin();
// Teks kanan bilah status, mis. "WiFi -58 dBm" atau "Offline".
void setStatus(const char *text);
// Layar sederhana: judul + hingga dua baris keterangan di tengah.
void message(const char *title, const char *line1 = nullptr, const char *line2 = nullptr,
             uint16_t color = 0xFFFF);
void idle(bool newSession);
// Petunjuk hotspot pengaturan Wi-Fi. `failed`: jaringan yang gagal disambung.
void portal(const char *apSsid, const char *apPassword, const char *ip, const char *failed);
// Dipanggil berulang selama merekam; hanya bagian yang berubah yang digambar ulang.
void recording(uint32_t elapsedMs, float levelDbfs);
void processing(uint32_t elapsedMs);
// `screen` dari jawaban /v1/ask: {title, title_size, lines[]}. `question` boleh kosong.
void answer(JsonObjectConst screen, const char *question);

}  // namespace display
