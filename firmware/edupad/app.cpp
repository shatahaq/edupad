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

bool newSession = false;  // ?new=1 pada pertanyaan berikutnya
uint32_t lastWifiCheckMs = 0;
String lastAnswer;  // JSON jawaban terakhir, untuk ditampilkan lagi saat putar ulang

// Hasil satu kali tombol ditekan.
struct Press {
  bool tap = false;    // tekan singkat (bukan rekaman)
  bool shown = false;  // layar rekam sempat tampil (tombol ditahan > 250 ms)
  String audioPath;    // suara yang perlu diputar, kosong bila tidak ada
};

uint32_t lastActivityMs = 0;  // akhir interaksi terakhir; tertidur setelah SLEEP_AFTER_MS
bool asleep = false;
uint32_t asleepSinceMs = 0;
bool powerSaving = false;

// Hemat daya saat tidur: Wi-Fi modem sleep (tetap tersambung) dan prosesor 80 MHz. Selalu
// dimatikan dulu sebelum EduPad melakukan hal lain (bangun, bertanya, pemberitahuan).
void powerSave(bool on) {
  if (!SLEEP_POWER_SAVE || on == powerSaving) return;
  powerSaving = on;
  if (on) {
    WiFi.setSleep(true);
    setCpuFrequencyMhz(80);
  } else {
    setCpuFrequencyMhz(240);
    WiFi.setSleep(false);
  }
  Serial.printf("[power] hemat daya %s\n", on ? "aktif" : "mati");
}

bool buttonDown() { return digitalRead(PIN_BUTTON) == LOW; }

void waitRelease() {
  while (buttonDown()) delay(10);
  delay(30);  // pantulan tombol
}

// Beri tahu layar bila Wi-Fi terputus (layar siap menampilkan peringatan).
void checkWifi(bool force = false) {
  if (!force && millis() - lastWifiCheckMs < 1000) return;
  lastWifiCheckMs = millis();
  display::setOnline(WiFi.status() == WL_CONNECTED);
}

// Tampilkan jawaban /v1/ask; mengembalikan audio_url (kosong bila tidak ada suara).
String showResponse(const api::Response &res) {
  if (res.status == 0) {
    Serial.printf("[ask] gagal: %s\n", res.error.c_str());
    display::message("Gagal terhubung", res.error.c_str(), "Tahan tombol untuk mencoba lagi", display::Tone::Error);
    return "";
  }
  if (res.status == 401) {  // layar dari server hanya "sedang ada gangguan"
    display::message("Token perangkat salah", "Samakan EDUPAD_DEVICE_TOKEN di secrets.h", "dan .env server", display::Tone::Error);
    return "";
  }
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, res.body);
  if (err || !doc["screen"].is<JsonObjectConst>()) {
    Serial.printf("[ask] HTTP %d, JSON tidak valid (%s): %.200s\n", res.status, err.c_str(),
                  res.body.c_str());
    display::message("Jawaban tidak valid", "Lihat Serial Monitor", nullptr, display::Tone::Error);
    return "";
  }
  const char *status = doc["status"] | "";
  Serial.printf("[ask] HTTP %d %s | stt %.2fs agent %.2fs | %s\n", res.status, status,
                doc["timing"]["stt"] | 0.0f, doc["timing"]["agent"] | 0.0f,
                doc["question"] | "");
  if (doc["error"].is<const char *>()) Serial.printf("[ask] error: %s\n", doc["error"].as<const char *>());
  display::answer(doc["screen"], doc["question"] | "", status);
  if (strcmp(status, "ok") != 0) return "";
  newSession = false;
  lastAnswer = res.body;
  return doc["audio_url"] | "";
}

