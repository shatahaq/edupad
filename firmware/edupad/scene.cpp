#include "scene.h"

#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <string>

#include "owl_sprites.h"
#include "ui_fonts.h"

namespace scene {
namespace {

constexpr uint16_t rgb(uint32_t hex) {
  return ((hex >> 8) & 0xF800) | ((hex >> 5) & 0x07E0) | ((hex >> 3) & 0x001F);
}

// Palet: biru malam, tosca burung hantu, aksen emas. Semua layar memakai warna yang sama.
constexpr uint32_t BG_TOP_888 = 0x1B2458, BG_BOTTOM_888 = 0x0B1030;
constexpr uint16_t BG_TOP = rgb(BG_TOP_888);
constexpr uint16_t BG_BOTTOM = rgb(BG_BOTTOM_888);
constexpr uint16_t HALO_OUT = rgb(0x22306E);
constexpr uint16_t HALO_IN = rgb(0x2A3A82);
constexpr uint16_t SHADOW = rgb(0x151D4A);
constexpr uint16_t PANEL = rgb(0x1C265E);
constexpr uint16_t PANEL_EDGE = rgb(0x3A4AA0);
constexpr uint16_t TRACK = rgb(0x26306A);
constexpr uint16_t GOLD = rgb(0xFFC83D);
constexpr uint16_t MINT = rgb(0x7EE6CC);
constexpr uint16_t TEAL = rgb(0x2ED8C3);
constexpr uint16_t TEAL_DIM = rgb(0x237A8A);
constexpr uint16_t WHITE = rgb(0xFFFFFF);
constexpr uint16_t TEXT = rgb(0xE6EBFF);
constexpr uint16_t MUTED = rgb(0xA3AEDD);
constexpr uint16_t CORAL = rgb(0xFF7A85);
constexpr uint16_t REC = rgb(0xFF4F64);
constexpr uint16_t SKY = rgb(0x8FD8FF);
constexpr uint16_t INK = rgb(0x10132A);
constexpr uint16_t CLOUD = rgb(0xEEF2FF);
constexpr uint16_t PAPER = rgb(0xFFF4DC);
constexpr uint16_t PAPER_DARK = rgb(0xEBD9B4);
constexpr uint16_t INKLINE = rgb(0xC9B48A);
constexpr uint16_t WOOD = rgb(0xC0844A);

constexpr float PI_F = 3.14159265f;
constexpr int CELL = 4;  // ukuran "piksel" hiasan supaya serasi dengan sprite 4x

// Panggung: burung hantu besar (4x) di tengah atas, dengan lingkaran cahaya dan hiasan.
// Dua baris teks di bawahnya.
constexpr int BIG = 4;
constexpr int BIG_X = W / 2 - OWL_W * BIG / 2;
constexpr int BIG_Y = 8;
constexpr int FEET_Y = BIG_Y + 47 * BIG;  // bawah kaki di sprite
constexpr int HALO_X = W / 2, HALO_Y = 112;
constexpr Rect STAGE{84, 0, 312, 214};
constexpr Rect LINE1{0, 214, W, 44};
constexpr Rect LINE2{0, 258, W, 62};
constexpr int LINE1_Y = 236, LINE2_Y = 272;

// Layar jawaban/Wi-Fi: burung hantu kecil (2x) kiri atas, gelembung judul, kartu isi.
constexpr int SMALL = 2;
constexpr Rect OWL_SMALL{0, 0, 108, 100};
constexpr Rect BUBBLE{114, 8, 358, 84};
constexpr Rect CARD{8, 100, 464, 212};

// Layar pesan: burung hantu sedang (3x) di kiri, teks di kanan.
constexpr int MID = 3;
constexpr int MID_X = 4, MID_Y = 72;
constexpr Rect OWL_MID{0, 40, 180, 220};
constexpr int NOTE_X = 186, NOTE_W = 280;

// Latar penuh yang sudah digambar sekali (gradasi dengan dithering lambat dibuat); disalin
// ke kanvas tiap kali sebuah area digambar ulang.
LGFX_Sprite bgCache;

struct Font {
  lgfx::PointerWrapper data;
  lgfx::VLWfont vlw;
};
Font logoFont, headFont, textFont, smallFont;

void load(Font &f, const uint8_t *array, uint32_t size) {
  f.data.set(array, size);
  f.vlw.loadFont(&f.data);
}

uint16_t mix(uint16_t a, uint16_t b, float t) {
  int k = (int)(t * 256);
  if (k <= 0) return a;
  if (k >= 256) return b;
  int r = ((a >> 11) * (256 - k) + (b >> 11) * k) >> 8;
  int g = (((a >> 5) & 63) * (256 - k) + ((b >> 5) & 63) * k) >> 8;
  int bl = ((a & 31) * (256 - k) + (b & 31) * k) >> 8;
  return r << 11 | g << 5 | bl;
}

uint16_t bgAt(int y) { return mix(BG_TOP, BG_BOTTOM, (float)y / (H - 1)); }

// Bahasa frame yang sedang digambar (ui.english, diisi render()).
bool english = false;
const char *tr(const char *id, const char *en) { return english ? en : id; }

float clamp01(float x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }
float easeOutCubic(float x) { return 1 - powf(1 - x, 3); }
float easeOutBack(float x) {
  const float c1 = 1.70158f, c3 = c1 + 1;
  return 1 + c3 * powf(x - 1, 3) + c1 * powf(x - 1, 2);
}
float easeOutBounce(float x) {
  const float n = 7.5625f, d = 2.75f;
  if (x < 1 / d) return n * x * x;
  if (x < 2 / d) return x -= 1.5f / d, n * x * x + 0.75f;
  if (x < 2.5f / d) return x -= 2.25f / d, n * x * x + 0.9375f;
  return x -= 2.625f / d, n * x * x + 0.984375f;
}

// Gradasi dengan ordered dithering 4x4 supaya tidak tampak bergaris di warna 16-bit.
void drawGradient(lgfx::LovyanGFX &g) {
  static const uint8_t bayer[4][4] = {{0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5}};
  auto ch = [](uint32_t c, int shift) { return (float)((c >> shift) & 0xFF); };
  for (int y = 0; y < H; y++) {
    float t = (float)y / (H - 1);
    float r = ch(BG_TOP_888, 16) + (ch(BG_BOTTOM_888, 16) - ch(BG_TOP_888, 16)) * t;
    float gr = ch(BG_TOP_888, 8) + (ch(BG_BOTTOM_888, 8) - ch(BG_TOP_888, 8)) * t;
    float b = ch(BG_TOP_888, 0) + (ch(BG_BOTTOM_888, 0) - ch(BG_TOP_888, 0)) * t;
    for (int x = 0; x < W; x++) {
      float d = (bayer[y & 3][x & 3] + 0.5f) / 16;
      int r5 = (int)(r / 8 + d), g6 = (int)(gr / 4 + d), b5 = (int)(b / 8 + d);
      g.drawPixel(x, y, (uint16_t)((r5 > 31 ? 31 : r5) << 11 | (g6 > 63 ? 63 : g6) << 5 | (b5 > 31 ? 31 : b5)));
    }
  }
}

// ---------------------------------------------------------------- bentuk pixel art

// Lingkaran/elips dari kotak-kotak `cell` piksel, berpusat di (cx, cy).
void cellEllipse(lgfx::LovyanGFX &g, int cx, int cy, float rx, float ry, uint16_t color, int cell = CELL) {
  if (rx <= 0 || ry <= 0) return;
  int nx = (int)rx + 1, ny = (int)ry + 1;
  for (int j = -ny; j < ny; j++) {
    float v = (j + 0.5f) / ry;
    if (v * v > 1) continue;
    int span = (int)floorf(rx * sqrtf(1 - v * v) + 0.5f);
    if (span <= 0 || span > nx) continue;
    g.fillRect(cx - span * cell, cy + j * cell, span * 2 * cell, cell, color);
  }
}

// Bintang "+" berkelip; size 0 = tak terlihat, 1 = titik, 2 = plus, 3 = plus besar.
void sparkle(lgfx::LovyanGFX &g, int x, int y, int size, uint16_t color) {
  if (size <= 0) return;
  g.fillRect(x - CELL / 2, y - CELL / 2, CELL, CELL, color);
  for (int i = 1; i < size; i++) {
    g.fillRect(x - CELL / 2 + i * CELL, y - CELL / 2, CELL, CELL, color);
    g.fillRect(x - CELL / 2 - i * CELL, y - CELL / 2, CELL, CELL, color);
    g.fillRect(x - CELL / 2, y - CELL / 2 + i * CELL, CELL, CELL, color);
    g.fillRect(x - CELL / 2, y - CELL / 2 - i * CELL, CELL, CELL, color);
  }
}

// Gambar kecil dari teks ('#' = isi), tiap titik selebar `cell`.
void glyph(lgfx::LovyanGFX &g, const char *const *rows, int n, int x, int y, int cell, uint16_t color) {
  for (int r = 0; r < n; r++)
    for (int c = 0; rows[r][c]; c++)
      if (rows[r][c] == '#') g.fillRect(x + c * cell, y + r * cell, cell, cell, color);
}

// Gambar kecil berwarna: tiap huruf dipetakan ke warna oleh `color(ch)` (negatif = kosong).
template <typename F>
void art(lgfx::LovyanGFX &g, const char *const *rows, int n, int x, int y, int cell, F color) {
  for (int r = 0; r < n; r++)
    for (int c = 0; rows[r][c]; c++) {
      int32_t k = color(rows[r][c]);
      if (k >= 0) g.fillRect(x + c * cell, y + r * cell, cell, cell, (uint16_t)k);
    }
}

// Cincin dari kotak-kotak `cell` piksel: kotak yang jaraknya dari pusat di [r - 1, r] (dalam cell).
void cellRing(lgfx::LovyanGFX &g, int cx, int cy, float r, uint16_t color, int cell) {
  int n = (int)r + 1;
  for (int j = -n; j < n; j++)
    for (int i = -n; i < n; i++) {
      float d = sqrtf((i + 0.5f) * (i + 0.5f) + (j + 0.5f) * (j + 0.5f));
      if (d <= r && d > r - 1) g.fillRect(cx + i * cell, cy + j * cell, cell, cell, color);
    }
}

// Panel bersudut pixel: sudut dipotong satu CELL, tepi 2 px.
void panel(lgfx::LovyanGFX &g, const Rect &r, uint16_t fill, uint16_t edge) {
  g.fillRect(r.x + CELL, r.y, r.w - 2 * CELL, r.h, edge);
  g.fillRect(r.x, r.y + CELL, r.w, r.h - 2 * CELL, edge);
  g.fillRect(r.x + CELL, r.y + 2, r.w - 2 * CELL, r.h - 4, fill);
  g.fillRect(r.x + 2, r.y + CELL, r.w - 4, r.h - 2 * CELL, fill);
}

// Sprite berindeks diperbesar; piksel bersebelahan berwarna sama digambar sekaligus.
void drawSprite(lgfx::LovyanGFX &g, const uint8_t *frame, int w, int h, int x, int y, int scale) {
  int32_t cx, cy, cw, ch;
  g.getClipRect(&cx, &cy, &cw, &ch);
  for (int row = 0; row < h; row++) {
    int py = y + row * scale;
    if (py + scale <= cy || py >= cy + ch) continue;
    const uint8_t *p = frame + row * w;
    for (int col = 0; col < w;) {
      uint8_t idx = p[col];
      int run = 1;
      while (col + run < w && p[col + run] == idx) run++;
      if (idx) g.fillRect(x + col * scale, py, run * scale, scale, OWL_PAL[idx - 1]);
      col += run;
    }
  }
}

void drawOwl(lgfx::LovyanGFX &g, const uint8_t *frame, int x, int y, int scale) {
  drawSprite(g, frame, OWL_W, OWL_H, x, y, scale);
}

// ---------------------------------------------------------------- teks

void useFont(lgfx::LovyanGFX &g, Font &f) { g.setFont(&f.vlw); }

void say(lgfx::LovyanGFX &g, const char *s, int x, int y, uint16_t color, textdatum_t datum = middle_left) {
  g.setTextColor(color);
  g.setTextDatum(datum);
  g.drawString(s, x, y);
}

std::string fitWidth(lgfx::LovyanGFX &g, const char *text, int maxWidth) {
  std::string s = text;
  if (g.textWidth(s.c_str()) <= maxWidth) return s;
  while (!s.empty() && g.textWidth((s + "...").c_str()) > maxWidth) s.pop_back();
  return s + "...";
}

// Bungkus kata ke lebar maxW dengan font aktif. Mengisi out (bila tidak null, maks maxLines)
// dan mengembalikan jumlah baris yang dibutuhkan, bisa lebih dari maxLines.
int wrap(lgfx::LovyanGFX &g, const char *text, int maxW, std::string *out, int maxLines) {
  int n = 0;
  std::string line;
  auto emit = [&](const std::string &s) {
    if (out && n < maxLines) out[n] = s;
    n++;
  };
  for (const char *p = text; *p;) {
    while (*p == ' ') p++;
    const char *e = p;
    while (*e && *e != ' ') e++;
    if (e == p) break;
    std::string token(p, e - p);
    std::string joined = line.empty() ? token : line + " " + token;
    if (!line.empty() && g.textWidth(joined.c_str()) > maxW) {
      emit(line);
      line = token;
    } else {
      line = joined;
    }
    while (line.size() > 1 && g.textWidth(line.c_str()) > maxW) {  // kata tunggal terlalu panjang
      size_t cut = line.size() - 1;
      while (cut > 1 && g.textWidth(line.substr(0, cut).c_str()) > maxW) cut--;
      emit(line.substr(0, cut));
      line = line.substr(cut);
    }
    p = e;
  }
  if (!line.empty()) emit(line);
  return n;
}

// ---------------------------------------------------------------- burung hantu

// Pose dasar dengan kedipan tiap 3,4 s (setengah - tutup - setengah) dan sesekali melirik.
const uint8_t *alive(float t, const uint8_t *open, bool look = true) {
  float b = fmodf(t + 0.6f, 3.4f);
  if (b > 3.1f) {
    float k = b - 3.1f;
    return (k < 0.05f || k >= 0.15f) ? OWL_BLINK_HALF : OWL_BLINK;
  }
  if (look) {
    float l = fmodf(t, 9.0f);
    if (l > 4.2f && l < 5.0f) return OWL_LOOK_L;
    if (l > 6.8f && l < 7.6f) return OWL_LOOK_R;
  }
  return open;
}

// Naik-turun pelan seperti bernapas (piksel layar).
int breath(float t, float amp = 2) { return (int)roundf(sinf(t * 2.4f) * amp); }

void halo(lgfx::LovyanGFX &g, float grow, float extra) {
  cellEllipse(g, HALO_X, HALO_Y, (24 + extra) * grow, (24 + extra) * grow, HALO_OUT);
  cellEllipse(g, HALO_X, HALO_Y, (20 + extra) * grow, (20 + extra) * grow, HALO_IN);
}

// Bintang berkelip di sekitar lingkaran cahaya; burst = semua menyala terang. skip = indeks
// bintang yang tidak digambar (mis. di jalur huruf Z saat tidur).
void stars(lgfx::LovyanGFX &g, float t, bool burst, int skip = -1) {
  struct Star {
    int dx, dy;
    float phase;
    uint16_t color;
  };
  static const Star list[] = {{-112, -64, 0.0f, GOLD}, {108, -84, 1.7f, MINT}, {-124, 34, 3.1f, MINT},
                              {118, 26, 4.4f, GOLD},   {-72, -96, 2.4f, GOLD}, {82, 82, 5.3f, MINT}};
  for (const Star &s : list) {
    if (&s - list == skip) continue;
    float v = sinf(t * 2.2f + s.phase);
    int size = burst ? 3 : (v > 0.75f ? 3 : v > 0.2f ? 2 : v > -0.3f ? 1 : 0);
    sparkle(g, HALO_X + s.dx, HALO_Y + s.dy, size, s.color);
  }
}

void shadow(lgfx::LovyanGFX &g, float air) {
  cellEllipse(g, W / 2, FEET_Y + 6, 12 * (1 - clamp01(air) * 0.5f), 1.5f, SHADOW);
}

// Progress bar pixel art (42 kotak 4 px) berpusat di (W/2, y).
constexpr int BAR_SEGS = 42;
void barTrack(lgfx::LovyanGFX &g, int y, uint16_t color) {
  int bx = W / 2 - BAR_SEGS * CELL / 2;
  g.fillRect(bx - CELL, y, (BAR_SEGS + 2) * CELL, CELL * 2, color);
  g.fillRect(bx, y - CELL, BAR_SEGS * CELL, CELL * 4, color);
}
void barFill(lgfx::LovyanGFX &g, int y, int from, int count, uint16_t color, uint16_t shine) {
  if (count <= 0) return;
  int bx = W / 2 - BAR_SEGS * CELL / 2 + from * CELL;
  g.fillRect(bx, y, count * CELL, CELL * 2, color);
  g.fillRect(bx, y, count * CELL, CELL / 2, shine);
}

// ---------------------------------------------------------------- layar nyala

const uint8_t *bootFrame(float t, float done) {
  if (done >= 0) return OWL_HAPPY;
  if (t < 1.0f) return OWL_BLINK;  // masih tidur saat jatuh
  if (t < 1.08f) return OWL_BLINK_HALF;
  if (t >= 1.4f && t < 2.6f) return ((int)((t - 1.4f) / 0.17f) % 2) ? OWL_WAVE_2 : OWL_WAVE_1;
  return alive(t - 1.0f, OWL_IDLE);
}

void bootStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  halo(g, easeOutCubic(clamp01(t / 0.6f)), sinf(t * 1.6f) * 0.5f);
  if (t > 0.8f) stars(g, t, ui.done >= 0 && ui.done < 0.9f);
  // jatuh dari atas lalu memantul; bernapas; melompat saat siap
  float y = -(1 - easeOutBounce(clamp01((t - 0.1f) / 0.75f))) * 150;
  if (t > 0.85f) y += breath(t - 0.85f);
  float lift = ui.done >= 0 ? sinf(clamp01(ui.done / 0.45f) * PI_F) * 20 : 0;
  if (t > 0.1f) shadow(g, (-y + lift) / 60);
  drawOwl(g, bootFrame(t, ui.done), BIG_X, BIG_Y + (int)(y - lift), BIG);
}

void bootTitle(lgfx::LovyanGFX &g, float t) {
  float a = easeOutCubic(clamp01((t - 0.7f) / 0.5f));
  if (a <= 0) return;
  int y = LINE1_Y + (int)((1 - a) * 12);
  uint16_t bg = bgAt(y);
  useFont(g, logoFont);
  int w1 = g.textWidth("Edu"), w2 = g.textWidth("Pad");
  int x = W / 2 - (w1 + w2) / 2;
  say(g, "Edu", x, y, mix(bg, WHITE, a));
  say(g, "Pad", x + w1, y, mix(bg, TEAL, a));
}

void bootStatus(lgfx::LovyanGFX &g, const Ui &ui) {
  float a = clamp01((ui.t - 0.9f) / 0.4f);
  if (a <= 0) return;
  int y = 270;
  uint16_t bg = bgAt(y);
  bool done = ui.done >= 0;
  // teks status + tiga titik bergelombang (tanpa titik saat siap)
  useFont(g, textFont);
  std::string s = fitWidth(g, ui.status, W - 100);
  int tw = g.textWidth(s.c_str());
  int dots = done ? 0 : 3;
  int x = W / 2 - (tw + (dots ? 6 + dots * 8 : 0)) / 2;
  say(g, s.c_str(), x, y, mix(bg, done ? TEAL : MUTED, a));
  for (int i = 0; i < dots; i++) {
    float k = clamp01(sinf(ui.t * 6 - i * 0.9f));
    g.fillRect(x + tw + 6 + i * 8, y + 4 - (int)(k * 3), 4, 4, mix(bg, MUTED, a * (0.35f + 0.65f * k)));
  }
  int by = 290;
  uint16_t bbg = bgAt(by);
  barTrack(g, by, mix(bbg, TRACK, a));
  barFill(g, by, 0, (int)(clamp01(ui.progress) * BAR_SEGS + 0.5f), mix(bbg, TEAL, a), mix(bbg, MINT, a));
}

// ---------------------------------------------------------------- tidur & bangun

constexpr uint16_t BLANKET = rgb(0x4152B8);
constexpr uint16_t BLANKET_DOT = rgb(0x5C6FD6);
constexpr uint16_t BLANKET_HEM = rgb(0x9AA8F0);
constexpr uint16_t MOON = rgb(0xFFE9A8);
const char *const MOON_GLYPH[] = {"..###", ".##..", "##...", "##...", "##...", ".##..", "..###"};
const char *const Z_GLYPH[] = {"####", "..#.", ".#..", "####"};
const char *const BANG_GLYPH[] = {"#", "#", "#", ".", "#"};

constexpr int BLANKET_TOP = BIG_Y + 35 * BIG;  // menutupi dari perut ke bawah, wajah tetap terlihat
constexpr int BLANKET_BOTTOM = FEET_Y + 10;
constexpr float WAKE_SECONDS = WAKE_ROOM_SECONDS + 2.05f;

// Selimut bertitik dengan lipatan terang di tepi atas, dari `top` sampai bawah kaki.
void blanket(lgfx::LovyanGFX &g, int top) {
  if (top >= BLANKET_BOTTOM - 8) return;
  Rect r{W / 2 - 92, top, 184, BLANKET_BOTTOM - top};
  panel(g, r, BLANKET, INK);
  g.fillRect(r.x + 2, top + 4, r.w - 4, 8, BLANKET_HEM);
  g.fillRect(r.x + 2, top + 12, r.w - 4, 2, INK);
  for (int y = top + 20, row = 0; y < r.y + r.h - 6; y += 12, row++)
    for (int x = r.x + 12 + (row % 2) * 12; x < r.x + r.w - 10; x += 24) g.fillRect(x, y, 4, 4, BLANKET_DOT);
}

// ---- kamar tidur (seperti mockup): kamar gelap, burung hantu berbaring berselimut

constexpr float ROOM_AT = SLEEP_ROOM_AT;
constexpr int BED_SCALE = 4;
constexpr int FLOOR_Y = 262;
constexpr int BED_X = W / 2 - BED_W * BED_SCALE / 2;
constexpr int BED_Y = FLOOR_Y + 8 - BED_H * BED_SCALE;
constexpr Rect ZZZ_AREA{240, 4, 112, 116};  // satu-satunya bagian yang bergerak saat tidur
constexpr Rect BANG_AREA{248, 8, 36, 64};    // tanda seru saat dibangunkan di ranjang
constexpr uint16_t WALL_TOP = rgb(0x141B3E), WALL_BOTTOM = rgb(0x0D1230);
constexpr uint16_t FLOOR = rgb(0x0A0D26), FLOOR_EDGE = rgb(0x1C2352);
constexpr uint16_t SHELF = rgb(0x222A5A), SHELF_DARK = rgb(0x161C44);
constexpr uint16_t POT = rgb(0x2E3462), LEAF = rgb(0x1B4750), LEAF_LIGHT = rgb(0x23606A);
constexpr uint16_t MOON_DIM = rgb(0xE6C46A), Z_BLUE = rgb(0x6F9BFF);

// Tiga huruf Z bergantian naik dari kepala, membesar, lalu memudar di dinding gelap.
void zzz(lgfx::LovyanGFX &g, float t) {
  for (int k = 0; k < 3; k++) {
    float age = t - k * 1.0f;
    if (age < 0) continue;
    float a = fmodf(age, 3.0f);
    int x = 256 + (int)(a * 16 + sinf(a * 3) * 4), y = 96 - (int)(a * 26);
    float alpha = a > 2.2f ? 1 - (a - 2.2f) / 0.8f : clamp01(a / 0.3f);
    glyph(g, Z_GLYPH, 4, x, y, 3 + (int)a, mix(mix(WALL_TOP, WALL_BOTTOM, (float)y / FLOOR_Y), Z_BLUE, alpha));
  }
}

// Kamar: dinding, lantai, rak berpot tanaman, tumpukan buku, rak buku, bulan, lalu ranjang.
// Semua dibatasi area clip, jadi murah dipakai untuk menggambar ulang bagian kecil.
// awake: dibangunkan (w = detik sejak itu): mata terbuka kaget dan tanda seru, tanpa Z.
void bedroom(lgfx::LovyanGFX &g, float t, bool awake = false, float w = 0) {
  int32_t cx, cy, cw, ch;
  g.getClipRect(&cx, &cy, &cw, &ch);
  for (int y = cy; y < cy + ch; y++)
    g.drawFastHLine(cx, y, cw, y < FLOOR_Y ? mix(WALL_TOP, WALL_BOTTOM, (float)y / FLOOR_Y) : FLOOR);
  g.fillRect(0, FLOOR_Y, W, 2, FLOOR_EDGE);
  // rak dinding kiri dengan pot tanaman
  g.fillRect(12, 150, 88, 6, SHELF);
  g.fillRect(12, 156, 88, 3, SHELF_DARK);
  for (int i = 0; i < 5; i++) {  // daun
    static const int leaf[5][4] = {{26, 104, 14, 8}, {22, 96, 8, 8}, {58, 100, 16, 8}, {70, 92, 8, 8}, {44, 82, 10, 26}};
    g.fillRect(leaf[i][0], leaf[i][1], leaf[i][2], leaf[i][3], i % 2 ? LEAF_LIGHT : LEAF);
  }
  g.fillRect(36, 108, 8, 16, LEAF);
  g.fillRect(56, 106, 8, 18, LEAF);
  g.fillRect(34, 122, 36, 6, rgb(0x383E74));  // pot
  g.fillRect(38, 128, 28, 22, POT);
  // tumpukan buku di lantai kiri
  g.fillRect(6, 244, 70, 16, rgb(0x5A4034));
  g.fillRect(10, 248, 62, 3, rgb(0x8A7E66));
  g.fillRect(12, 230, 56, 14, rgb(0x2E3A73));
  g.fillRect(16, 234, 48, 2, rgb(0x55608F));
  g.fillRect(18, 220, 42, 10, rgb(0x4A2F4F));
  // rak buku kanan
  g.fillRect(404, 100, 66, 162, SHELF_DARK);
  g.fillRect(404, 100, 66, 4, SHELF);
  g.fillRect(404, 100, 4, 162, SHELF);
  g.fillRect(466, 100, 4, 162, SHELF);
  static const uint16_t spines[] = {rgb(0x2E3A73), rgb(0x4A2F4F), rgb(0x24485A), rgb(0x5A4034), rgb(0x3A2E66)};
  for (int shelf = 0; shelf < 3; shelf++) {
    int base = 152 + shelf * 52;
    g.fillRect(404, base, 66, 4, SHELF);
    for (int b = 0, x = 410; x < 458; b++) {
      int w = 8 + (b * 3 + shelf) % 4 * 2, h = 30 + (b * 7 + shelf * 5) % 14;
      g.fillRect(x, base - h, w, h, spines[(b + shelf * 2) % 5]);
      x += w + 2;
    }
  }
  glyph(g, MOON_GLYPH, 7, 424, 28, 5, MOON_DIM);
  drawSprite(g, awake ? OWL_BED_AWAKE : OWL_BED, BED_W, BED_H, BED_X, BED_Y, BED_SCALE);
  if (awake) {
    glyph(g, BANG_GLYPH, 5, 258, 22 - (int)(sinf(clamp01(w / 0.3f) * PI_F) * 10), 5, GOLD);
  } else if (t > ROOM_AT + 0.4f) {
    zzz(g, t - ROOM_AT - 0.4f);
  }
}

const uint8_t *fallingAsleep(float t) {
  if (t < 0.3f) return alive(t, OWL_IDLE, false);
  if (t < 1.3f) return OWL_YAWN;
  if (t < 1.6f) return OWL_BLINK_HALF;
  return OWL_BLINK;
}

// Sebelum pindah ke kamar: menguap lalu terkantuk-kantuk, cahaya di belakang meredup.
void dozeStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  float dim = clamp01((t - 1.0f) / 1.2f) * 0.6f;
  uint16_t bg = bgAt(HALO_Y);
  cellEllipse(g, HALO_X, HALO_Y, 24, 24, mix(HALO_OUT, bg, dim));
  cellEllipse(g, HALO_X, HALO_Y, 20, 20, mix(HALO_IN, bg, dim));
  stars(g, t * 0.4f, false);
  shadow(g, 0);
  int nod = t > 1.6f ? (int)(clamp01((t - 1.6f) / 0.5f) * 6) : breath(t);  // kepala terangguk
  drawOwl(g, fallingAsleep(t), BIG_X, BIG_Y + nod, BIG);
}

