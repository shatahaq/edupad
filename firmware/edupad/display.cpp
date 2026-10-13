#include "display.h"

#include <LovyanGFX.hpp>

#include "config.h"

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

constexpr int W = 480;
constexpr int H = 320;
constexpr int BAR_H = 28;
constexpr int MARGIN = 12;

constexpr uint16_t BG = 0x0000;
constexpr uint16_t BAR = 0x18E3;
constexpr uint16_t TEXT = 0xFFFF;
constexpr uint16_t MUTED = 0xAD55;
constexpr uint16_t ACCENT = 0x5E7F;
constexpr uint16_t RED = 0xF8A2;
constexpr uint16_t GREEN = 0x2F65;
constexpr uint16_t YELLOW = 0xFEA0;

// Meter level mikrofon: -60..0 dBFS, garis kuning = ambang "ada suara" server (-35 dBFS).
constexpr int METER_X = 40, METER_Y = 200, METER_W = 400, METER_H = 24;
constexpr float METER_MIN_DB = -60.0f;
constexpr float SPEECH_DBFS = -35.0f;

enum class View { None, Message, Recording, Processing, Answer };
View view = View::None;
char status[40] = "";
uint32_t lastSeconds = UINT32_MAX;

void drawBar() {
  tft.fillRect(0, 0, W, BAR_H, BAR);
  tft.setFont(&fonts::Font2);
  tft.setTextColor(TEXT, BAR);
  tft.setTextDatum(middle_left);
  tft.drawString("EduPad", MARGIN, BAR_H / 2);
  tft.setTextColor(MUTED, BAR);
  tft.setTextDatum(middle_right);
  tft.drawString(status, W - MARGIN, BAR_H / 2);
}

void clearBody() { tft.fillRect(0, BAR_H, W, H - BAR_H, BG); }

// Potong `text` dengan "..." supaya muat `maxWidth` piksel dengan font aktif.
String fitWidth(const char *text, int maxWidth) {
  String s = text;
  if (tft.textWidth(s.c_str()) <= maxWidth) return s;
  while (s.length() && tft.textWidth((s + "...").c_str()) > maxWidth) s.remove(s.length() - 1);
  return s + "...";
}

void centered(const char *text, int y, const lgfx::IFont *font, uint16_t color) {
  if (!text) return;
  tft.setFont(font);
  tft.setTextColor(color, BG);
  tft.setTextDatum(top_center);
  tft.drawString(fitWidth(text, W - 2 * MARGIN).c_str(), W / 2, y);
}

void leftLine(const char *text, int y, const lgfx::IFont *font, uint16_t color) {
  tft.setFont(font);
  tft.setTextColor(color, BG);
  tft.setTextDatum(top_left);
  tft.drawString(fitWidth(text, W - 2 * MARGIN).c_str(), MARGIN, y);
}

int meterX(float db) {
  db = constrain(db, METER_MIN_DB, 0.0f);
  return (int)((db - METER_MIN_DB) / -METER_MIN_DB * (METER_W - 2));
}

// Angka detik di bawah judul; digambar ulang hanya saat berubah.
void drawSeconds(uint32_t elapsedMs, int y) {
  uint32_t seconds = elapsedMs / 1000;
  if (seconds == lastSeconds) return;
  lastSeconds = seconds;
  char text[16];
  snprintf(text, sizeof text, "%lu s", (unsigned long)seconds);
  tft.fillRect(0, y, W, 26, BG);
  centered(text, y, &fonts::Font4, MUTED);
}

void beginView(View next) {
  if (view == View::None) drawBar();
  clearBody();
  view = next;
  lastSeconds = UINT32_MAX;
}

}  // namespace