// Putar suara; true bila dihentikan karena tombol ditekan (tombol masih tertahan).
bool play(const String &path, bool replay) {
  display::speaking(true);
  api::AudioResult r = api::streamAudio(path.c_str(), [](const uint8_t *pcm, size_t size) {
    if (buttonDown()) return false;
    speaker::write(pcm, size);
    display::voice(speaker::level(), speaker::positionMs());  // gerak paruh + teks perkenalan
    return true;
  });
  if (r.stopped) {
    speaker::stop();
  } else {
    speaker::finish();
  }
  display::speaking(false);
  Serial.printf("[audio] %s HTTP %d, %u byte%s %s\n", path.c_str(), r.status, (unsigned)r.bytes,
                r.stopped ? " (dihentikan)" : "", r.error.c_str());
  if (replay && r.status == 404) {
    display::message("Belum ada suara", "Tanyakan sesuatu dulu:", "tahan tombol lalu bicara", display::Tone::Warn);
  } else if (!r.stopped && !r.complete) {
    display::toast("Suara gagal diputar");
  }
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
    press.shown = shown;
    if (shown && !lastAnswer.isEmpty()) {
      // layar rekam sempat muncul: kembalikan jawaban terakhir
      JsonDocument doc;
      if (!deserializeJson(doc, lastAnswer)) display::answer(doc["screen"], doc["question"] | "", "ok");
    } else if (shown) {
      display::idle(newSession);
    }
    return press;
  }
  if (!ok) {
    api::Response res = api::askSalvage();
    if (res.status != 0) {
      showResponse(res);
      waitRelease();
      return press;
    }
    Serial.printf("[ask] gagal: %s\n", error.c_str());
    display::message("Gagal mengirim", error.c_str(), "Tahan tombol untuk mencoba lagi", display::Tone::Error);
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
  waitRelease();  // bila rekaman berhenti karena MAX_RECORD_MS
  return press;
}

// Perkenalan diri setelah menyala: kalimat + gerakan dari /v1/intro, suaranya disimpan server
// (tidak memakai kuota TTS). Tombol menghentikannya; bila terus ditahan, langsung merekam.
void introduce() {
  api::Response res = api::get("/v1/intro", 30000);  // pertama kali server membuat suaranya dulu
  JsonDocument doc;
  if (res.status != 200 || deserializeJson(doc, res.body)) {
    Serial.printf("[intro] dilewati: HTTP %d %s\n", res.status, res.error.c_str());
    return;
  }
  display::intro(doc["segments"], doc["duration"] | 0.0f);
  if (!play(doc["audio_url"] | "/v1/intro/audio", false)) delay(800);  // biarkan confetti selesai
}

// ---- Kabar dari server (/v1/updates): kuliah berikutnya + pemberitahuan presensi/deadline

uint32_t lastUpdatesMs = 0;
String shownAlerts[16];  // id pemberitahuan yang sudah tampil, supaya tidak diulang
uint8_t shownNext = 0;

bool alertShown(const char *id) {
  for (const String &s : shownAlerts)
    if (s == id) return true;
  return false;
}

// Satu pemberitahuan sampai waktunya habis atau tombol ditekan. true bila tombol masih ditahan
// (pengguna langsung ingin bertanya); tekan singkat hanya menutup.
bool showAlert(JsonObjectConst alert) {
  const char *kind = alert["kind"] | "";
  bool attendance = !strcmp(kind, "attendance");
  display::alert(alert);
  if (attendance) speaker::chime();
  uint32_t duration = attendance                 ? ALERT_ATTENDANCE_MS
                      : !strcmp(kind, "deadline") ? ALERT_DEADLINE_MS
                      : !strcmp(kind, "warning")  ? ALERT_WARNING_MS
                      : !strcmp(kind, "review")   ? ALERT_REVIEW_MS
                                                  : ALERT_ATTENDED_MS;
  for (uint32_t start = millis(); millis() - start < duration; delay(20)) {
    if (!buttonDown()) continue;
    for (uint32_t pressed = millis(); buttonDown() && millis() - pressed < SHORT_PRESS_MS;) delay(10);
    if (buttonDown()) return true;
    delay(30);  // pantulan tombol
    return false;
  }
  return false;
}