// Animasi bangun (w = detik sejak dibangunkan): kaget dengan "!", melompat kecil, lalu
// melambai. Mengembalikan nullptr bila sudah selesai.
// Setelah kaget di ranjang (lihat bedroom): melompat keluar selimut, menggeliat, lalu melambai.
// w = detik sejak dibangunkan. nullptr bila sudah selesai atau masih di kamar.
const uint8_t *wakeFrame(float w, float &lift) {
  lift = 0;
  float k = w - WAKE_ROOM_SECONDS;
  if (k < 0 || w >= WAKE_SECONDS) return nullptr;
  if (k < 0.5f) {
    lift = sinf(clamp01(k / 0.45f) * PI_F) * 18;
    return OWL_SURPRISED;
  }
  if (k < 1.2f) return OWL_STRETCH;
  return ((int)((k - 1.2f) / 0.17f) % 2) ? OWL_WAVE_2 : OWL_WAVE_1;
}

// Hiasan saat melompat keluar: selimut jatuh ke bawah dan tanda seru.
void wakeDecor(lgfx::LovyanGFX &g, float w) {
  float k = w - WAKE_ROOM_SECONDS;
  if (k < 0) return;
  if (k < 0.35f) blanket(g, BLANKET_TOP + (int)(easeOutCubic(k / 0.35f) * (BLANKET_BOTTOM - BLANKET_TOP)));
  if (k < 0.5f) glyph(g, BANG_GLYPH, 5, 330, 30 - (int)(sinf(clamp01(k / 0.3f) * PI_F) * 8), 4, GOLD);
}

