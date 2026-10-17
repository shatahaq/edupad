#include "display.h"

#include <LovyanGFX.hpp>

#include "config.h"
#include "scene.h"
#include "sound_cues.h"
#include "speaker.h"

namespace {

class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_ST7796 panel_;
  lgfx::Bus_SPI bus_;
  lgfx::Light_PWM light_;

 public:
  LGFX() {
    auto bus = bus_.config();
    bus.spi_host = SPI2_HOST;
    bus.spi_mode = 0;
    bus.freq_write = TFT_SPI_HZ;
    bus.freq_read = 16000000;
    bus.spi_3wire = false;
    bus.use_lock = true;
    bus.dma_channel = SPI_DMA_CH_AUTO;
    bus.pin_sclk = PIN_TFT_SCLK;
    bus.pin_mosi = PIN_TFT_MOSI;
    bus.pin_miso = PIN_TFT_MISO;
    bus.pin_dc = PIN_TFT_DC;
    bus_.config(bus);
    panel_.setBus(&bus_);

    auto panel = panel_.config();
    panel.pin_cs = PIN_TFT_CS;
    panel.pin_rst = PIN_TFT_RST;
    panel.pin_busy = -1;
    panel.panel_width = 320;
    panel.panel_height = 480;
    panel.readable = PIN_TFT_MISO >= 0;
    panel.invert = TFT_INVERT;
    panel.rgb_order = TFT_BGR;
    panel.bus_shared = false;
    panel_.config(panel);

#if PIN_TFT_BL >= 0
    auto light = light_.config();
    light.pin_bl = PIN_TFT_BL;
    light.invert = false;
    light.freq = 12000;
    light.pwm_channel = 7;
    light_.config(light);
    panel_.setLight(&light_);
#endif
    setPanel(&panel_);
  }
};

LGFX tft;
LGFX_Sprite canvas(&tft);  // seluruh layar di PSRAM; tiap frame hanya area yang berubah dikirim

// Data layar yang dibagi dengan task gambar; semua akses lewat `lock`.
SemaphoreHandle_t lock = nullptr;
scene::Ui shared;
uint32_t generation = 0;  // naik bila layar harus digambar penuh (ganti layar, toast, dsb.)
uint32_t sceneStartMs = 0;
float rawLevel = -90;  // mikrofon
float rawVoice = -90;  // suara yang diputar
uint32_t lastLoudMs = 0;
float bootTarget = 0.05f;
uint32_t bootDoneAt = 0;  // millis() saat siap, 0 = belum
uint32_t toastAt = 0;     // millis() saat toast muncul, 0 = tidak ada
uint32_t wakeAt = 0;      // millis() saat dibangunkan dari tidur, 0 = tidak
uint32_t clockTs = 0, clockMs = 0;  // jam dari server: detik epoch pada millis() clockMs
bool running = false;

template <typename F>
void update(F change) {
  if (!running) return;
  xSemaphoreTake(lock, portMAX_DELAY);
  change();
  xSemaphoreGive(lock);
}

// Ganti layar (di dalam update): animasinya mulai dari awal dan digambar penuh.
void show(scene::Kind kind) {
  shared.kind = kind;
  sceneStartMs = millis();
  generation++;
}

void copy(char *dst, size_t size, const char *src) { strlcpy(dst, src ? src : "", size); }

void pushArea(const scene::Rect &r) {
  tft.setClipRect(r.x, r.y, r.w, r.h);
  canvas.pushSprite(0, 0);
  tft.clearClipRect();
}

// Kecerahan lampu layar: redup saat tidur (hemat baterai), terang di layar lain.
constexpr int BRIGHT_FULL = 255, BRIGHT_SLEEP = 40;