void checkUpdates(bool force = false) {
  if (!force && millis() - lastUpdatesMs < UPDATES_EVERY_MS) return;
  lastUpdatesMs = millis();
  if (WiFi.status() != WL_CONNECTED) return;
  api::Response res = api::get("/v1/updates", 10000);
  JsonDocument doc;
  if (res.status != 200 || deserializeJson(doc, res.body)) {
    Serial.printf("[updates] gagal: HTTP %d %s\n", res.status, res.error.c_str());
    return;
  }
  display::clock(doc["now_ts"] | 0);
  display::schedule(doc["next_class"].as<JsonObjectConst>(), doc["stale"].as<JsonArrayConst>());

  // Saat tidur hanya presensi yang dibuka yang membangunkan; pemberitahuan lain menunggu
  // sampai bangun (tidak ditandai tampil, jadi muncul pada pengecekan berikutnya).
  bool shown = false, held = false;
  for (JsonObjectConst alert : doc["alerts"].as<JsonArrayConst>()) {
    const char *id = alert["id"] | "";
    if (!*id || alertShown(id)) continue;
    if (asleep && strcmp(alert["kind"] | "", "attendance") != 0) continue;
    asleep = false;
    powerSave(false);
    shownAlerts[shownNext++ % 16] = id;
    shown = true;
    Serial.printf("[updates] pemberitahuan %s\n", id);
    if ((held = showAlert(alert))) break;
  }
  if (shown) {
    if (!held) display::idle(newSession);
    lastActivityMs = millis();
  }
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
    if (!deserializeJson(doc, lastAnswer)) display::answer(doc["screen"], doc["question"] | "", "ok");
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

  display::bootStep("Menyalakan mikrofon", 0.15f);
  if (!mic::begin()) {
    Serial.println("[mic] I2S gagal dimulai");
    display::message("Mikrofon gagal", "Periksa kabel INMP441", nullptr, display::Tone::Error);
    while (true) delay(1000);
  }
  if (!speaker::begin()) {
    Serial.println("[speaker] I2S gagal dimulai");
    display::message("Speaker gagal", "Periksa kabel MAX98357A", nullptr, display::Tone::Error);
    while (true) delay(1000);
  }

  Serial.printf("[mem] heap bebas %u, blok terbesar %u, PSRAM %u\n", (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getMaxAllocHeap(), (unsigned)ESP.getPsramSize());
  api::begin();
  bool online = wifisetup::connect([](const char *ssid) {
    char text[48];
    snprintf(text, sizeof text, "Menyambung ke %s", ssid);
    display::bootStep(text, 0.45f);
  });
  if (!online) wifisetup::runPortal();  // restart setelah Wi-Fi dipilih
  checkWifi(true);
  Serial.printf("[wifi] %s, IP %s\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());

  display::bootStep("Menghubungi server", 0.8f);
  api::Response res = api::health();
  if (res.status == 200) {
    display::bootDone();
    if (INTRO_ON_BOOT) introduce();
    display::idle(false);
    checkUpdates(true);
  } else {
    Serial.printf("[api] health: HTTP %d %s\n", res.status, res.error.c_str());
    display::message("Server tidak terjangkau", res.status ? "Jawaban server tidak normal" : res.error.c_str(),
                     "Tetap bisa dicoba: tahan tombol", display::Tone::Warn);
  }
  lastActivityMs = millis();
}

void loop() {
  checkWifi();
  checkUpdates();
  delay(10);
  if (!asleep && millis() - lastActivityMs > SLEEP_AFTER_MS) {
    asleep = true;
    asleepSinceMs = millis();
    display::sleep();
  }
  if (asleep && millis() - asleepSinceMs > SLEEP_POWER_SAVE_AFTER_MS) powerSave(true);
  if (!buttonDown()) return;
  delay(20);  // pantulan tombol
  if (!buttonDown()) return;

  // Saat tidur, tombol membangunkan dulu. Bila terus ditahan, rekaman tetap langsung mulai
  // (animasi bangun berlanjut di layar mendengarkan); tekan singkat hanya membangunkan.
  bool woke = asleep;
  if (asleep) {
    asleep = false;
    powerSave(false);
    display::wake();
    lastUpdatesMs = 0;  // pemberitahuan yang tertunda selama tidur dicek setelah ini
  }
  Press press = ask();
  if (press.tap && woke) {
    if (press.shown) display::idle(newSession);  // kembali ke layar siap, animasi bangun berlanjut
    lastActivityMs = millis();
    return;
  }
  if (press.tap) {
    if (secondTap()) {
      newSession = true;
      display::idle(true);
      lastActivityMs = millis();
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
  lastActivityMs = millis();
}

}  // namespace app