// ---------------------------------------------------------------- siap

int homeIconX = 0;  // posisi ikon tombol, dihitung dari lebar teks saat digambar penuh

constexpr uint16_t SKIN = rgb(0xFDE3B0);
constexpr int ICON_W = 36, ICON_H = 40;

// Jari menekan dan menahan tombol, berulang: penjelas cara bertanya. (x, y) = kiri atas,
// s = skala (ukuran ICON_W x ICON_H kali s).
void buttonIcon(lgfx::LovyanGFX &g, int x, int y, float t, int s = 1) {
  auto rect = [&](int rx, int ry, int rw, int rh, uint16_t c) { g.fillRect(x + rx * s, y + ry * s, rw * s, rh * s, c); };
  float c = fmodf(t, 2.4f);
  int press = (c > 0.4f && c < 1.8f) ? 4 : 0;
  // dudukan
  rect(2, 30, ICON_W - 4, 10, PANEL_EDGE);
  rect(0, 32, ICON_W, 6, PANEL_EDGE);
  rect(4, 32, ICON_W - 8, 4, PANEL);
  // tombol: garis tepi, isi tosca, kilau atas; memendek saat ditekan
  int top = 18 + press;
  rect(6, top, ICON_W - 12, 32 - top, INK);
  rect(8, top + 2, ICON_W - 16, 30 - top - 2, TEAL);
  rect(8, top + 2, ICON_W - 16, 2, MINT);
  // jari dari atas (ujung membulat), turun bersama tombol
  int fx = ICON_W / 2 - 6, tip = top - 2;
  rect(fx, 0, 12, tip, INK);
  rect(fx + 2, 0, 8, tip - 2, SKIN);
  rect(fx + 4, tip - 6, 4, 2, rgb(0xF5B98A));  // kuku
  if (press) {  // garis gerak di kiri-kanan tombol
    rect(-2, top + 2, 4, 4, GOLD);
    rect(ICON_W - 2, top + 2, 4, 4, GOLD);
  }
}

void homeTitle(lgfx::LovyanGFX &g, float t, bool drawText, int y = LINE1_Y) {
  const char *text = tr("Tahan tombol untuk bertanya", "Hold the button to ask");
  useFont(g, headFont);
  int tw = g.textWidth(text);
  int x = W / 2 - (ICON_W + 14 + tw) / 2;
  homeIconX = x;
  buttonIcon(g, x, y - 24, t);
  if (drawText) say(g, text, x + ICON_W + 14, y + 2, WHITE);
}

void homeHint(lgfx::LovyanGFX &g, const Ui &ui, int y = LINE2_Y) {
  useFont(g, smallFont);
  if (!ui.online) {
    say(g, tr("Wi-Fi terputus, menyambung ulang...", "Wi-Fi lost, reconnecting..."), W / 2, y, CORAL, middle_center);
  } else if (ui.warning[0]) {
    say(g, ui.warning, W / 2, y, CORAL, middle_center);
  } else if (ui.newSession) {
    say(g, tr("Topik baru dimulai", "New topic started"), W / 2, y, TEAL, middle_center);
  } else {
    const char *a = tr("Tekan 1x: ulangi jawaban", "Press 1x: repeat answer"),
               *b = tr("Tekan 2x: topik baru", "Press 2x: new topic");
    int wa = g.textWidth(a), wb = g.textWidth(b);
    int x = W / 2 - (wa + 28 + wb) / 2;
    say(g, a, x, y, MUTED);
    g.fillRect(x + wa + 12, y - 2, 4, 4, PANEL_EDGE);
    say(g, b, x + wa + 28, y, MUTED);
  }
}

// ---- kartu "kuliah berikutnya" di layar siap

constexpr Rect NEXT_CARD{24, 246, 432, 50};
constexpr int NEXT_TITLE_Y = 226, NEXT_HINT_Y = 309;
constexpr uint16_t CAL_RED = rgb(0xFF6B78);

const char *const MINI_CAL[] = {".o...o.", "rrrrrrr", "rrrrrrr", "wwwwwww", "wkwkwkw", "wwwwwww", "wkwkwkw"};

int32_t calColor(char c) {
  switch (c) {
    case 'o': return INK;
    case 'r': return CAL_RED;
    case 'w': return PAPER;
    case 'k': return INKLINE;
  }
  return -1;
}

// Sisa waktu singkat: "<1 menit", "14 menit", "2 jam 5 menit", "30 jam".
void duration(char *out, size_t n, int32_t s) {
  if (s < 60) {
    snprintf(out, n, "%s", tr("<1 menit", "<1 min"));
    return;
  }
  int m = (s + 59) / 60, h = m / 60;
  if (h == 0) {
    snprintf(out, n, tr("%d menit", "%d min"), m);
  } else if (h < 10 && m % 60) {
    snprintf(out, n, tr("%d jam %d menit", "%d h %d min"), h, m % 60);
  } else {
    snprintf(out, n, tr("%d jam", "%d hours"), h);
  }
}