void uiTask(void *) {
  static scene::Ui ui;
  uint32_t seen = 0, last = millis(), cuedStart = 0, cuedDone = 0;
  float progress = 0, level = -90, voiced = -90, bright = BRIGHT_FULL;
  int shownBright = BRIGHT_FULL;
  for (;;) {
    uint32_t now = millis();
    float dt = (now - last) / 1000.0f;
    last = now;

    xSemaphoreTake(lock, portMAX_DELAY);
    if (toastAt && now - toastAt > (uint32_t)(scene::TOAST_SECONDS * 1000)) {
      shared.toast[0] = 0;
      toastAt = 0;
      generation++;  // gambar ulang bagian yang tertutup toast
    }
    ui = shared;
    bool full = generation != seen;
    seen = generation;
    uint32_t start = sceneStartMs, loud = lastLoudMs, doneAt = bootDoneAt, shownAt = toastAt, woke = wakeAt;
    uint32_t baseTs = clockTs, baseMs = clockMs;
    float raw = rawLevel, target = bootTarget, spoken = rawVoice;
    xSemaphoreGive(lock);

    ui.t = (now - start) / 1000.0f;
    progress += (target - progress) * (1 - expf(-dt * 5));
    ui.progress = progress;
    ui.done = doneAt ? (now - doneAt) / 1000.0f : -1;
    level += (raw - level) * (1 - expf(-dt * (raw > level ? 30 : 6)));  // naik cepat, turun pelan
    ui.level = level;
    voiced += (spoken - voiced) * (1 - expf(-dt * (spoken > voiced ? 40 : 12)));
    ui.voice = voiced;
    ui.quiet = (now - loud) / 1000.0f;
    ui.toastT = shownAt ? (now - shownAt) / 1000.0f : -1;
    ui.wake = woke ? (now - woke) / 1000.0f : -1;
    ui.nowTs = baseTs ? baseTs + (now - baseMs) / 1000 : 0;

    // efek suara yang mengiringi layar baru / boot selesai (sound_cues.h), selaras dengan animasi
    if (start != cuedStart) {
      cuedStart = start;
      cues::List list = cues::forScreen(ui);
      speaker::effects(list.items, list.count, list.fromWake ? woke : start);
    }
    if (doneAt && doneAt != cuedDone) {
      cuedDone = doneAt;
      cues::List list = cues::bootDone(INTRO_ON_BOOT);
      speaker::effects(list.items, list.count, doneAt);
    }

    // tidur: setelah tertidur lampu meredup pelan dan gambar cukup 15 fps; bangun: terang cepat
    bool dozing = ui.kind == scene::Kind::Sleep && ui.t > scene::SLEEP_SETTLE_SECONDS;
    float wanted = dozing ? BRIGHT_SLEEP : BRIGHT_FULL;
    bright = wanted < bright ? fmaxf(wanted, bright - 120 * dt) : fminf(wanted, bright + 1500 * dt);
    if ((int)bright != shownBright) {
      shownBright = (int)bright;
      tft.setBrightness(shownBright);
    }

    scene::render(canvas, ui, full, pushArea);
    uint32_t frameMs = dozing ? 66 : 33, spent = millis() - now;
    vTaskDelay(pdMS_TO_TICKS(spent < frameMs ? frameMs - spent : 1));
  }
}

scene::Gesture gestureNamed(const char *name) {
  static const struct {
    const char *name;
    scene::Gesture gesture;
  } names[] = {{"wave", scene::Gesture::Wave},   {"happy", scene::Gesture::Happy},
               {"book", scene::Gesture::Book},   {"tasks", scene::Gesture::Tasks},
               {"button", scene::Gesture::Button}, {"cheer", scene::Gesture::Cheer}};
  for (const auto &n : names)
    if (strcmp(name, n.name) == 0) return n.gesture;
  return scene::Gesture::Talk;
}

// Satu butir jawaban server untuk layar pesan: buang "- " dan gabungkan baris lanjutan.
uint8_t noticeLines(JsonArrayConst lines, char (*out)[48], uint8_t max) {
  uint8_t n = 0;
  for (JsonVariantConst v : lines) {
    const char *l = v | "";
    bool more = l[0] == ' ' && l[1] == ' ';
    while (*l == ' ') l++;
    if (l[0] == '-' && l[1] == ' ') l += 2;
    if (!*l) continue;
    if (more && n > 0) {
      size_t len = strlen(out[n - 1]);
      snprintf(out[n - 1] + len, 48 - len, " %s", l);
    } else if (n < max) {
      strlcpy(out[n++], l, 48);
    }
  }
  return n;
}

}  // namespace

