// EduPad: tahan tombol BOOT, bicara, lepas -> jawaban tampil di LCD lalu dibacakan lewat speaker.
// Rekaman dikirim ke POST /v1/ask sambil merekam (chunked); suara jawaban (audio_url) diambil
// lewat koneksi yang sama dan diputar begitu tiba. Tekan 1x = putar ulang (server memakai
// suara tersimpan, tanpa kuota TTS), tekan 2x = percakapan baru, tekan saat bicara = berhenti.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>

#include "api.h"
#include "app.h"
#include "config.h"
#include "display.h"
#include "mic.h"
#include "secrets.h"
#include "speaker.h"
#include "wifi_setup.h"

namespace {

constexpr uint16_t RED = 0xF8A2;
constexpr uint16_t YELLOW = 0xFEA0;

bool newSession = false;  // ?new=1 pada pertanyaan berikutnya
uint32_t lastStatusMs = 0;
String lastAnswer;  // JSON jawaban terakhir, untuk ditampilkan lagi saat putar ulang

// Hasil satu kali tombol ditekan.
struct Press {
  bool tap = false;  // tekan singkat (bukan rekaman)
  String audioPath;  // suara yang perlu diputar, kosong bila tidak ada
};

bool buttonDown() { return digitalRead(PIN_BUTTON) == LOW; }

void waitRelease() {
  while (buttonDown()) delay(10);
  delay(30);  // pantulan tombol
}

void updateStatus(bool force = false) {
  if (!force && millis() - lastStatusMs < 3000) return;
  lastStatusMs = millis();
  char text[40];
  if (WiFi.status() == WL_CONNECTED) {
    snprintf(text, sizeof text, "%sWiFi %d dBm", newSession ? "Sesi baru | " : "", WiFi.RSSI());
  } else {
    snprintf(text, sizeof text, "Offline");
  }
  display::setStatus(text);
}

// Tampilkan jawaban /v1/ask; mengembalikan audio_url (kosong bila tidak ada suara).
String showResponse(const api::Response &res) {
  if (res.status == 0) {
    Serial.printf("[ask] gagal: %s\n", res.error.c_str());
    display::message("Gagal terhubung", res.error.c_str(), "Tahan BOOT untuk mencoba lagi", RED);
    return "";
  }
  if (res.status == 401) {  // layar dari server hanya "sedang ada gangguan"
    display::message("Token perangkat salah", "Samakan EDUPAD_DEVICE_TOKEN di", "secrets.h dan .env server", RED);
    return "";
  }
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, res.body);
  if (err || !doc["screen"].is<JsonObjectConst>()) {
    Serial.printf("[ask] HTTP %d, JSON tidak valid (%s): %.200s\n", res.status, err.c_str(),
                  res.body.c_str());
    display::message("Jawaban tidak valid", "Lihat Serial monitor", nullptr, RED);
    return "";
  }
  const char *status = doc["status"] | "";
  Serial.printf("[ask] HTTP %d %s | stt %.2fs agent %.2fs | %s\n", res.status, status,
                doc["timing"]["stt"] | 0.0f, doc["timing"]["agent"] | 0.0f,
                doc["question"] | "");
  if (doc["error"].is<const char *>()) Serial.printf("[ask] error: %s\n", doc["error"].as<const char *>());
  display::answer(doc["screen"], doc["question"] | "");
  if (strcmp(status, "ok") != 0) return "";
  newSession = false;
  lastAnswer = res.body;
  return doc["audio_url"] | "";
}

// Putar suara; true bila dihentikan karena tombol ditekan (tombol masih tertahan).
bool play(const String &path, bool replay) {
  display::setStatus("Memutar suara...");
  api::AudioResult r = api::streamAudio(path.c_str(), [](const uint8_t *pcm, size_t size) {
    if (buttonDown()) return false;
    speaker::write(pcm, size);
    return true;
  });
  if (r.stopped) {
    speaker::stop();
  } else {
    speaker::finish();
  }
  Serial.printf("[audio] %s HTTP %d, %u byte%s %s\n", path.c_str(), r.status, (unsigned)r.bytes,
                r.stopped ? " (dihentikan)" : "", r.error.c_str());
  if (replay && r.status == 404) {
    display::message("Belum ada suara", "Tanyakan sesuatu dulu:", "tahan BOOT lalu bicara", YELLOW);
  } else if (!r.stopped && !r.complete) {
    display::setStatus("Suara gagal diputar");
    lastStatusMs = millis();  // biarkan pesan terlihat beberapa detik
    return false;
  }
  updateStatus(true);
  return r.stopped;
}