// Label kanan kartu: "Berlangsung", "25 mnt", "3 jam", atau hari ("Besok"/"Tomorrow").
// soon: mulai < 30 menit lagi (label berkedip emas).
void nextChip(const Ui &ui, char *out, size_t n, bool &ongoing, bool &soon) {
  ongoing = soon = false;
  if (!ui.nowTs) {
    snprintf(out, n, "%s", ui.nextDay);
    return;
  }
  int32_t s = (int32_t)(ui.nextStart - ui.nowTs);
  if (s <= 0 && ui.nowTs < ui.nextEnd) {
    ongoing = true;
    snprintf(out, n, "%s", tr("Berlangsung", "Ongoing"));
  } else if (s < 3600) {
    soon = s < 1800;
    snprintf(out, n, tr("%d mnt", "%d min"), (s + 59) / 60);
  } else if (!strcmp(ui.nextDay, "Hari ini") || !strcmp(ui.nextDay, "Today")) {
    snprintf(out, n, tr("%d jam", "%d hr"), s / 3600);
  } else {
    snprintf(out, n, "%s", ui.nextDay);
  }
}

// Kunci isi kartu (berubah tiap menit, atau tiap kedip saat hampir mulai).
int nextCardKey(const Ui &ui) {
  char chip[24];
  bool ongoing, soon;
  nextChip(ui, chip, sizeof chip, ongoing, soon);
  int32_t minutes = ui.nowTs ? (int32_t)(ui.nextStart - ui.nowTs) / 60 : 0;
  return minutes * 4 + ongoing * 2 + (soon && fmodf(ui.t, 1.0f) < 0.5f);
}

void nextCard(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = NEXT_CARD;
  panel(g, r, PANEL, PANEL_EDGE);
  art(g, MINI_CAL, 7, r.x + 12, r.y + 11, 4, calColor);
  char chip[24];
  bool ongoing, soon;
  nextChip(ui, chip, sizeof chip, ongoing, soon);
  // label kanan
  useFont(g, smallFont);
  int cw = g.textWidth(chip) + 22;
  Rect c{r.x + r.w - cw - 10, r.y + 10, cw, 30};
  bool blink = soon && fmodf(ui.t, 1.0f) < 0.5f;
  uint16_t fill = ongoing ? TEAL : (soon ? (blink ? GOLD : rgb(0x8A6A1E)) : PANEL_EDGE);
  panel(g, c, fill, fill);
  say(g, chip, c.x + c.w / 2, c.y + c.h / 2, ongoing || blink ? INK : WHITE, middle_center);
  // dua baris teks: keterangan, lalu nama - jam - ruang
  int x = r.x + 50, maxW = c.x - 10 - x;
  char label[40];
  snprintf(label, sizeof label, ongoing ? tr("Sedang berlangsung", "In progress") : tr("Kuliah berikutnya - %s", "Next class - %s"),
           ui.nextDay);
  say(g, fitWidth(g, label, maxW).c_str(), x, r.y + 15, ongoing ? TEAL : MUTED);
  useFont(g, textFont);
  int wn = g.textWidth(ui.nextName);
  say(g, ui.nextName, x, r.y + 35, WHITE);
  int xt = x + wn + 10;
  say(g, ui.nextTime, xt, r.y + 35, GOLD);
  int xr = xt + g.textWidth(ui.nextTime) + 10;
  useFont(g, smallFont);
  if (xr < x + maxW - 20) say(g, fitWidth(g, ui.nextRoom, x + maxW - xr).c_str(), xr, r.y + 36, MUTED);
}

void homeStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  halo(g, 1, sinf(t * 1.6f) * 0.5f);
  stars(g, t, false);
  shadow(g, 0);
  float lift;
  if (const uint8_t *waking = wakeFrame(ui.wake, lift)) {
    drawOwl(g, waking, BIG_X, BIG_Y + breath(t) - (int)lift, BIG);
    wakeDecor(g, ui.wake);
    return;
  }
  // melambai sebentar tiap 12 s supaya tetap terasa hidup
  float w = fmodf(t, 12.0f);
  const uint8_t *frame =
      (w > 8.0f && w < 9.1f) ? (((int)((w - 8.0f) / 0.17f) % 2) ? OWL_WAVE_2 : OWL_WAVE_1) : alive(t, OWL_IDLE);
  drawOwl(g, frame, BIG_X, BIG_Y + breath(t), BIG);
}

// ---------------------------------------------------------------- mendengarkan

// Batang suara kiri-kanan; tinggi mengikuti level mikrofon, terang bila cukup keras.
void soundBars(lgfx::LovyanGFX &g, float t, float level) {
  float norm = clamp01((level + 60) / 45);
  bool loud = level >= SPEECH_DBFS;
  static const float profile[5] = {0.45f, 0.65f, 0.85f, 1.0f, 0.75f};  // luar -> dalam
  for (int side = -1; side <= 1; side += 2) {
    for (int i = 0; i < 5; i++) {
      float wob = 0.55f + 0.45f * fabsf(sinf(t * 8.5f + i * 1.7f + (side > 0 ? 0.9f : 0)));
      int cells = 2 + (int)(norm * 15 * profile[i] * wob);
      int h = cells * CELL;
      int x = side < 0 ? 92 + i * 12 : W - 92 - 8 - i * 12;
      uint16_t c = loud ? (i == 3 ? MINT : TEAL) : TEAL_DIM;
      g.fillRect(x, HALO_Y - h / 2, 8, h, c);
    }
  }
}

void listenStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  float norm = clamp01((ui.level + 60) / 45);
  halo(g, 1, norm * 2.5f);
  soundBars(g, t, ui.level);
  shadow(g, 0);
  if (ui.wake >= 0 && ui.wake < 1.0f) {  // dibangunkan sambil langsung bertanya: kaget sebentar
    float lift = sinf(clamp01(ui.wake / 0.45f) * PI_F) * 14;
    drawOwl(g, OWL_SURPRISED, BIG_X, BIG_Y - (int)lift, BIG);
    glyph(g, BANG_GLYPH, 5, 330, 30 - (int)(lift / 2), 4, GOLD);
    return;
  }
  drawOwl(g, alive(t, OWL_LISTEN, false), BIG_X, BIG_Y + breath(t, 1), BIG);
}

void listenTitle(lgfx::LovyanGFX &g, const Ui &ui) {
  char timer[12];
  uint32_t s = ui.elapsedMs / 1000;
  snprintf(timer, sizeof timer, "%lu:%02lu", (unsigned long)(s / 60), (unsigned long)(s % 60));
  useFont(g, headFont);
  const char *label = tr("Mendengarkan", "Listening");
  int wl = g.textWidth(label), wt = g.textWidth(timer);
  int x = W / 2 - (16 + 10 + wl + 16 + wt) / 2;
  if (fmodf(ui.t, 1.0f) < 0.6f) {  // titik rekam berkedip
    g.fillRect(x + 2, LINE1_Y - 6, 12, 12, REC);
    g.fillRect(x, LINE1_Y - 4, 16, 8, REC);
    g.fillRect(x + 4, LINE1_Y - 8, 8, 16, REC);
  }
  say(g, label, x + 26, LINE1_Y, WHITE);
  say(g, timer, x + 26 + wl + 16, LINE1_Y, TEAL);
}

bool listenQuiet(const Ui &ui) { return ui.elapsedMs > 1500 && ui.quiet > 1.5f; }

void listenHint(lgfx::LovyanGFX &g, const Ui &ui) {
  useFont(g, textFont);
  if (listenQuiet(ui)) {
    say(g, tr("Suaramu pelan, dekatkan ke mikrofon", "Too quiet, move closer to the mic"), W / 2, LINE2_Y, GOLD, middle_center);
  } else {
    say(g, tr("Lepas tombol kalau sudah selesai", "Release the button when you're done"), W / 2, LINE2_Y, MUTED, middle_center);
  }
}

// ---------------------------------------------------------------- berpikir

void thinkStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  halo(g, 1, sinf(t * 1.6f) * 0.5f);
  stars(g, t * 0.6f, false);
  shadow(g, 0);
  const uint8_t *frame = fmodf(t + 1.0f, 3.0f) > 2.82f ? OWL_THINK_BLINK : OWL_THINK;
  drawOwl(g, frame, BIG_X, BIG_Y + breath(t, 1), BIG);
  // gelembung pikiran (awan bergelombang) dengan tiga titik bergantian naik
  cellEllipse(g, 316, 60, 1.2f, 1.2f, CLOUD);
  cellEllipse(g, 326, 48, 2.0f, 2.0f, CLOUD);
  panel(g, {334, 12, 58, 30}, CLOUD, CLOUD);
  cellEllipse(g, 346, 16, 3.0f, 2.5f, CLOUD);
  cellEllipse(g, 368, 12, 3.5f, 3.0f, CLOUD);
  cellEllipse(g, 386, 22, 2.5f, 3.0f, CLOUD);
  cellEllipse(g, 356, 40, 3.0f, 2.0f, CLOUD);
  cellEllipse(g, 378, 40, 2.5f, 2.0f, CLOUD);
  for (int i = 0; i < 3; i++) {
    float k = fmaxf(0, sinf(t * 6 - i * 0.8f));
    g.fillRect(348 + i * 12, 26 - (int)(k * 5), 8, 8, INK);
  }
}

const char *thinkText(uint32_t ms) {
  if (ms < 6000) return tr("Sebentar, aku pikirkan dulu...", "Hmm, let me think...");
  if (ms < 15000) return tr("Masih mencari jawaban...", "Still looking for the answer...");
  return tr("Hampir selesai, tunggu ya...", "Almost done, hang on...");
}

constexpr Rect THINK_BAR{W / 2 - BAR_SEGS * CELL / 2 - CELL, 280, (BAR_SEGS + 2) * CELL, 20};

void thinkBar(lgfx::LovyanGFX &g, float t) {
  int y = THINK_BAR.y + 6;
  barTrack(g, y, TRACK);
  // blok bergerak bolak-balik: menunggu tanpa persentase
  constexpr int LEN = 10;
  int from = (int)((sinf(t * 2.2f) * 0.5f + 0.5f) * (BAR_SEGS - LEN) + 0.5f);
  barFill(g, y, from, LEN, TEAL, MINT);
}

// ---------------------------------------------------------------- jawaban & Wi-Fi

bool mouthOpen(const Ui &ui) { return ui.voice > MOUTH_DBFS; }

const uint8_t *talkFrame(const Ui &ui) {
  if (ui.speaking && mouthOpen(ui)) return OWL_TALK;
  return alive(ui.t, OWL_IDLE);
}

void smallOwl(lgfx::LovyanGFX &g, const Ui &ui) {
  drawOwl(g, talkFrame(ui), 2, -2 + breath(ui.t, 1), SMALL);
}

// Gelembung judul dengan ekor ke arah burung hantu.
void bubble(lgfx::LovyanGFX &g, const char *title, const char *sub, uint16_t subColor) {
  panel(g, BUBBLE, PANEL, PANEL_EDGE);
  // ekor bertingkat ke kiri (tepi lalu isi)
  int x = BUBBLE.x;
  g.fillRect(x - 4, 36, 6, 20, PANEL_EDGE);
  g.fillRect(x - 8, 40, 4, 12, PANEL_EDGE);
  g.fillRect(x - 12, 44, 4, 4, PANEL_EDGE);
  g.fillRect(x - 2, 38, 4, 16, PANEL);
  g.fillRect(x - 6, 42, 4, 8, PANEL);
  x = BUBBLE.x + 16;
  int maxW = BUBBLE.w - 32;
  bool hasSub = sub && *sub;
  useFont(g, headFont);
  say(g, fitWidth(g, title, maxW).c_str(), x, hasSub ? 34 : 50, GOLD);
  if (hasSub) {
    useFont(g, smallFont);
    say(g, fitWidth(g, sub, maxW).c_str(), x, 66, subColor);
  }
}

