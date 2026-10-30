// Bahasa layar: mengikuti setelan server (`language` di /v1/updates dan /v1/ask, voice/lang.py).
// Disimpan di flash supaya layar nyala dan pesan galat sebelum server terhubung juga ikut.
#pragma once

#include <ArduinoJson.h>

namespace lang {

void begin();
// Baca `language` ("id"/"en") dari jawaban server; disimpan bila berubah.
void update(JsonVariantConst doc);
bool english();
// Teks sesuai bahasa yang aktif.
inline const char *tr(const char *id, const char *en) { return english() ? en : id; }

}  // namespace lang