namespace display {

void begin() {
  tft.init();
  tft.setRotation(1);  // landscape, konektor di kiri; 3 untuk sebaliknya
  tft.setBrightness(255);
  tft.fillScreen(TFT_BLACK);
  canvas.setColorDepth(16);
  canvas.setPsram(true);
  if (!canvas.createSprite(scene::W, scene::H)) {
    Serial.println("[lcd] kanvas 300 KB gagal dibuat: aktifkan PSRAM (Tools -> PSRAM -> OPI PSRAM)");
    tft.setTextColor(TFT_WHITE);
    tft.setTextDatum(middle_center);
    tft.setFont(&fonts::FreeSansBold12pt7b);
    tft.drawString("Aktifkan PSRAM (OPI PSRAM)", scene::W / 2, scene::H / 2);
    return;
  }
  scene::begin(true);
  lock = xSemaphoreCreateMutex();
  copy(shared.status, sizeof shared.status, "Menyiapkan...");
  shared.kind = scene::Kind::Boot;
  sceneStartMs = millis();
  generation = 1;
  running = true;
  // core 0 (Wi-Fi juga di sana, dengan prioritas lebih tinggi); loop() tetap bebas di core 1
  xTaskCreatePinnedToCore(uiTask, "ui", 12288, nullptr, 1, nullptr, 0);
}

void bootStep(const char *text, float progress) {
  update([&] {
    copy(shared.status, sizeof shared.status, text);
    bootTarget = progress;
  });
}

void bootDone() {
  if (!running) return;
  update([&] {
    copy(shared.status, sizeof shared.status, "Siap!");
    bootTarget = 1;
    bootDoneAt = millis();
  });
  delay(1200);  // burung hantu melompat senang
}

void idle(bool newSession) {
  update([&] {
    show(scene::Kind::Home);
    shared.newSession = newSession;
  });
}

void sleep() {
  update([&] {
    show(scene::Kind::Sleep);
    wakeAt = 0;
  });
}

void wake() {
  update([&] {
    // Dibangunkan saat masih menguap (belum di kamar tidur): lewati bagian kaget di ranjang.
    bool inBed = shared.kind == scene::Kind::Sleep && millis() - sceneStartMs >= scene::SLEEP_ROOM_AT * 1000;
    show(scene::Kind::Home);
    wakeAt = millis() - (inBed ? 0 : (uint32_t)(scene::WAKE_ROOM_SECONDS * 1000));
  });
}

void setOnline(bool online) {
  update([&] {
    if (shared.online == online) return;
    shared.online = online;
    if (shared.kind == scene::Kind::Home) generation++;
  });
}

void recording(uint32_t elapsedMs, float levelDbfs) {
  update([&] {
    uint32_t now = millis();
    if (shared.kind != scene::Kind::Listen) {
      show(scene::Kind::Listen);
      lastLoudMs = now;
    }
    shared.elapsedMs = elapsedMs;
    rawLevel = levelDbfs;
    if (levelDbfs >= scene::SPEECH_DBFS) lastLoudMs = now;
  });
}

void processing(uint32_t elapsedMs) {
  update([&] {
    if (shared.kind != scene::Kind::Think) show(scene::Kind::Think);
    shared.elapsedMs = elapsedMs;
  });
}

void answer(JsonObjectConst screen, const char *question, const char *status) {
  update([&] {
    shared.speaking = false;
    if (strcmp(status, "no_speech") == 0) {
      show(scene::Kind::Notice);
      shared.tone = scene::Tone::Warn;
      copy(shared.title, sizeof shared.title, "Suara tidak terdengar");
      copy(shared.lines[0], sizeof shared.lines[0], "Coba bicara lebih dekat, ya.");
      copy(shared.lines[1], sizeof shared.lines[1], "Tahan tombol lalu bicara lagi");
      shared.lineCount = 2;
      return;
    }
    if (strcmp(status, "ok") != 0) {  // galat dari server: judul dan keterangannya apa adanya
      show(scene::Kind::Notice);
      shared.tone = scene::Tone::Error;
      copy(shared.title, sizeof shared.title, screen["title"] | "Ada gangguan");
      shared.lineCount = noticeLines(screen["lines"].as<JsonArrayConst>(), shared.lines, 3);
      return;
    }
    show(scene::Kind::Answer);
    copy(shared.title, sizeof shared.title, screen["title"] | "EduPad");
    copy(shared.subtitle, sizeof shared.subtitle, question);
    uint8_t n = 0;
    for (JsonVariantConst line : screen["lines"].as<JsonArrayConst>()) {
      if (n == scene::MAX_LINES) break;
      copy(shared.lines[n++], sizeof shared.lines[0], line | "");
    }
    shared.lineCount = n;
  });
}

void speaking(bool on) {
  update([&] {
    shared.speaking = on;
    if (!on) rawVoice = -90;
  });
}

void voice(float levelDbfs, uint32_t positionMs) {
  update([&] {
    rawVoice = levelDbfs;
    shared.position = positionMs / 1000.0f;
  });
}

void intro(JsonArrayConst segments, float duration) {
  update([&] {
    show(scene::Kind::Intro);
    uint8_t n = 0;
    for (JsonObjectConst seg : segments) {
      if (n == scene::MAX_SEGMENTS) break;
      shared.segStart[n] = seg["start"] | 0.0f;
      shared.segGesture[n] = gestureNamed(seg["gesture"] | "");
      copy(shared.segText[n], sizeof shared.segText[0], seg["text"] | "");
      n++;
    }
    shared.segCount = n;
    shared.duration = duration;
    shared.position = -1;
    rawVoice = -90;
  });
}

void message(const char *title, const char *line1, const char *line2, Tone tone) {
  update([&] {
    show(scene::Kind::Notice);
    shared.tone = tone == Tone::Error ? scene::Tone::Error : tone == Tone::Warn ? scene::Tone::Warn : scene::Tone::Info;
    copy(shared.title, sizeof shared.title, title);
    uint8_t n = 0;
    if (line1 && *line1) copy(shared.lines[n++], sizeof shared.lines[0], line1);
    if (line2 && *line2) copy(shared.lines[n++], sizeof shared.lines[0], line2);
    shared.lineCount = n;
  });
}

void portal(const char *apSsid, const char *apPassword, const char *ip, const char *failed) {
  update([&] {
    show(scene::Kind::Portal);
    copy(shared.ssid, sizeof shared.ssid, apSsid);
    copy(shared.password, sizeof shared.password, apPassword);
    copy(shared.ip, sizeof shared.ip, ip);
    copy(shared.subtitle, sizeof shared.subtitle, failed);
  });
}

void clock(uint32_t nowTs) {
  update([&] {
    clockTs = nowTs;
    clockMs = millis();
  });
}

void schedule(JsonObjectConst next, JsonArrayConst stale) {
  update([&] {
    scene::Ui before = shared;
    shared.hasNext = !next.isNull();
    if (shared.hasNext) {
      copy(shared.nextName, sizeof shared.nextName, next["name"] | "");
      copy(shared.nextTime, sizeof shared.nextTime, next["time"] | "");
      copy(shared.nextDay, sizeof shared.nextDay, next["day"] | "");
      copy(shared.nextRoom, sizeof shared.nextRoom, next["room"] | "");
      shared.nextStart = next["start_ts"] | 0;
      shared.nextEnd = next["end_ts"] | 0;
    }
    // sesi habis di server: datanya tidak diperbarui sampai login ulang
    shared.warning[0] = 0;
    for (const char *source : stale) {
      if (!strcmp(source, "SATU")) {
        copy(shared.warning, sizeof shared.warning, "Sesi SATU habis: presensi tidak terpantau");
        break;
      }
      copy(shared.warning, sizeof shared.warning, "Sesi kelas.usu habis: tugas tidak diperbarui");
    }
    bool changed = before.hasNext != shared.hasNext || strcmp(before.nextName, shared.nextName) ||
                   strcmp(before.nextTime, shared.nextTime) || strcmp(before.nextDay, shared.nextDay) ||
                   strcmp(before.nextRoom, shared.nextRoom) || strcmp(before.warning, shared.warning);
    if (changed && shared.kind == scene::Kind::Home) generation++;
  });
}

void alert(JsonObjectConst a) {
  update([&] {
    show(scene::Kind::Alert);
    const char *kind = a["kind"] | "";
    shared.alert = !strcmp(kind, "attendance") ? scene::Alert::Attendance
                   : !strcmp(kind, "attended") ? scene::Alert::Attended
                                               : scene::Alert::Deadline;
    copy(shared.alertCourse, sizeof shared.alertCourse, a["course"] | "");
    copy(shared.alertDetail, sizeof shared.alertDetail, a["detail"] | "");
    copy(shared.alertWhen, sizeof shared.alertWhen, a["when"] | "");
    shared.alertQr = strcmp(a["method"] | "qr", "direct") != 0;
    shared.alertFrom = a["from_ts"] | 0;
    shared.alertTo = a["to_ts"] | 0;
  });
}

void toast(const char *text) {
  update([&] {
    copy(shared.toast, sizeof shared.toast, text);
    toastAt = millis();
    generation++;
  });
}

}  // namespace display