void answerCard(lgfx::LovyanGFX &g, const Ui &ui) {
  panel(g, CARD, PANEL, PANEL_EDGE);
  // satukan baris server jadi butir: "- " memulai butir, "  " melanjutkan butir sebelumnya
  std::string items[MAX_LINES];
  int n = 0;
  for (int i = 0; i < ui.lineCount; i++) {
    const char *l = ui.lines[i];
    if (l[0] == ' ' && l[1] == ' ' && n > 0) {
      while (*l == ' ') l++;
      if (strcmp(l, "...") != 0) items[n - 1] += std::string(" ") + l;
    } else if (n < MAX_LINES) {
      if (l[0] == '-' && l[1] == ' ') l += 2;
      if (*l) items[n++] = l;
    }
  }
  constexpr int PAD = 20, BULLET = 18;
  int textW = CARD.w - 2 * PAD - BULLET, top = CARD.y + 14, availH = CARD.h - 28;
  // font biasa bila muat, kecil bila tidak, terakhir dipotong dengan "..."
  Font *font = &textFont;
  int lineH = 26;
  for (int pass = 0; pass < 2; pass++) {
    useFont(g, *font);
    int total = 0;
    for (int i = 0; i < n; i++) total += wrap(g, items[i].c_str(), textW, nullptr, 0);
    if (total * lineH <= availH || pass == 1) break;
    font = &smallFont;
    lineH = 22;
  }
  useFont(g, *font);
  int maxRows = availH / lineH, row = 0;
  for (int i = 0; i < n && row < maxRows; i++) {
    std::string parts[MAX_LINES * 2];
    int count = wrap(g, items[i].c_str(), textW, parts, MAX_LINES * 2);
    for (int k = 0; k < count && k < MAX_LINES * 2 && row < maxRows; k++, row++) {
      int y = top + row * lineH + lineH / 2;
      if (k == 0) g.fillRect(CARD.x + PAD, y - 3, 6, 6, TEAL);
      std::string s = parts[k];
      bool cut = row == maxRows - 1 && (k < count - 1 || i < n - 1);
      if (cut) s = fitWidth(g, (s + "...").c_str(), textW);
      say(g, s.c_str(), CARD.x + PAD + BULLET, y, TEXT);
    }
  }
}

void numberBadge(lgfx::LovyanGFX &g, int x, int y, const char *n) {
  cellEllipse(g, x, y, 3.2f, 3.2f, TEAL);
  useFont(g, textFont);
  say(g, n, x, y, INK, middle_center);
}

void portalCard(lgfx::LovyanGFX &g, const Ui &ui) {
  panel(g, CARD, PANEL, PANEL_EDGE);
  int x = CARD.x + 52;
  numberBadge(g, CARD.x + 26, 128, "1");
  useFont(g, textFont);
  say(g, tr("Sambungkan HP ke Wi-Fi ini:", "Connect your phone to this Wi-Fi:"), x, 128, TEXT);
  useFont(g, headFont);
  say(g, ui.ssid, x, 160, TEAL);
  int ws = g.textWidth(ui.ssid);
  useFont(g, smallFont);
  const char *pass = tr("sandi", "password");
  say(g, pass, x + ws + 16, 161, MUTED);
  int wk = g.textWidth(pass);
  useFont(g, headFont);
  say(g, ui.password, x + ws + 16 + wk + 8, 160, GOLD);

  numberBadge(g, CARD.x + 26, 204, "2");
  useFont(g, textFont);
  say(g, tr("Halaman pengaturan terbuka sendiri", "The setup page opens by itself"), x, 204, TEXT);
  useFont(g, smallFont);
  const char *orOpen = tr("atau buka", "or open");
  say(g, orOpen, x, 232, MUTED);
  int wa = g.textWidth(orOpen);
  char url[32];
  snprintf(url, sizeof url, "http://%s", ui.ip);
  useFont(g, textFont);
  say(g, url, x + wa + 8, 231, TEAL);

  g.fillRect(CARD.x + 16, 262, CARD.w - 32, 2, PANEL_EDGE);
  useFont(g, smallFont);
  say(g, tr("Tekan tombol untuk mencoba Wi-Fi lagi", "Press the button to retry Wi-Fi"), W / 2, 287, MUTED, middle_center);
}

// ---------------------------------------------------------------- pesan

const char *const QUESTION[] = {".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."};
const char *const DROP[] = {"..#.", ".##.", ".###", "####", "####", ".##."};

uint16_t toneColor(Tone tone) { return tone == Tone::Error ? CORAL : tone == Tone::Warn ? GOLD : TEAL; }

void noticeOwl(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  int cx = MID_X + OWL_W * MID / 2;
  cellEllipse(g, cx, 152, 17, 17, HALO_OUT, MID + 1);
  cellEllipse(g, cx, 152, 14, 14, HALO_IN, MID + 1);
  const uint8_t *pose = ui.tone == Tone::Error ? OWL_WORRIED : ui.tone == Tone::Warn ? OWL_CONFUSED : OWL_IDLE;
  drawOwl(g, alive(t, pose, ui.tone == Tone::Info), MID_X, MID_Y + breath(t, 1), MID);
  if (ui.tone == Tone::Warn) {  // tanda tanya terayun pelan
    int dy = (int)roundf(sinf(t * 3) * 3);
    glyph(g, QUESTION, 7, 150, 52 + dy, 4, GOLD);
  } else if (ui.tone == Tone::Error) {  // keringat menetes lalu muncul lagi
    float k = fmodf(t, 1.6f) / 1.6f;
    glyph(g, DROP, 6, 150, 70 + (int)(k * 24), 3, SKY);
  } else {
    sparkle(g, 158, 66, 1 + (int)(fmodf(t * 2, 3)), GOLD);
  }
}

void noticeText(lgfx::LovyanGFX &g, const Ui &ui) {
  std::string title[2], body[8];
  useFont(g, headFont);
  int nt = wrap(g, ui.title, NOTE_W, title, 2);
  if (nt > 2) nt = 2;
  useFont(g, smallFont);
  int nb = 0;
  for (int i = 0; i < ui.lineCount && nb < 6; i++) {
    std::string part[6];
    int c = wrap(g, ui.lines[i], NOTE_W, part, 6);
    for (int k = 0; k < c && k < 6 && nb < 6; k++) body[nb++] = part[k];
  }
  constexpr int TH = 30, BH = 24, GAP = 10;
  int total = nt * TH + (nb ? GAP + nb * BH : 0);
  int y = 152 - total / 2;
  useFont(g, headFont);
  for (int i = 0; i < nt; i++) say(g, title[i].c_str(), NOTE_X, y + i * TH + TH / 2, toneColor(ui.tone));
  y += nt * TH + GAP;
  useFont(g, smallFont);
  for (int i = 0; i < nb; i++) say(g, body[i].c_str(), NOTE_X, y + i * BH + BH / 2, i == nb - 1 && nb > 1 ? MUTED : TEXT);
}

// ---------------------------------------------------------------- perkenalan

constexpr Rect CAPTION{16, 224, 448, 64};
constexpr Rect CAPTION_AREA{16, 214, 448, 76};  // panel + ekornya ke atas
constexpr int SKIP_Y = 305;

int currentSegment(const Ui &ui) {
  if (ui.position < 0 || ui.segCount == 0) return -1;
  int k = 0;
  for (int i = 0; i < ui.segCount; i++)
    if (ui.position >= ui.segStart[i]) k = i;
  return k;
}

float segmentEnd(const Ui &ui, int i) { return i + 1 < ui.segCount ? ui.segStart[i + 1] : ui.duration; }

// Detik sejak kalimat terakhir bergerakan `g` mulai; negatif bila belum ada.
float since(const Ui &ui, Gesture g) {
  float s = -1;
  for (int i = 0; i < ui.segCount; i++)
    if (ui.segGesture[i] == g && ui.position >= ui.segStart[i]) s = ui.position - ui.segStart[i];
  return s;
}

// Jumlah huruf kalimat yang sudah "diketik": selesai pada 85% durasi kalimatnya.
int revealed(const Ui &ui, int seg) {
  if (seg < 0) return 0;
  int len = (int)strlen(ui.segText[seg]);
  float dur = segmentEnd(ui, seg) - ui.segStart[seg];
  if (dur <= 0.1f) return len;
  return (int)ceilf(clamp01((ui.position - ui.segStart[seg]) / (dur * 0.85f)) * len);
}

// Muncul dari bawah dengan sedikit memantul; nilai = geser y (piksel), < 0 = belum muncul.
int popIn(float age) {
  if (age < 0) return -1;
  return (int)((1 - easeOutBack(clamp01(age / 0.35f))) * 28);
}

// Buku terbuka; halamannya berbalik tiap 1,2 s.
void bookProp(lgfx::LovyanGFX &g, int cx, int cy, float age, float t) {
  int dy = popIn(age);
  if (dy < 0) return;
  cy += dy + (int)roundf(sinf(t * 2.6f) * 2);
  g.fillRect(cx - 34, cy - 10, 68, 34, INK);  // sampul
  g.fillRect(cx - 32, cy - 8, 64, 30, CORAL);
  for (int side = -1; side <= 1; side += 2) {  // dua halaman bergaris
    int px = side < 0 ? cx - 30 : cx - 1;
    g.fillRect(px, cy - 20, 31, 38, INK);
    g.fillRect(px + 2, cy - 18, 27, 34, PAPER);
    for (int r = 0; r < 4; r++) g.fillRect(px + 6, cy - 12 + r * 7, r == 3 ? 12 : 19, 2, INKLINE);
  }
  float p = fmodf(age, 1.2f) / 0.45f;
  if (p < 1) {  // halaman berbalik dari kanan ke kiri
    int w = (int)(27 * fabsf(cosf(p * PI_F)));
    int px = p < 0.5f ? cx + 1 : cx - 1 - w;
    if (w > 2) {
      g.fillRect(px - 2, cy - 20, w + 4, 38, INK);
      g.fillRect(px, cy - 18, w, 34, PAPER_DARK);
    }
  }
  g.fillRect(cx - 1, cy - 20, 2, 38, INK);  // punggung buku
}

// Papan klip berisi tiga tugas yang dicentang satu per satu.
void tasksProp(lgfx::LovyanGFX &g, int cx, int cy, float age) {
  int dy = popIn(age);
  if (dy < 0) return;
  cy += dy;
  g.fillRect(cx - 24, cy - 30, 48, 62, INK);
  g.fillRect(cx - 22, cy - 28, 44, 58, WOOD);
  g.fillRect(cx - 18, cy - 22, 36, 48, PAPER);
  g.fillRect(cx - 10, cy - 34, 20, 10, INK);  // penjepit
  g.fillRect(cx - 8, cy - 32, 16, 6, GOLD);
  for (int i = 0; i < 3; i++) {
    int bx = cx - 14, by = cy - 16 + i * 14;
    g.fillRect(bx, by, 10, 10, INK);
    g.fillRect(bx + 2, by + 2, 6, 6, PAPER);
    g.fillRect(cx, by + 4, i == 2 ? 10 : 14, 2, INKLINE);
    if (age > 0.4f + i * 0.45f) {  // centang
      g.fillRect(bx + 1, by + 4, 2, 2, TEAL);
      g.fillRect(bx + 3, by + 6, 2, 2, TEAL);
      g.fillRect(bx + 5, by + 4, 2, 2, TEAL);
      g.fillRect(bx + 7, by + 2, 2, 2, TEAL);
      g.fillRect(bx + 9, by, 2, 2, TEAL);
    }
  }
}