namespace display {

void begin() {
  tft.init();
  tft.setRotation(1);  // landscape, konektor di kiri; 3 untuk sebaliknya
  tft.setTextWrap(false);
  tft.setBrightness(255);
  tft.fillScreen(BG);
  drawBar();
}

void setStatus(const char *text) {
  if (strncmp(status, text, sizeof status) == 0) return;
  strlcpy(status, text, sizeof status);
  drawBar();
}

void message(const char *title, const char *line1, const char *line2, uint16_t color) {
  beginView(View::Message);
  centered(title, 110, &fonts::FreeSansBold18pt7b, color);
  centered(line1, 170, &fonts::FreeSans12pt7b, MUTED);
  centered(line2, 205, &fonts::FreeSans12pt7b, MUTED);
}

void idle(bool newSession) {
  message("Siap", "Tahan tombol BOOT lalu bicara",
          newSession ? "Percakapan baru dimulai" : "Tekan 1x: ulangi | 2x: sesi baru", ACCENT);
}

void portal(const char *apSsid, const char *apPassword, const char *ip, const char *failed) {
  beginView(View::Message);
  centered("Atur Wi-Fi", 40, &fonts::FreeSansBold18pt7b, YELLOW);
  if (failed && *failed) {
    String text = String("Gagal tersambung ke ") + failed;
    centered(text.c_str(), 86, &fonts::FreeSans9pt7b, MUTED);
  }
  String hotspot = String("    ") + apSsid + ", sandi " + apPassword;
  String url = String("    atau buka http://") + ip;
  leftLine("1. Sambungkan HP ke Wi-Fi:", 120, &fonts::FreeSans12pt7b, TEXT);
  leftLine(hotspot.c_str(), 150, &fonts::FreeSansBold12pt7b, ACCENT);
  leftLine("2. Halaman akan terbuka otomatis,", 190, &fonts::FreeSans12pt7b, TEXT);
  leftLine(url.c_str(), 220, &fonts::FreeSansBold12pt7b, ACCENT);
  centered("Tekan BOOT untuk mencoba lagi", 276, &fonts::FreeSans9pt7b, MUTED);
}

void recording(uint32_t elapsedMs, float levelDbfs) {
  if (view != View::Recording) {
    beginView(View::Recording);
    tft.fillCircle(W / 2 - 118, 92, 9, RED);
    tft.setFont(&fonts::FreeSansBold18pt7b);
    tft.setTextColor(TEXT, BG);
    tft.setTextDatum(middle_left);
    tft.drawString("Mendengarkan", W / 2 - 98, 92);
    centered("Lepas tombol untuk mengirim", 250, &fonts::FreeSans12pt7b, MUTED);
    tft.drawRect(METER_X, METER_Y, METER_W, METER_H, MUTED);
  }
  drawSeconds(elapsedMs, 130);

  int fill = meterX(levelDbfs);
  int mark = meterX(SPEECH_DBFS);
  tft.fillRect(METER_X + 1, METER_Y + 1, fill, METER_H - 2, levelDbfs >= SPEECH_DBFS ? GREEN : ACCENT);
  tft.fillRect(METER_X + 1 + fill, METER_Y + 1, METER_W - 2 - fill, METER_H - 2, BG);
  tft.drawFastVLine(METER_X + 1 + mark, METER_Y - 4, METER_H + 8, YELLOW);
}

void processing(uint32_t elapsedMs) {
  if (view != View::Processing) {
    beginView(View::Processing);
    centered("Memproses...", 92, &fonts::FreeSansBold18pt7b, ACCENT);
    centered("Mengenali suara dan mencari jawaban", 190, &fonts::FreeSans12pt7b, MUTED);
  }
  drawSeconds(elapsedMs, 135);
}

void answer(JsonObjectConst screen, const char *question) {
  beginView(View::Answer);

  // Server membungkus baris untuk font lebar tetap (38 kolom, judul besar 24 kolom).
  const char *title = screen["title"] | "EduPad";
  bool large = strcmp(screen["title_size"] | "normal", "large") == 0;
  const lgfx::IFont *titleFonts[] = {&fonts::FreeSansBold18pt7b, &fonts::FreeSansBold12pt7b,
                                     &fonts::FreeSansBold9pt7b};
  int pick = large ? 0 : 1;
  tft.setFont(titleFonts[pick]);
  while (pick < 2 && tft.textWidth(title) > W - 2 * MARGIN) tft.setFont(titleFonts[++pick]);
  tft.setTextColor(ACCENT, BG);
  tft.setTextDatum(middle_left);
  tft.drawString(fitWidth(title, W - 2 * MARGIN).c_str(), MARGIN, 56);
  tft.drawFastHLine(MARGIN, 80, W - 2 * MARGIN, BAR);

  tft.setFont(&fonts::FreeMonoBold9pt7b);  // 11 px per huruf: 38 kolom = 418 px
  tft.setTextColor(TEXT, BG);
  tft.setTextDatum(top_left);
  int y = 88;
  for (JsonVariantConst line : screen["lines"].as<JsonArrayConst>()) {
    if (y > 270) break;
    tft.drawString(line | "", MARGIN + 8, y);
    y += 22;
  }

  if (question && *question) {
    tft.fillRect(0, H - 26, W, 26, BAR);
    tft.setFont(&fonts::Font2);
    tft.setTextColor(MUTED, BAR);
    tft.setTextDatum(middle_left);
    String text = String("Kamu: ") + question;
    tft.drawString(fitWidth(text.c_str(), W - 2 * MARGIN).c_str(), MARGIN, H - 13);
  }
}

}  // namespace display