Press ask() {
  uint32_t pressedAt = millis();
  mic::start();
  bool shown = false;  // layar rekam ditunda supaya tekan singkat tidak membuatnya berkedip

  bool opened = false, ok = false;
  String error;
  static uint8_t chunk[4096];
  uint32_t held = 0;
  while (buttonDown() && (held = millis() - pressedAt) < MAX_RECORD_MS) {
    // Koneksi baru dibuka setelah jelas bukan tekan singkat; selama TLS tersambung
    // (~0,5-2 s) rekaman tetap tertampung di mic.
    if (!opened && held >= SHORT_PRESS_MS) {
      opened = true;
      if (WiFi.status() != WL_CONNECTED) {
        error = "Wi-Fi terputus";
      } else {
        ok = api::askOpen(newSession, error);
      }
      if (!ok) break;
    }
    if (ok && mic::available() >= 2048) {
      size_t n = mic::read(chunk, sizeof chunk, 0);
      if (!api::askWrite(chunk, n)) {
        ok = false;
        error = "koneksi terputus saat mengirim";
        break;
      }
    }
    if (held >= 250) {
      display::recording(held, mic::levelDbfs());
      shown = true;
    }
    delay(10);
  }
  held = millis() - pressedAt;
  mic::stop();

  Press press;
  if (!opened) {
    press.tap = true;
    if (shown && !lastAnswer.isEmpty()) {
      // layar rekam sempat muncul: kembalikan jawaban terakhir
      JsonDocument doc;
      if (!deserializeJson(doc, lastAnswer)) display::answer(doc["screen"], doc["question"] | "");
    } else if (shown) {
      display::idle(newSession);
    }
    return press;
  }
  if (!ok) {
    api::Response res = api::askSalvage();
    if (res.status != 0) {
      showResponse(res);
      updateStatus(true);
      waitRelease();
      return press;
    }
    Serial.printf("[ask] gagal: %s\n", error.c_str());
    display::message("Gagal mengirim", error.c_str(), "Tahan BOOT untuk mencoba lagi", RED);
    waitRelease();
    return press;
  }

  size_t n;
  while ((n = mic::read(chunk, sizeof chunk, 0)) > 0) {
    if (!api::askWrite(chunk, n)) break;
  }
  if (mic::droppedBytes()) {
    Serial.printf("[mic] %lu byte rekaman terbuang (koneksi lambat)\n",
                  (unsigned long)mic::droppedBytes());
  }
  Serial.printf("[ask] rekaman %.1f s terkirim\n", held / 1000.0f);

  display::processing(0);
  api::Response res = api::askFinish(display::processing);
  press.audioPath = showResponse(res);
  updateStatus(true);
  waitRelease();  // bila rekaman berhenti karena MAX_RECORD_MS
  return press;
}

// Setelah satu tekan singkat: tunggu tekan kedua sebentar.
bool secondTap() {
  for (uint32_t started = millis(); millis() - started < DOUBLE_TAP_MS;) {
    if (buttonDown()) {
      waitRelease();
      return true;
    }
    delay(5);
  }
  return false;
}

// Putar ulang suara jawaban terakhir (server mengambilnya dari simpanan, tanpa kuota TTS).
Press replay() {
  if (!lastAnswer.isEmpty()) {
    JsonDocument doc;
    if (!deserializeJson(doc, lastAnswer)) display::answer(doc["screen"], doc["question"] | "");
  }
  Press press;
  press.audioPath = "/v1/audio/latest";
  return press;
}

}  // namespace

namespace app {

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  display::begin();

  display::message("EduPad", "Menyalakan mikrofon...");
  if (!mic::begin()) {
    Serial.println("[mic] I2S gagal dimulai");
    display::message("Mikrofon gagal", "Periksa kabel INMP441", nullptr, RED);
    while (true) delay(1000);
  }
  if (!speaker::begin()) {
    Serial.println("[speaker] I2S gagal dimulai");
    display::message("Speaker gagal", "Periksa kabel MAX98357A", nullptr, RED);
    while (true) delay(1000);
  }

  api::begin();
  bool online = wifisetup::connect(
      [](const char *ssid) { display::message("EduPad", "Menyambung Wi-Fi", ssid); });
  if (!online) wifisetup::runPortal();  // restart setelah Wi-Fi dipilih
  updateStatus(true);
  Serial.printf("[wifi] %s, IP %s\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());

  display::message("EduPad", "Menghubungi server", EDUPAD_HOST);
  api::Response res = api::health();
  if (res.status == 200) {
    display::idle(false);
  } else {
    Serial.printf("[api] health: HTTP %d %s\n", res.status, res.error.c_str());
    display::message("Server tidak terjangkau", res.status ? "Jawaban server tidak normal" : res.error.c_str(),
                     "Tetap bisa dicoba: tahan BOOT", YELLOW);
  }
}

void loop() {
  updateStatus();
  delay(10);
  if (!buttonDown()) return;
  delay(20);  // pantulan tombol
  if (!buttonDown()) return;

  Press press = ask();
  if (press.tap) {
    if (secondTap()) {
      newSession = true;
      display::idle(true);
      updateStatus(true);
      return;
    }
    press = replay();
  }
  // Tombol ditekan saat suara diputar: berhenti; bila terus ditahan, langsung merekam.
  bool replaying = press.audioPath == "/v1/audio/latest";
  while (!press.audioPath.isEmpty() && play(press.audioPath, replaying)) {
    press = ask();  // tekan singkat di sini hanya menghentikan suara
    replaying = false;
  }
}

}  // namespace app