// Kertas warna-warni berjatuhan.
void confetti(lgfx::LovyanGFX &g, float age) {
  static const uint16_t colors[] = {GOLD, MINT, CORAL, TEAL, CLOUD};
  for (int i = 0; i < 20; i++) {
    float a = age - (i % 5) * 0.09f;
    if (a < 0) continue;
    int y = -8 + (int)(a * 70 + a * a * 120);
    if (y > STAGE.h) continue;
    int x = STAGE.x + 8 + (i * 61) % (STAGE.w - 16) + (int)(sinf(a * 7 + i) * 6);
    g.fillRect(x, y, i % 3 ? 6 : 4, i % 3 ? 4 : 6, colors[i % 5]);
  }
}

void introStage(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  int seg = currentSegment(ui);
  Gesture gesture = seg >= 0 ? ui.segGesture[seg] : Gesture::Talk;
  float age = seg >= 0 ? ui.position - ui.segStart[seg] : 0;
  bool open = mouthOpen(ui);

  halo(g, 1, sinf(t * 1.6f) * 0.5f);
  stars(g, t, (gesture == Gesture::Happy && age < 0.9f) || gesture == Gesture::Cheer);
  // properti di belakang burung hantu: buku tetap ada selama kalimat "tugas"
  if (gesture == Gesture::Book || gesture == Gesture::Tasks) bookProp(g, 128, 122, since(ui, Gesture::Book), t);
  if (gesture == Gesture::Tasks) tasksProp(g, 356, 118, age);
  if (gesture == Gesture::Button) buttonIcon(g, 322, 46, age, 2);

  const uint8_t *frame;
  float lift = 0;
  switch (gesture) {
    case Gesture::Wave:
      frame = (int)(age / 0.17f) % 2 ? (open ? OWL_WAVE_2_TALK : OWL_WAVE_2) : (open ? OWL_WAVE_1_TALK : OWL_WAVE_1);
      break;
    case Gesture::Happy:
      frame = open ? OWL_HAPPY_TALK : OWL_HAPPY;
      lift = sinf(clamp01(age / 0.4f) * PI_F) * 12;
      break;
    case Gesture::Cheer:
      frame = open ? OWL_HAPPY_TALK : OWL_HAPPY;
      lift = age < 1.2f ? fabsf(sinf(age * PI_F / 0.6f)) * 16 : 0;  // dua lompatan
      break;
    default:
      frame = open ? OWL_TALK : alive(t, OWL_IDLE, false);
  }
  if (seg < 0) frame = alive(t, OWL_IDLE, false);  // menunggu suara mulai
  shadow(g, lift / 60);
  drawOwl(g, frame, BIG_X, BIG_Y + breath(t) - (int)lift, BIG);
  if (gesture == Gesture::Cheer) confetti(g, age);
}

// Kalimat yang sedang diucapkan, "diketik" sampai `shown` huruf. Posisi tiap baris dihitung
// dari kalimat utuh supaya teks tidak bergeser saat huruf bertambah.
void caption(lgfx::LovyanGFX &g, const Ui &ui, int seg, int shown) {
  panel(g, CAPTION, PANEL, PANEL_EDGE);
  g.fillRect(W / 2 - 8, CAPTION.y - 4, 16, 6, PANEL_EDGE);  // ekor ke arah burung hantu
  g.fillRect(W / 2 - 4, CAPTION.y - 8, 8, 4, PANEL_EDGE);
  g.fillRect(W / 2 - 6, CAPTION.y - 2, 12, 4, PANEL);
  g.fillRect(W / 2 - 2, CAPTION.y - 6, 4, 4, PANEL);
  if (seg < 0) return;
  useFont(g, headFont);
  std::string lines[3];
  int n = wrap(g, ui.segText[seg], CAPTION.w - 40, lines, 3);
  if (n > 2) n = 2;
  int y = CAPTION.y + CAPTION.h / 2 - (n - 1) * 13;
  for (int i = 0; i < n; i++, y += 26) {
    int x = W / 2 - g.textWidth(lines[i].c_str()) / 2;
    int take = shown < 0 ? 0 : (shown < (int)lines[i].size() ? shown : (int)lines[i].size());
    say(g, lines[i].substr(0, take).c_str(), x, y, WHITE);
    shown -= (int)lines[i].size() + 1;  // +1: spasi yang hilang saat dibungkus
  }
}

// ---------------------------------------------------------------- pemberitahuan

// Tata letak bersama: ikon besar + judul di kiri atas, kartu rincian di kiri, burung hantu
// (3x) di kanan, sisa waktu di bawah.
constexpr Rect ALERT_ICON{0, 0, 108, 104};
constexpr Rect ALERT_CARD{16, 108, 280, 112};
constexpr Rect ALERT_OWL{296, 58, 184, 170};  // di bawah judul supaya judul tidak tertimpa
constexpr Rect ALERT_FOOT{16, 228, 448, 58};
constexpr int ALERT_TEXT_X = 116, ALERT_OWL_X = 298, ALERT_OWL_Y = 62, ALERT_HINT_Y = 304;
constexpr uint16_t GOLD_DARK = rgb(0xD8901F), GOLD_LIGHT = rgb(0xFFE89A), GREEN = rgb(0x3FE08A);

const char *const BELL[] = {"....oo....", "...oggo...", "..oghggo..", ".oghgggdo.", ".oghgggdo.",
                            ".ohggggdo.", ".ogggggdo.", "oggggggddo", "oooooooooo"};
const char *const CLAPPER[] = {".oo.", "oddo", ".oo."};
const char *const PIN[] = {".###.", "#####", "##.##", "#####", ".###.", "..#..", "..#.."};
const char *const QR[] = {"###.###", "#.#.#.#", "###.###", ".......", "###.#.#", "#.#..#.", "###.#.#"};
const char *const PHONE[] = {"#####", "#...#", "#...#", "#...#", "#...#", "#####", "##.##"};
const char *const CLOCK[] = {"..###..", ".#...#.", "#.....#", "#..#..#", "#.....#", ".#...#.", "..###.."};
const char *const CHECK[] = {"........#", ".......##", "#.....##.", "##...##..", ".##.##...", "..###....", "...#....."};
const char *const BIG_CAL[] = {"..o....o..", "rrorrrrorr", "rrrrrrrrrr", "rrrrrrrrrr", "wwwwwwwwww",
                               "wwwwwwwwww", "wwwwwwwwww", "wwwwwwwwww", "wwwwwwwwww", "wwwwwwwwww"};

int32_t bellColor(char c) {
  switch (c) {
    case 'o': return INK;
    case 'g': return GOLD;
    case 'd': return GOLD_DARK;
    case 'h': return GOLD_LIGHT;
  }
  return -1;
}

// Jam kecil (7x7 kotak) dengan jarum yang menunjuk salah satu dari 8 arah.
void clockIcon(lgfx::LovyanGFX &g, int x, int y, int cell, int dir, uint16_t color) {
  static const int dx[8] = {0, 1, 1, 1, 0, -1, -1, -1}, dy[8] = {-1, -1, 0, 1, 1, 1, 0, -1};
  glyph(g, CLOCK, 7, x, y, cell, color);
  for (int k = 1; k <= 2; k++) g.fillRect(x + (3 + dx[dir & 7] * k) * cell, y + (3 + dy[dir & 7] * k) * cell, cell, cell, color);
}

// Sisa waktu sebagai detik; INT32_MIN bila jam belum diketahui.
int32_t secondsLeft(const Ui &ui) { return ui.nowTs && ui.alertTo ? (int32_t)(ui.alertTo - ui.nowTs) : INT32_MIN; }

// Baris bawah: label sisa waktu + bar yang menyusut, berubah warna makin mendesak.
void alertFoot(lgfx::LovyanGFX &g, const Ui &ui, float total, bool deadline) {
  const Rect &r = ALERT_FOOT;
  int32_t s = secondsLeft(ui);
  char text[40], d[24];
  if (s == INT32_MIN) {
    snprintf(text, sizeof text, "%s", ui.alertWhen);
  } else if (s <= 0) {
    snprintf(text, sizeof text, "%s",
             deadline ? tr("Sudah lewat", "Past due") : tr("Presensi sudah tutup", "Attendance closed"));
  } else {
    duration(d, sizeof d, s);
    snprintf(text, sizeof text, deadline ? tr("%s lagi", "%s left") : tr("Sisa %s", "%s left"), d);
  }
  float frac = s == INT32_MIN ? 1 : clamp01(s / total);
  bool blink = frac < 0.15f && fmodf(ui.t, 0.8f) < 0.4f;
  uint16_t color = frac > 0.5f ? TEAL : (frac > 0.2f ? GOLD : CORAL);
  clockIcon(g, r.x + 8, r.y + 4, 3, (int)(ui.t * 2) & 7, blink ? WHITE : color);
  useFont(g, headFont);
  say(g, text, r.x + 38, r.y + 15, blink ? WHITE : color);
  // bar kotak-kotak
  constexpr int SEGS = 105;
  int bx = r.x + 6, by = r.y + 36, on = (int)(frac * SEGS + 0.999f);
  g.fillRect(bx - 4, by - 4, SEGS * 4 + 8, 18, INK);
  g.fillRect(bx, by, SEGS * 4, 10, TRACK);
  if (on > 0) {
    g.fillRect(bx, by, on * 4, 10, color);
    g.fillRect(bx, by, on * 4, 2, mix(color, WHITE, 0.45f));
  }
}

// -- presensi dibuka: lonceng berayun dengan riak, burung hantu melambai heboh

void bellIcon(lgfx::LovyanGFX &g, float t) {
  float phase = fmodf(t, 1.6f);
  bool ringing = phase < 0.9f;
  int swing = ringing ? (int)roundf(sinf(t * 18) * 5 * (1 - phase / 0.9f)) : 0;
  int bx = 24 + swing, by = 22, cx = 54, cy = 50;
  for (int k = 0; k < 2; k++) {  // riak gelombang bunyi
    float age = fmodf(t + k * 0.8f, 1.6f) / 1.6f;
    cellRing(g, cx, cy, 6 + age * 6, mix(bgAt(cy), GOLD, (1 - age) * 0.55f), 4);
  }
  art(g, CLAPPER, 3, bx + 18 - swing / 2, by + 48, 6, bellColor);
  art(g, BELL, 9, bx, by, 6, bellColor);
  if (ringing && fmodf(t, 0.2f) < 0.1f) {  // garis getar di kiri-kanan
    for (int i = 0; i < 3; i++) {
      g.fillRect(4, by + 8 + i * 12, 10, 4, GOLD);
      g.fillRect(96, by + 8 + i * 12, 10, 4, GOLD);
    }
  }
}

void alertOwl(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  const uint8_t *frame;
  int lift = 0;
  int cx = ALERT_OWL_X + OWL_W * MID / 2;
  cellEllipse(g, cx, 150, 17, 17, HALO_OUT, MID + 1);
  cellEllipse(g, cx, 150, 14, 14, HALO_IN, MID + 1);
  switch (ui.alert) {
    case Alert::Attendance:  // melambai cepat sambil "bicara": ayo isi!
      frame = (int)(t / 0.14f) % 2 ? OWL_WAVE_2_TALK : OWL_WAVE_1;
      lift = (int)(fabsf(sinf(t * 6)) * 6);
      sparkle(g, cx - 70, 70 + (int)(sinf(t * 4) * 4), 2 + (int)(fmodf(t * 3, 2)), GOLD);
      sparkle(g, cx + 66, 96, 2 + (int)(fmodf(t * 3 + 1, 2)), MINT);
      break;
    case Alert::Attended:  // senang melompat
      frame = OWL_HAPPY;
      lift = (int)(fabsf(sinf(t * 4.5f)) * 12);
      break;
    case Alert::Review:  // menyemangati: melambai pelan
      frame = (int)(t / 0.35f) % 2 ? OWL_WAVE_2 : OWL_WAVE_1;
      lift = (int)(fabsf(sinf(t * 3)) * 4);
      sparkle(g, cx + 66, 84, 2 + (int)(fmodf(t * 3, 2)), GOLD);
      break;
    default: {  // deadline & peringatan: cemas, keringat menetes
      frame = alive(t, OWL_WORRIED, false);
      float k = fmodf(t, 1.4f) / 1.4f;
      glyph(g, DROP, 6, cx + 54, 64 + (int)(k * 26), 3, SKY);
    }
  }
  drawOwl(g, frame, ALERT_OWL_X, ALERT_OWL_Y - lift, MID);
}

