#include "voice.h"

#include <Preferences.h>
#include <WiFi.h>
#include <esp_heap_caps.h>

#include "api.h"
#include "config.h"
#include "speaker.h"

namespace {

// Nama sama dengan server (voice/clips.py CLIPS).
struct Clip {
  const char *name;
  String url;        // alamat terbaru dari server (?v= berganti bila suaranya berubah)
  String loadedUrl;  // alamat yang isinya sudah ada di `pcm`
  uint8_t *pcm = nullptr;  // PCM di PSRAM; hilang saat perangkat dimatikan, diunduh lagi saat menyala
  size_t size = 0;
  uint32_t retryAt = 0;
};

Clip clips[] = {{"ready"},     {"wifi"},  {"send"},      {"server"},     {"error"},
                {"no_speech"}, {"audio"}, {"no_answer"}, {"new_session"}};

bool on = false;

// Tujuan unduhan untuk sink streamAudio (fungsi biasa, tanpa capture).
Clip *target = nullptr;
size_t received = 0;

bool collect(const uint8_t *data, size_t size) {
  size_t take = min(size, (size_t)VOICE_CLIP_MAX_BYTES - received);
  memcpy(target->pcm + received, data, take);
  received += take;
  return true;  // sisa yang tidak muat dibuang, unduhan tetap dituntaskan
}

void save(bool value) {
  Preferences prefs;
  if (!prefs.begin("voice", false)) return;
  prefs.putBool("on", value);
  prefs.end();
}

}  // namespace

namespace voice {

void begin() {
  Preferences prefs;
  if (prefs.begin("voice", true)) {  // false bila belum pernah disimpan
    on = prefs.getBool("on", false);
    prefs.end();
  }
}

void update(JsonVariantConst doc) {
  JsonVariantConst mode = doc["voice_mode"];
  if (mode.is<bool>() && mode.as<bool>() != on) {
    on = mode.as<bool>();
    save(on);
    Serial.printf("[voice] Mode Suara %s\n", on ? "aktif" : "mati");
  }
  JsonObjectConst urls = doc["voice_clips"];
  if (urls.isNull()) return;
  for (Clip &c : clips) {
    const char *url = urls[c.name] | "";
    if (*url) c.url = url;
  }
}

bool enabled() { return on; }

void cue(Cue c) {
  if (!on) return;
  switch (c) {
    case Cue::Listen:  // naik: mulai merekam, silakan bicara
      speaker::tone(880, 70);
      speaker::tone(1320, 90);
      break;
    case Cue::Sent:  // turun: rekaman selesai dan terkirim
      speaker::tone(1320, 70);
      speaker::tone(880, 90);
      break;
    case Cue::Thinking:  // ketukan pelan berkala: server masih memproses
      speaker::tone(660, 40, 0.12f);
      break;
    case Cue::Error:
      speaker::tone(392, 130);
      delay(40);
      speaker::tone(262, 200);
      break;
    case Cue::Wake:
      speaker::tone(988, 60, 0.2f);
      break;
  }
}

void say(const char *name, Cue fallback) {
  if (!on) return;
  for (Clip &c : clips) {
    if (strcmp(c.name, name) != 0) continue;
    if (!c.size) break;
    for (size_t at = 0; at < c.size; at += 2048) {
      if (digitalRead(PIN_BUTTON) == LOW) {  // pengguna ingin langsung bertanya
        speaker::stop();
        return;
      }
      speaker::write(c.pcm + at, min((size_t)2048, c.size - at));
    }
    speaker::finish();
    return;
  }
  cue(fallback);  // pesan belum terunduh (mis. baru menyala tanpa server)
}

void loadPending() {
  if (!on || WiFi.status() != WL_CONNECTED) return;
  for (Clip &c : clips) {
    if (c.url.isEmpty() || c.url == c.loadedUrl || (int32_t)(millis() - c.retryAt) < 0) continue;
    if (!c.pcm) {
      c.pcm = (uint8_t *)heap_caps_malloc(VOICE_CLIP_MAX_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
      if (!c.pcm) {
        Serial.println("[voice] PSRAM tidak cukup untuk pesan suara");
        c.retryAt = millis() + VOICE_RETRY_MS;
        return;
      }
    }
    c.size = 0;  // isi lama tertimpa selama mengunduh: jangan diputar sampai selesai
    target = &c;
    received = 0;
    api::AudioResult r = api::streamAudio(c.url.c_str(), collect);
    if (r.status == 200 && r.complete) {
      c.size = received - received % 2;
      c.loadedUrl = c.url;
      Serial.printf("[voice] pesan %s siap (%u byte)\n", c.name, (unsigned)c.size);
    } else {
      c.retryAt = millis() + VOICE_RETRY_MS;
      Serial.printf("[voice] pesan %s gagal diunduh: HTTP %d %s\n", c.name, r.status, r.error.c_str());
    }
    return;  // satu pesan per panggilan supaya tombol tetap cepat ditanggapi
  }
}

}  // namespace voice