void attendanceCard(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = ALERT_CARD;
  panel(g, r, PANEL, PANEL_EDGE);
  int x = r.x + 46, w = r.w - 58;
  glyph(g, PIN, 7, r.x + 16, r.y + 12, 3, CORAL);
  useFont(g, textFont);
  say(g, fitWidth(g, ui.alertDetail[0] ? ui.alertDetail : tr("Ruang kelas", "Classroom"), w).c_str(), x, r.y + 22, TEXT);
  if (ui.alertQr) {
    glyph(g, QR, 7, r.x + 14, r.y + 46, 3, WHITE);
    say(g, tr("Scan QR di kelas", "Scan the QR in class"), x, r.y + 56, TEXT);
  } else {
    glyph(g, PHONE, 7, r.x + 17, r.y + 46, 3, WHITE);
    say(g, tr("Isi di portal SATU", "Fill it in on SATU"), x, r.y + 56, TEXT);
  }
  clockIcon(g, r.x + 14, r.y + 80, 3, 1, GOLD);
  say(g, ui.alertWhen, x, r.y + 90, GOLD);
}

// -- presensi tercatat: cap "HADIR" dihentakkan

void stamp(lgfx::LovyanGFX &g, float t) {
  constexpr int CX = 352, CY = 92, R = 56;
  float k = clamp01(t / 0.22f);  // turun dari "udara"
  int cell = k < 1 ? 6 : 4;
  int shake = (t > 0.22f && t < 0.4f) ? ((int)(t * 40) % 2 ? 3 : -3) : 0;
  uint16_t color = k < 1 ? mix(bgAt(CY), GREEN, 0.45f) : GREEN;
  int cx = CX + shake;
  cellRing(g, cx, CY, (float)R / cell, color, cell);
  cellRing(g, cx, CY, (float)(R - 10) / cell, color, cell);
  int cw = 9 * cell, ch = 7 * cell;
  glyph(g, CHECK, 7, cx - cw / 2, CY - ch / 2 - 8, cell, color);
  if (k >= 1) {
    useFont(g, smallFont);
    say(g, tr("HADIR", "HERE"), cx, CY + 26, GREEN, middle_center);
    float p = clamp01((t - 0.3f) / 0.5f);  // percikan bintang setelah cap mendarat
    if (p > 0 && p < 1) {
      int d = (int)(R + 6 + p * 18), size = p < 0.6f ? 3 : 2;
      sparkle(g, cx - d, CY - d / 2, size, GOLD);
      sparkle(g, cx + d, CY - d / 2, size, MINT);
      sparkle(g, cx - d / 2, CY + d, size, MINT);
      sparkle(g, cx + d / 2, CY + d, size, GOLD);
    }
  }
}

// -- deadline: kalender bertanggal dengan lencana "!"

void calendarIcon(lgfx::LovyanGFX &g, const Ui &ui) {
  static const char *const MONTHS[] = {"JAN", "FEB", "MAR", "APR", "MEI", "JUN",
                                       "JUL", "AGU", "SEP", "OKT", "NOV", "DES"};
  static const char *const MONTHS_EN[] = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                                          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};
  float t = ui.t;
  float b = fmodf(t, 1.2f);
  int shake = b < 0.3f ? ((int)(t * 30) % 2 ? 2 : -2) : 0;
  int x = 24 + shake, y = 18;
  g.fillRect(x - 2, y + 4, 64, 54, INK);  // garis tepi
  art(g, BIG_CAL, 10, x, y, 6, [](char c) -> int32_t {
    switch (c) {
      case 'o': return INK;
      case 'r': return CAL_RED;
      case 'w': return PAPER;
    }
    return -1;
  });
  if (ui.alertTo) {
    time_t local = (time_t)ui.alertTo + 7 * 3600;  // WIB
    struct tm tm;
    gmtime_r(&local, &tm);
    char day[4];
    snprintf(day, sizeof day, "%d", tm.tm_mday);
    useFont(g, smallFont);
    say(g, (english ? MONTHS_EN : MONTHS)[tm.tm_mon % 12], x + 30, y + 17, WHITE, middle_center);
    useFont(g, headFont);
    say(g, day, x + 30, y + 42, INK, middle_center);
  }
  // lencana "!" memantul di sudut kanan atas
  int by = 6 - (int)(fabsf(sinf(t * 5)) * 6);
  cellEllipse(g, x + 62, by + 12, 3, 3, CORAL, 4);
  g.fillRect(x + 60, by + 4, 4, 10, WHITE);
  g.fillRect(x + 60, by + 16, 4, 4, WHITE);
}

void deadlineCard(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = ALERT_CARD;
  panel(g, r, PANEL, PANEL_EDGE);
  int x = r.x + 16, w = r.w - 32;
  std::string lines[3];
  useFont(g, textFont);
  int n = wrap(g, ui.alertDetail, w, lines, 3);
  if (n > 2) lines[1] = fitWidth(g, (lines[1] + " " + lines[2]).c_str(), w);
  for (int i = 0; i < n && i < 2; i++) say(g, lines[i].c_str(), x, r.y + 22 + i * 26, WHITE);
  clockIcon(g, x - 2, r.y + 78, 3, 2, CORAL);
  say(g, ui.alertWhen, x + 30, r.y + 88, CORAL);
}

const char *deadlineTitle(const Ui &ui) {
  if (!strncmp(ui.alertWhen, "Hari ini", 8) || !strncmp(ui.alertWhen, "Today", 5))
    return tr("Deadline hari ini!", "Due today!");
  if (!strncmp(ui.alertWhen, "Besok", 5) || !strncmp(ui.alertWhen, "Tomorrow", 8))
    return tr("Deadline besok!", "Due tomorrow!");
  return tr("Deadline mendekat", "Deadline coming up");
}

// -- peringatan dini: segitiga "!" berdenyut (kehadiran mendekati batas, anggaran menipis)

const char *const WARN_SIGN[] = {".....yy.....", "....yyyy....", "....yyyy....", "...yyyyyy...",
                                 "...yykkyy...", "..yyykkyyy..", "..yyykkyyy..", ".yyyykkyyyy.",
                                 ".yyyyyyyyyy.", "yyyyykkyyyyy", "yyyyyyyyyyyy"};

void warningIcon(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  uint16_t fill = ui.alertHigh ? CORAL : GOLD;
  int x = 18, y = 18, cx = 54, cy = 51;
  for (int k = 0; k < 2; k++) {  // denyut cincin di belakang tanda
    float age = fmodf(t + k * 0.7f, 1.4f) / 1.4f;
    cellRing(g, cx, cy, 6 + age * 7, mix(bgAt(cy), fill, (1 - age) * 0.5f), 4);
  }
  int bump = fmodf(t, 1.4f) < 0.12f ? -3 : 0;
  art(g, WARN_SIGN, 11, x, y + bump, 6, [fill](char c) -> int32_t {
    switch (c) {
      case 'y': return fill;
      case 'k': return INK;
    }
    return -1;
  });
}

void warningCard(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = ALERT_CARD;
  panel(g, r, PANEL, PANEL_EDGE);
  int x = r.x + 16, w = r.w - 32;
  std::string lines[2];
  useFont(g, textFont);
  int n = wrap(g, ui.alertDetail[0] ? ui.alertDetail : tr("Perlu perhatian", "Needs attention"), w, lines, 2);
  for (int i = 0; i < n && i < 2; i++) say(g, lines[i].c_str(), x, r.y + 22 + i * 26, WHITE);
  useFont(g, smallFont);
  say(g, tr("Detail ada di dashboard", "Details are on the dashboard"), x, r.y + 88, MUTED);
}

// -- waktunya mengulang: buku terbuka berkilau + meter penguasaan topik

const char *const BOOK[] = {".pppp..pppp.", "pwwwwppwwwwp", "pwkkwppwkkwp", "pwwwwppwwwwp", "pwkkkppkkkwp",
                            "pwwwwppwwwwp", "pwkkwppwkkwp", "pwwwwppwwwwp", "pppppppppppp"};

void bookIcon(lgfx::LovyanGFX &g, float t) {
  int lift = (int)(fabsf(sinf(t * 2.5f)) * 5);
  art(g, BOOK, 9, 18, 26 - lift, 6, [](char c) -> int32_t {
    switch (c) {
      case 'p': return TEAL;
      case 'w': return PAPER;
      case 'k': return INKLINE;
    }
    return -1;
  });
  sparkle(g, 14, 18, 1 + (int)fmodf(t * 3, 3), GOLD);
  sparkle(g, 96, 30, 1 + (int)fmodf(t * 3 + 1, 3), MINT);
  sparkle(g, 92, 86, 1 + (int)fmodf(t * 3 + 2, 2), GOLD);
}

// "Penguasaan 40%" / "Mastery 40%" -> 40; -1 bila tidak ada angka.
int percentIn(const char *text) {
  for (const char *p = text; *p; p++)
    if (*p >= '0' && *p <= '9') return atoi(p);
  return -1;
}

void reviewCard(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = ALERT_CARD;
  panel(g, r, PANEL, PANEL_EDGE);
  int x = r.x + 16, w = r.w - 32;
  std::string lines[2];
  useFont(g, textFont);
  int n = wrap(g, ui.alertDetail[0] ? ui.alertDetail : tr("Topik kuis", "Quiz topic"), w, lines, 2);
  for (int i = 0; i < n && i < 2; i++) say(g, lines[i].c_str(), x, r.y + 22 + i * 26, WHITE);
  int pct = percentIn(ui.alertWhen);
  useFont(g, smallFont);
  say(g, ui.alertWhen, x, r.y + 82, pct >= 0 && pct < 60 ? GOLD : MINT);
  if (pct >= 0) {  // meter kotak-kotak
    constexpr int SEGS = 20;
    int bx = x + 150, by = r.y + 76, on = (pct * SEGS + 99) / 100;
    g.fillRect(bx, by, SEGS * 4, 10, TRACK);
    if (on > 0) g.fillRect(bx, by, on * 4, 10, pct < 60 ? GOLD : MINT);
  }
}

// Baris bawah untuk peringatan/pengulangan: ajakan bicara (tanpa hitung mundur).
void hintFoot(lgfx::LovyanGFX &g, const Ui &ui) {
  const Rect &r = ALERT_FOOT;
  bool review = ui.alert == Alert::Review;
  useFont(g, headFont);
  say(g,
      review ? tr("Tahan tombol: \"uji aku lagi\"", "Hold the button: \"quiz me again\"")
             : tr("Tahan tombol lalu tanya EduPad", "Hold the button and ask EduPad"),
      r.x + 6, r.y + 15, review ? MINT : TEAL);
  useFont(g, smallFont);
  say(g,
      review ? tr("SORA menyiapkan kuis lisan dari materi asli", "SORA prepares a spoken quiz from the real material")
             : tr("\"apa yang perlu aku perhatikan?\"", "\"what should I watch out for?\""),
      r.x + 6, r.y + 42, MUTED);
}

// ---------------------------------------------------------------- notifikasi kecil

void toast(lgfx::LovyanGFX &g, const Ui &ui) {
  if (ui.toastT < 0 || ui.toastT >= TOAST_SECONDS || !ui.toast[0]) return;
  useFont(g, smallFont);
  int w = g.textWidth(ui.toast) + 40;
  Rect r{W / 2 - w / 2, H - 44, w, 32};
  panel(g, r, rgb(0x2B3A86), MINT);
  say(g, ui.toast, W / 2, r.y + 16, TEXT, middle_center);
}

}  // namespace

void begin(bool psram) {
  load(logoFont, ui_black_44, sizeof ui_black_44);
  load(headFont, ui_bold_22, sizeof ui_bold_22);
  load(textFont, ui_semibold_19, sizeof ui_semibold_19);
  load(smallFont, ui_semibold_16, sizeof ui_semibold_16);
  bgCache.setColorDepth(16);
  bgCache.setPsram(psram);
  if (bgCache.createSprite(W, H)) drawGradient(bgCache);
}

void background(lgfx::LovyanGFX &g) {
  if (bgCache.getBuffer()) {
    bgCache.pushSprite(&g, 0, 0);
    return;
  }
  int32_t x, y, w, h;
  g.getClipRect(&x, &y, &w, &h);
  for (int row = y; row < y + h; row++) g.drawFastHLine(x, row, w, bgAt(row));
}

void render(lgfx::LovyanGFX &canvas, const Ui &ui, bool full, void (*push)(const Rect &area)) {
  // Gambar ulang satu area: latar dulu, lalu isinya; kirim ke LCD bila bukan gambar penuh.
  auto area = [&](const Rect &r, auto draw) {
    canvas.setClipRect(r.x, r.y, r.w, r.h);
    background(canvas);
    draw();
    canvas.clearClipRect();
    if (!full) push(r);
  };
  english = ui.english;
  // Kunci isi baris teks yang hanya digambar ulang saat berubah.
  static int lastKey1, lastKey2;
  if (full) {
    canvas.clearClipRect();
    background(canvas);
    lastKey1 = lastKey2 = -1;
  }

  switch (ui.kind) {
    case Kind::Boot:
      area(STAGE, [&] { bootStage(canvas, ui); });
      if (full || ui.t < 1.3f) area(LINE1, [&] { bootTitle(canvas, ui.t); });
      area(LINE2, [&] { bootStatus(canvas, ui); });
      break;

    case Kind::Home: {
      // Baru dibangunkan dari kamar tidur: kaget di ranjang dulu, lalu layar siap.
      static bool inRoom;
      bool room = ui.wake >= 0 && ui.wake < WAKE_ROOM_SECONDS;
      if (room != inRoom && !full) {  // kamar <-> layar siap: gambar ulang seluruh layar
        canvas.clearClipRect();
        background(canvas);
        full = true;
      }
      inRoom = room;
      if (room) {
        if (full) {
          bedroom(canvas, 0, true, ui.wake);
        } else {
          area(BANG_AREA, [&] { bedroom(canvas, 0, true, ui.wake); });
        }
        break;
      }
      area(STAGE, [&] { homeStage(canvas, ui); });
      int titleY = ui.hasNext ? NEXT_TITLE_Y : LINE1_Y;
      if (full) {
        area(LINE1, [&] { homeTitle(canvas, ui.t, true, titleY); });
        if (ui.hasNext) {
          nextCard(canvas, ui);
          homeHint(canvas, ui, NEXT_HINT_Y);
          lastKey2 = nextCardKey(ui);
        } else {
          area(LINE2, [&] { homeHint(canvas, ui); });
        }
      } else {
        Rect icon{homeIconX - 4, titleY - 24, ICON_W + 8, ICON_H};
        area(icon, [&] { homeTitle(canvas, ui.t, false, titleY); });
        int key = ui.hasNext ? nextCardKey(ui) : 0;
        if (ui.hasNext && key != lastKey2) area(NEXT_CARD, [&] { nextCard(canvas, ui); });
        lastKey2 = key;
      }
      break;
    }

    case Kind::Listen: {
      area(STAGE, [&] { listenStage(canvas, ui); });
      int key1 = (int)(ui.elapsedMs / 1000) * 2 + (fmodf(ui.t, 1.0f) < 0.6f);
      if (key1 != lastKey1) area(LINE1, [&] { listenTitle(canvas, ui); });
      lastKey1 = key1;
      int key2 = listenQuiet(ui);
      if (key2 != lastKey2) area(LINE2, [&] { listenHint(canvas, ui); });
      lastKey2 = key2;
      break;
    }

    case Kind::Think: {
      area(STAGE, [&] { thinkStage(canvas, ui); });
      const char *text = thinkText(ui.elapsedMs);
      int key1 = (int)(intptr_t)text & 0xFFFF;
      if (key1 != lastKey1) {
        area(LINE1, [&] {
          useFont(canvas, headFont);
          say(canvas, text, W / 2, LINE1_Y, WHITE, middle_center);
        });
      }
      lastKey1 = key1;
      area(THINK_BAR, [&] { thinkBar(canvas, ui.t); });
      break;
    }

    case Kind::Answer:
      if (full) {
        char sub[110] = "";
        if (ui.subtitle[0]) snprintf(sub, sizeof sub, tr("Kamu: %s", "You: %s"), ui.subtitle);
        bubble(canvas, ui.title, sub, MUTED);
        answerCard(canvas, ui);
      }
      area(OWL_SMALL, [&] { smallOwl(canvas, ui); });
      break;

    case Kind::Portal:
      if (full) {
        char sub[128];
        if (ui.subtitle[0]) snprintf(sub, sizeof sub, tr("Gagal tersambung ke %s", "Couldn't connect to %s"), ui.subtitle);
        bubble(canvas, tr("Atur Wi-Fi dulu, ya", "Let's set up Wi-Fi"),
               ui.subtitle[0] ? sub : tr("Belum ada Wi-Fi yang tersimpan", "No saved Wi-Fi yet"),
               ui.subtitle[0] ? CORAL : MUTED);
        portalCard(canvas, ui);
      }
      area(OWL_SMALL, [&] { smallOwl(canvas, ui); });
      break;

    case Kind::Notice:
      if (full) noticeText(canvas, ui);
      area(OWL_MID, [&] { noticeOwl(canvas, ui); });
      break;

    case Kind::Sleep: {
      static bool roomShown;
      if (full) roomShown = false;
      if (ui.t < ROOM_AT) {
        area(STAGE, [&] { dozeStage(canvas, ui); });
        if (full) {
          useFont(canvas, headFont);
          say(canvas, tr("Hoaam... aku ngantuk", "Yaawn... I'm sleepy"), W / 2, LINE1_Y, MUTED, middle_center);
        }
        break;
      }
      if (!roomShown) {  // pindah ke kamar: seluruh layar digambar sekali
        canvas.clearClipRect();
        bedroom(canvas, ui.t);
        roomShown = true;
        if (!full) push({0, 0, W, H});
        break;
      }
      area(ZZZ_AREA, [&] { bedroom(canvas, ui.t); });
      break;
    }

    case Kind::Alert: {
      bool attend = ui.alert == Alert::Attendance, done = ui.alert == Alert::Attended;
      bool warn = ui.alert == Alert::Warning, review = ui.alert == Alert::Review;
      if (full) {
        useFont(canvas, headFont);
        if (done) {
          say(canvas, tr("Presensi tercatat!", "Attendance recorded!"), 352, 176, GREEN, middle_center);
          useFont(canvas, textFont);
          say(canvas, fitWidth(canvas, ui.alertCourse, 250).c_str(), 352, 206, WHITE, middle_center);
          char sub[sizeof ui.alertWhen + sizeof ui.alertDetail + 4];
          snprintf(sub, sizeof sub, "%s%s%s", ui.alertWhen, ui.alertDetail[0] ? " - " : "", ui.alertDetail);
          useFont(canvas, smallFont);
          say(canvas, fitWidth(canvas, sub, 250).c_str(), 352, 232, MUTED, middle_center);
        } else {
          const char *title = attend ? tr("PRESENSI DIBUKA!", "ATTENDANCE OPEN!")
                              : warn   ? tr("PERINGATAN DINI", "EARLY WARNING")
                              : review ? tr("WAKTUNYA MENGULANG", "TIME TO REVIEW")
                                       : deadlineTitle(ui);
          uint16_t titleColor = attend ? GOLD : warn ? (ui.alertHigh ? CORAL : GOLD) : review ? MINT : CORAL;
          say(canvas, title, ALERT_TEXT_X, 36, titleColor);
          say(canvas, fitWidth(canvas, ui.alertCourse, ALERT_OWL.x - ALERT_TEXT_X).c_str(), ALERT_TEXT_X, 70,
              attend ? WHITE : GOLD);
          if (attend) {
            attendanceCard(canvas, ui);
          } else if (warn) {
            warningCard(canvas, ui);
          } else if (review) {
            reviewCard(canvas, ui);
          } else {
            deadlineCard(canvas, ui);
          }
          if (warn || review) hintFoot(canvas, ui);
        }
        useFont(canvas, smallFont);
        say(canvas, tr("Tekan tombol untuk menutup", "Press the button to close"), W / 2, ALERT_HINT_Y, MUTED, middle_center);
      }
      if (done) {
        area({0, 40, 200, 220}, [&] {  // burung hantu di kiri untuk layar "tercatat"
          int cx = 98;
          cellEllipse(canvas, cx, 150, 17, 17, HALO_OUT, MID + 1);
          cellEllipse(canvas, cx, 150, 14, 14, HALO_IN, MID + 1);
          drawOwl(canvas, OWL_HAPPY, 8, 72 - (int)(fabsf(sinf(ui.t * 4.5f)) * 12), MID);
        });
        if (ui.t < 1.4f || full) area({272, 6, 168, 160}, [&] { stamp(canvas, ui.t); });
        break;
      }
      area(ALERT_OWL, [&] { alertOwl(canvas, ui); });
      area(ALERT_ICON, [&] {
        if (attend) {
          bellIcon(canvas, ui.t);
        } else if (warn) {
          warningIcon(canvas, ui);
        } else if (review) {
          bookIcon(canvas, ui.t);
        } else {
          calendarIcon(canvas, ui);
        }
      });
      if (warn || review) break;  // tanpa hitung mundur; petunjuk bawah digambar sekali
      // sisa waktu: digambar ulang tiap detik (dan saat berkedip)
      int32_t left = secondsLeft(ui);
      int key = (left == INT32_MIN ? 0 : left) * 2 + (fmodf(ui.t, 0.8f) < 0.4f);
      if (key != lastKey1 || full) {
        float total = attend ? (ui.alertTo > ui.alertFrom ? (float)(ui.alertTo - ui.alertFrom) : 1800) : 48 * 3600;
        area(ALERT_FOOT, [&] { alertFoot(canvas, ui, total, !attend); });
      }
      lastKey1 = key;
      break;
    }

    case Kind::Intro: {
      area(STAGE, [&] { introStage(canvas, ui); });
      int seg = currentSegment(ui), shown = revealed(ui, seg);
      int key1 = (seg + 1) * 1000 + shown;
      if (key1 != lastKey1) area(CAPTION_AREA, [&] { caption(canvas, ui, seg, shown); });
      lastKey1 = key1;
      if (full) {
        useFont(canvas, smallFont);
        say(canvas, tr("Tekan tombol untuk melewati", "Press the button to skip"), W / 2, SKIP_Y, MUTED, middle_center);
      }
      break;
    }
  }

  if (full) {
    toast(canvas, ui);
    push({0, 0, W, H});
  }
}

}  // namespace scene
