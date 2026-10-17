// Eksperimen: layar EduPad bergaya Duolingo. Interface sama dengan ../../edupad/scene.h, jadi
// file ini bisa menggantikan scene.cpp firmware tanpa mengubah display.cpp.
//
// - Burung hantu tetap sprite pixel art yang sama (owl_sprites.h), tetapi digambar dengan
//   transformasi: squash & stretch, miring, lompat dengan aba-aba (jongkok -> memanjang di udara
//   -> gepeng saat mendarat -> memantul), dan getaran pegas. Tiap layar punya reaksi sendiri.
// - Latar terang, kartu membulat dengan "bibir" 3D di bawah, tombol 3D yang bisa ditekan, pill
//   progress, konfeti, dan font Nunito Black/ExtraBold (pengganti font Duolingo).
// - Tiap frame seluruh layar digambar ulang (sederhana untuk eksperimen). Di firmware, area yang
//   dikirim ke LCD perlu dibatasi lagi seperti scene.cpp asli supaya tetap lancar.
#include "scene.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <string>

#include "new_ui_fonts.h"
#include "owl_sprites.h"

namespace scene {
namespace {

constexpr uint16_t rgb(uint32_t hex) {
  return ((hex >> 8) & 0xF800) | ((hex >> 5) & 0x07E0) | ((hex >> 3) & 0x001F);
}

// Palet ala Duolingo: putih bersih, abu-abu untuk tepi, warna cerah dengan bayangan lebih gelap.
constexpr uint16_t SNOW = rgb(0xFFFFFF), POLAR = rgb(0xF7F7F7), SWAN = rgb(0xE5E5E5);
constexpr uint16_t HARE = rgb(0xAFAFAF), WOLF = rgb(0x777777), EEL = rgb(0x4B4B4B);
constexpr uint16_t GREEN = rgb(0x58CC02), GREEN_DARK = rgb(0x58A700), GREEN_PALE = rgb(0xD7FFB8);
constexpr uint16_t BLUE = rgb(0x1CB0F6), BLUE_DARK = rgb(0x1899D6), BLUE_PALE = rgb(0xDDF4FF);
constexpr uint16_t RED = rgb(0xFF4B4B), RED_DARK = rgb(0xEA2B2B), RED_PALE = rgb(0xFFDFE0);
constexpr uint16_t YELLOW = rgb(0xFFC800), YELLOW_DARK = rgb(0xE5A400), YELLOW_PALE = rgb(0xFFF4CC);
constexpr uint16_t YELLOW_TEXT = rgb(0xB87A00);
constexpr uint16_t ORANGE = rgb(0xFF9600), ORANGE_DARK = rgb(0xE07B00);
constexpr uint16_t PURPLE = rgb(0xCE82FF), PURPLE_DARK = rgb(0xA75FE0);
constexpr uint16_t NIGHT = rgb(0x152036), NIGHT_LIGHT = rgb(0x1F2D4B), MOON = rgb(0xFFE38A);
constexpr uint16_t ZBLUE = rgb(0x8FB8FF), SKIN = rgb(0xFDE3B0);

// Tema: -DNEW_UI_DARK=1 = gelap (biru malam). Warna di bawah dipakai menurut perannya, bukan
// namanya, supaya kedua tema memakai kode gambar yang sama.
#ifndef NEW_UI_DARK
#define NEW_UI_DARK 0
#endif
constexpr bool DARK = NEW_UI_DARK;
// Biru malam tema gelap; layar nyala selalu memakainya, juga di tema terang.
constexpr uint16_t NAVY = rgb(0x101B3F), NAVY_EDGE = rgb(0x2D3F78), NAVY_MUTED = rgb(0xA8B4DC);
constexpr uint16_t NAVY_GROUND = rgb(0x0A1231);
constexpr uint16_t BG = DARK ? NAVY : SNOW;                // latar layar
constexpr uint16_t SURFACE = DARK ? rgb(0x1A2853) : SNOW;  // isi kartu & gelembung
constexpr uint16_t EDGE = DARK ? NAVY_EDGE : SWAN;         // tepi kartu, jalur bar
constexpr uint16_t RAISED = DARK ? rgb(0x24356A) : POLAR;  // chip netral
constexpr uint16_t INK = DARK ? rgb(0xF1F4FF) : EEL;       // teks utama
constexpr uint16_t MUTED = DARK ? NAVY_MUTED : WOLF;       // teks kedua
constexpr uint16_t FAINT = DARK ? rgb(0x7383B8) : HARE;    // petunjuk kecil
constexpr uint16_t GROUND = DARK ? NAVY_GROUND : SWAN;     // bayangan di lantai

constexpr float PI_F = 3.14159265f;

struct Font {
  lgfx::PointerWrapper data;
  lgfx::VLWfont vlw;
};
Font logoFont, titleFont, headFont, textFont, smallFont;

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

// Latar lembut berwarna (pita pesan, layar dengar).
uint16_t pale(uint16_t c) { return mix(BG, c, DARK ? 0.2f : 0.17f); }

// ---------------------------------------------------------------- gerak

float clamp01(float x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }
float easeOutCubic(float x) { return 1 - powf(1 - clamp01(x), 3); }
float easeOutBack(float x) {
  x = clamp01(x);
  const float c1 = 1.70158f, c3 = c1 + 1;
  return 1 + c3 * powf(x - 1, 3) + c1 * powf(x - 1, 2);
}
float smooth(float x) {
  x = clamp01(x);
  return x * x * (3 - 2 * x);
}
// Muncul dengan pegas (sedikit melewati 1 lalu kembali); 0 sebelum mulai.
float pop(float age, float dur = 0.4f) { return age <= 0 ? 0 : easeOutBack(age / dur); }
// Getaran teredam setelah sebuah hentakan (age = detik sejak hentakan).
float wobble(float age, float amp, float freq = 20, float damp = 6) {
  return age < 0 ? 0 : amp * expf(-damp * age) * sinf(freq * age);
}

uint32_t hash(uint32_t x) {
  x ^= x >> 16;
  x *= 0x7feb352d;
  x ^= x >> 15;
  x *= 0x846ca68b;
  x ^= x >> 16;
  return x;
}
float rnd(int i, int k) { return (hash(i * 9781 + k * 6271 + 13) & 0xFFFF) / 65535.0f; }

// ---------------------------------------------------------------- burung hantu

// Pose sprite: posisi kaki di layar, skala dasar, squash & stretch di sekitar kaki, miring
// (derajat, searah jarum jam, berporos di kaki), dan tinggi lompatan.
struct Pose {
  const uint8_t *frame = OWL_IDLE;
  float x = W / 2, y = 204, scale = 4;
  float sx = 1, sy = 1, angle = 0, lift = 0;
};

// q > 0 = gepeng (melebar), q < 0 = memanjang. Volume kira-kira tetap.
void squash(Pose &p, float q) {
  p.sy *= 1 - q;
  p.sx *= 1 + q * 0.8f;
}

void breathe(Pose &p, float t, float amount = 0.022f) { squash(p, amount * sinf(t * 2.6f)); }

// Satu lompatan sejak k detik: jongkok (aba-aba), melesat memanjang, gepeng saat mendarat lalu
// memantul. Hasilnya ditambahkan ke pose, jadi bisa digabung dengan gerak lain. `stretch`
// mengecilkan regangan di udara untuk burung hantu besar yang kepalanya dekat tepi layar.
void jump(Pose &p, float k, float height, float air = 0.42f, float crouch = 0.12f, float stretch = 1) {
  if (k < 0) return;
  if (k < crouch) {
    squash(p, 0.17f * sinf(k / crouch * PI_F / 2));
    return;
  }
  k -= crouch;
  if (k < air) {
    float a = k / air;
    p.lift += height * 4 * a * (1 - a);
    squash(p, (a < 0.5f ? -0.16f * (1 - 2 * a) : -0.07f * (2 * a - 1)) * stretch);
    return;
  }
  k -= air;
  squash(p, 0.24f * expf(-k * 7) * cosf(k * 21));
}

bool inAir(float k, float air = 0.42f, float crouch = 0.12f) { return k >= crouch && k < crouch + air; }

// Pose dasar dengan kedipan tiap 3,4 s dan sesekali melirik.
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

const uint8_t *waveFrame(float k, bool talk = false) {
  bool second = (int)(k / 0.15f) % 2;
  if (talk) return second ? OWL_WAVE_2_TALK : OWL_WAVE_1_TALK;
  return second ? OWL_WAVE_2 : OWL_WAVE_1;
}

// Sprite berindeks dengan transformasi (skala x/y + putar di titik jangkar), nearest neighbor
// supaya tetap pixel art. (ax, ay) = jangkar dalam piksel sprite, (x, y) = posisinya di layar.
void drawSpriteT(lgfx::LovyanGFX &g, const uint8_t *data, int w, int h, float ax, float ay, float x, float y,
                 float kx, float ky, float deg) {
  if (kx < 0.05f || ky < 0.05f) return;
  float a = deg * PI_F / 180, c = cosf(a), s = sinf(a);
  float minX = 1e9f, minY = 1e9f, maxX = -1e9f, maxY = -1e9f;
  for (int i = 0; i < 4; i++) {
    float u = ((i & 1) ? w : 0) - ax, v = ((i & 2) ? h : 0) - ay;
    float X = x + c * u * kx - s * v * ky, Y = y + s * u * kx + c * v * ky;
    minX = fminf(minX, X), maxX = fmaxf(maxX, X), minY = fminf(minY, Y), maxY = fmaxf(maxY, Y);
  }
  int32_t cx, cy, cw, ch;
  g.getClipRect(&cx, &cy, &cw, &ch);
  int x0 = (int)floorf(minX), x1 = (int)ceilf(maxX), y0 = (int)floorf(minY), y1 = (int)ceilf(maxY);
  if (x0 < cx) x0 = cx;
  if (y0 < cy) y0 = cy;
  if (x1 > cx + cw) x1 = cx + cw;
  if (y1 > cy + ch) y1 = cy + ch;
  float du = c / kx, dv = -s / ky;
  for (int Y = y0; Y < y1; Y++) {
    float dx = x0 + 0.5f - x, dy = Y + 0.5f - y;
    float u = (c * dx + s * dy) / kx + ax, v = (-s * dx + c * dy) / ky + ay;
    int runStart = x0, runIdx = 0;
    for (int X = x0; X <= x1; X++, u += du, v += dv) {
      int idx = -1;  // penutup baris
      if (X < x1) {
        int iu = (int)floorf(u), iv = (int)floorf(v);
        idx = (iu >= 0 && iu < w && iv >= 0 && iv < h) ? data[iv * w + iu] : 0;
      }
      if (idx != runIdx) {
        if (runIdx > 0) g.drawFastHLine(runStart, Y, X - runStart, OWL_PAL[runIdx - 1]);
        runIdx = idx;
        runStart = X;
      }
    }
  }
}

constexpr int MARGIN = 10;  // jarak minimal isi layar ke tepi

// Semua isi digambar di area aman (MARGIN dari tepi), termasuk yang sedang meluncur masuk dan
// partikel; yang keluar area ini terpotong seperti container ber-padding. Hanya latar dan pita
// selebar layar yang digambar di luar area aman (fillBg, atau clearClipRect lalu safeArea).
void safeArea(lgfx::LovyanGFX &g) { g.setClipRect(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN); }

void fillBg(lgfx::LovyanGFX &g, uint16_t color) {
  g.clearClipRect();
  g.fillScreen(color);
  safeArea(g);
}

// fillSmoothRoundRect (juga fillSmoothCircle) menulis piksel tepi halusnya tanpa memperhatikan
// clip, jadi bentuk yang sebagian di luar area clip (mis. sedang meluncur masuk) digambar
// dengan versi biasa yang mematuhi clip.
void smoothRect(lgfx::LovyanGFX &g, int x, int y, int w, int h, int rad, uint16_t c) {
  if (w <= 0 || h <= 0) return;
  int32_t cx, cy, cw, ch;
  g.getClipRect(&cx, &cy, &cw, &ch);
  if (x >= cx && y >= cy && x + w <= cx + cw && y + h <= cy + ch) {
    g.fillSmoothRoundRect(x, y, w, h, rad, c);
  } else {
    g.fillRoundRect(x, y, w, h, rad, c);
  }
}

// Garis tebal halus; drawWideLine juga tidak memperhatikan clip, jadi garis yang sebagian di luar
// area clip memakai drawLine biasa (hanya sesaat, saat sedang meluncur masuk).
void wideLine(lgfx::LovyanGFX &g, float x0, float y0, float x1, float y1, float r, uint16_t c) {
  int32_t cx, cy, cw, ch;
  g.getClipRect(&cx, &cy, &cw, &ch);
  if (fminf(x0, x1) - r >= cx && fminf(y0, y1) - r >= cy && fmaxf(x0, x1) + r < cx + cw &&
      fmaxf(y0, y1) + r < cy + ch) {
    g.drawWideLine(x0, y0, x1, y1, r, c);
  } else {
    g.drawLine((int)x0, (int)y0, (int)x1, (int)y1, c);
  }
}

void smoothCircle(lgfx::LovyanGFX &g, int x, int y, int r, uint16_t c) {
  if (r > 0) smoothRect(g, x - r, y - r, r * 2 + 1, r * 2 + 1, r, c);
}
// Isi sprite burung hantu dimulai di baris 3 (owl_sprites.h): 45 baris di atas kaki.
constexpr float OWL_TOP = 45;

void drawOwl(lgfx::LovyanGFX &g, const Pose &p) {
  // Kepala tetap >= MARGIN dari tepi atas: potong regangan dulu, lalu turunkan lompatannya.
  // Jatuh dari luar layar (lift besar, mis. layar nyala) tidak ditahan; area aman memotongnya.
  float ky = p.scale * p.sy, y = p.y - p.lift;
  if (p.lift < 60) {
    float fit = (y - MARGIN) / OWL_TOP;
    if (ky > fit) ky = fmaxf(fit, fminf(ky, p.scale));
    if (y - OWL_TOP * ky < MARGIN) y = MARGIN + OWL_TOP * ky;
  }
  // jangkar: tengah bawah kaki (baris 47 sprite)
  drawSpriteT(g, p.frame, OWL_W, OWL_H, OWL_W / 2.0f, 48, roundf(p.x), roundf(y), p.scale * p.sx, ky, p.angle);
}

// Latar gelap: lingkaran cahaya lembut di belakang burung hantu supaya topinya yang biru tua
// tidak tenggelam. Diam di tempat (tidak ikut melompat). Tema terang: tidak ada, kecuali
// `force` (layar nyala, yang selalu gelap).
void halo(lgfx::LovyanGFX &g, int x, int footY, float scale, uint16_t bg = BG, bool force = false) {
  if (!DARK && !force) return;
  int cy = footY - (int)(24 * scale);
  int r = (int)(27 * scale);
  if (r > cy - MARGIN) r = cy - MARGIN;
  smoothCircle(g, x, cy, r, mix(bg, BLUE, 0.07f));
  smoothCircle(g, x, cy, r * 23 / 27, mix(bg, BLUE, 0.13f));
}

// Bayangan lonjong di lantai; mengecil saat melompat.
void shadow(lgfx::LovyanGFX &g, const Pose &p, uint16_t color) {
  float k = 1 - clamp01(p.lift / 110) * 0.6f;
  int rx = (int)(p.scale * 12 * k * p.sx), ry = (int)(p.scale * 1.7f * k) + 1;
  g.fillEllipse((int)p.x, (int)p.y + 1, rx, ry, color);
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

// Bungkus kata ke lebar maxW; mengembalikan jumlah baris (bisa lebih dari maxLines).
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
    while (line.size() > 1 && g.textWidth(line.c_str()) > maxW) {
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

// ---------------------------------------------------------------- komponen

void rrect(lgfx::LovyanGFX &g, const Rect &r, int rad, uint16_t c) {
  smoothRect(g, r.x, r.y, r.w, r.h, rad, c);
}

// Kartu: tepi 2 px dan "bibir" 4 px di bawah, seperti kartu Duolingo.
void card(lgfx::LovyanGFX &g, const Rect &r, uint16_t fill = SURFACE, uint16_t edge = EDGE, int rad = 16) {
  rrect(g, r, rad, edge);
  rrect(g, {r.x + 2, r.y + 2, r.w - 4, r.h - 6}, rad - 2, fill);
}

// Tombol 3D: muka tombol turun ke bayangannya saat ditekan (press 0..1). Mengembalikan pusat y
// muka tombol untuk label.
int button3d(lgfx::LovyanGFX &g, const Rect &r, uint16_t face, uint16_t shade, float press, int rad = 14) {
  constexpr int DEPTH = 5;
  int off = (int)roundf(clamp01(press) * DEPTH);
  rrect(g, {r.x, r.y + DEPTH, r.w, r.h - DEPTH}, rad, shade);
  rrect(g, {r.x, r.y + off, r.w, r.h - DEPTH}, rad, face);
  return r.y + off + (r.h - DEPTH) / 2;
}

// Bar progress membulat dengan kilau di atas isinya.
void pill(lgfx::LovyanGFX &g, int x, int y, int w, int h, float frac, uint16_t fill, uint16_t track) {
  rrect(g, {x, y, w, h}, h / 2, track);
  int fw = (int)(w * clamp01(frac) + 0.5f);
  if (fw <= 0) return;
  if (fw < h) fw = h;
  rrect(g, {x, y, fw, h}, h / 2, fill);
  if (fw > h) rrect(g, {x + h / 2, y + h / 4, fw - h, h / 4 > 2 ? h / 4 : 2}, 2, mix(fill, SNOW, 0.35f));
}

// Gelembung bicara; ekor ke (tipX, tipY), dari sisi kiri atau atas.
void bubble(lgfx::LovyanGFX &g, const Rect &r, int tipX, int tipY, bool fromTop = false, uint16_t fill = SURFACE,
            uint16_t edge = EDGE) {
  if (fromTop) {
    int c = tipX < r.x + 30 ? r.x + 30 : (tipX > r.x + r.w - 30 ? r.x + r.w - 30 : tipX);
    g.fillTriangle(c - 16, r.y + 8, c + 16, r.y + 8, tipX, tipY, edge);
    card(g, r, fill, edge, 18);
    g.fillTriangle(c - 12, r.y + 3, c + 12, r.y + 3, tipX, tipY + 4, fill);
  } else {
    int c = tipY < r.y + 22 ? r.y + 22 : (tipY > r.y + r.h - 26 ? r.y + r.h - 26 : tipY);
    g.fillTriangle(r.x + 8, c - 15, r.x + 8, c + 13, tipX, tipY, edge);
    card(g, r, fill, edge, 18);
    g.fillTriangle(r.x + 3, c - 11, r.x + 3, c + 9, tipX + 4, tipY, fill);
  }
}

// Bintang empat sudut (kilau).
void star4(lgfx::LovyanGFX &g, float x, float y, float r, uint16_t c) {
  if (r < 1) return;
  float q = r * 0.3f;
  g.fillTriangle(x, y - r, x - q, y, x + q, y, c);
  g.fillTriangle(x, y + r, x - q, y, x + q, y, c);
  g.fillTriangle(x - r, y, x, y - q, x, y + q, c);
  g.fillTriangle(x + r, y, x, y - q, x, y + q, c);
}

const uint16_t CONFETTI[] = {GREEN, BLUE, RED, YELLOW, PURPLE, ORANGE};

// Kertas yang membalik (lebar mengikuti cos putaran) atau bulatan.
void confettiPiece(lgfx::LovyanGFX &g, int i, float x, float y, float spin) {
  uint16_t c = CONFETTI[i % 6];
  if (i % 4 == 3) {
    g.fillCircle((int)x, (int)y, 3, c);
    return;
  }
  int w = 2 + (int)(7 * fabsf(cosf(spin))), h = 5;
  g.fillRect((int)x - w / 2, (int)y - h / 2, w, h, c);
}

// Ledakan konfeti dari (cx, cy): melesat ke atas lalu jatuh.
void confettiBurst(lgfx::LovyanGFX &g, float age, float cx, float cy, int n, float power) {
  if (age < 0) return;
  for (int i = 0; i < n; i++) {
    float ang = -PI_F / 2 + (rnd(i, 0) - 0.5f) * 2.6f, v = power * (0.45f + rnd(i, 1) * 0.75f);
    float x = cx + cosf(ang) * v * age + sinf(age * 4 + i) * 5;
    float y = cy + sinf(ang) * v * age + 260 * age * age;
    if (y > H + 10) continue;
    confettiPiece(g, i, x, y, age * (6 + rnd(i, 2) * 8) + i);
  }
}

// Hujan konfeti terus-menerus dari atas.
void confettiRain(lgfx::LovyanGFX &g, float t, int n) {
  for (int i = 0; i < n; i++) {
    float speed = 60 + rnd(i, 3) * 70;
    float y = fmodf(t * speed + rnd(i, 4) * (H + 40), H + 40) - 20;
    float x = rnd(i, 5) * W + sinf(t * 2 + i) * 10;
    confettiPiece(g, i, x, y, t * (5 + rnd(i, 6) * 6) + i);
  }
}

// ---------------------------------------------------------------- ikon vektor

void micIcon(lgfx::LovyanGFX &g, int cx, int cy, float s, uint16_t c) {
  rrect(g, {(int)(cx - 4 * s), (int)(cy - 9 * s), (int)(8 * s), (int)(13 * s)}, (int)(4 * s), c);
  g.fillArc(cx, (int)(cy + 0 * s), (int)(6 * s), (int)(7.6f * s), 0, 180, c);
  g.fillRect((int)(cx - s * 0.8f), (int)(cy + 7 * s), (int)(1.6f * s + 1), (int)(3 * s), c);
  rrect(g, {(int)(cx - 4 * s), (int)(cy + 9.5f * s), (int)(8 * s), (int)(1.8f * s + 1)}, 1, c);
}

// Wi-Fi: titik + tiga busur; `lit` busur pertama menyala.
void wifiIcon(lgfx::LovyanGFX &g, int cx, int cy, float s, int lit, uint16_t on, uint16_t off) {
  smoothCircle(g, cx, cy, (int)(2.2f * s), lit >= 0 ? on : off);
  for (int i = 1; i <= 3; i++) {
    int r0 = (int)(s * (1.8f + i * 3.2f));
    g.fillArc(cx, cy, r0, r0 + (int)(2.2f * s), 225, 315, i <= lit ? on : off);
  }
}

void clockIcon(lgfx::LovyanGFX &g, int cx, int cy, int r, float turn, uint16_t c) {
  smoothCircle(g, cx, cy, r, c);
  smoothCircle(g, cx, cy, r - 3, SURFACE);
  float a = turn * 2 * PI_F - PI_F / 2;
  wideLine(g, cx, cy, cx + (int)(cosf(a) * (r - 6)), cy + (int)(sinf(a) * (r - 6)), 1.5f, c);
  wideLine(g, cx, cy, cx, cy - (r - 7), 1.5f, c);
}

void pinIcon(lgfx::LovyanGFX &g, int cx, int cy, float s, uint16_t c) {
  g.fillTriangle(cx - 6 * s, cy - 1 * s, cx + 6 * s, cy - 1 * s, cx, cy + 10 * s, c);
  smoothCircle(g, cx, (int)(cy - 3 * s), (int)(7 * s), c);
  smoothCircle(g, cx, (int)(cy - 3 * s), (int)(2.6f * s), SURFACE);
}

void checkMark(lgfx::LovyanGFX &g, int cx, int cy, float s, float progress, float width, uint16_t c) {
  float ax = cx - 10 * s, ay = cy, bx = cx - 3 * s, by = cy + 7 * s, ex = cx + 11 * s, ey = cy - 8 * s;
  float k1 = clamp01(progress / 0.4f), k2 = clamp01((progress - 0.4f) / 0.6f);
  if (k1 <= 0) return;
  wideLine(g, ax, ay, ax + (bx - ax) * k1, ay + (by - ay) * k1, width, c);
  if (k2 > 0) wideLine(g, bx, by, bx + (ex - bx) * k2, by + (ey - by) * k2, width, c);
}

void crossMark(lgfx::LovyanGFX &g, int cx, int cy, float s, float width, uint16_t c) {
  wideLine(g, cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s, width, c);
  wideLine(g, cx + 7 * s, cy - 7 * s, cx - 7 * s, cy + 7 * s, width, c);
}

// Lonceng; swing = geser badan (px), klepon bergerak berlawanan.
void bellIcon(lgfx::LovyanGFX &g, int cx, int cy, float s, float swing, uint16_t c, uint16_t dark) {
  int x = cx + (int)swing;
  smoothCircle(g, cx - (int)(swing * 0.5f), (int)(cy + 17 * s), (int)(6 * s), dark);
  smoothCircle(g, x, (int)(cy - 22 * s), (int)(5 * s), dark);
  rrect(g, {(int)(x - 17 * s), (int)(cy - 21 * s), (int)(34 * s), (int)(34 * s)}, (int)(16 * s), c);
  rrect(g, {(int)(x - 25 * s), (int)(cy + 5 * s), (int)(50 * s), (int)(10 * s)}, (int)(5 * s), c);
  rrect(g, {(int)(x - 10 * s), (int)(cy - 14 * s), (int)(5 * s), (int)(17 * s)}, (int)(2 * s), mix(c, SNOW, 0.55f));
}

// Nomor langkah dalam bulatan 3D.
void numberBadge(lgfx::LovyanGFX &g, int cx, int cy, const char *n, uint16_t c, uint16_t dark) {
  smoothCircle(g, cx, cy + 3, 15, dark);
  smoothCircle(g, cx, cy, 15, c);
  useFont(g, headFont);
  say(g, n, cx, cy + 1, SNOW, middle_center);
}

// ---------------------------------------------------------------- nyala

void bootScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  // selalu biru malam, juga di tema terang
  const uint16_t bootBg = NAVY;
  fillBg(g, bootBg);
  // bulatan lembut melayang di latar
  for (int i = 0; i < 6; i++) {
    float y = fmodf(H + 60 - t * (14 + i * 4) - i * 70, H + 120) - 60;
    smoothCircle(g, (int)(40 + rnd(i, 1) * 400), (int)y, 10 + (int)(rnd(i, 2) * 22), mix(bootBg, BLUE, 0.08f));
  }

  Pose p;
  p.y = 200;
  bool done = ui.done >= 0;
  // jatuh (masih tidur) lalu mendarat gepeng dan memantul
  float k = t - 0.1f;
  if (k < 0) {
    p.lift = 400;
  } else if (k < 0.42f) {
    float a = k / 0.42f;
    p.lift = 280 * (1 - a * a);
    squash(p, -0.14f * a);  // memanjang saat meluncur
  } else {
    squash(p, 0.28f * expf(-(k - 0.42f) * 6) * cosf((k - 0.42f) * 18));
  }
  if (t < 1.0f) {
    p.frame = OWL_BLINK;
  } else if (t < 1.1f) {
    p.frame = OWL_BLINK_HALF;
  } else if (t >= 1.4f && t < 2.6f) {
    p.frame = waveFrame(t - 1.4f);
    p.angle = sinf((t - 1.4f) * 7) * 6;
  } else {
    p.frame = alive(t - 1.0f, OWL_IDLE);
    if (t > 2.6f) {  // menunggu: hop kecil tiap 1,6 s
      float h = fmodf(t - 2.6f, 1.6f);
      jump(p, h, 8, 0.28f, 0.1f, 0.3f);
    }
  }
  if (k > 0.42f) breathe(p, t);
  if (done) {
    p = Pose();
    p.y = 200;
    p.frame = OWL_HAPPY;
    jump(p, ui.done, 12, 0.46f, 0.12f, 0.3f);
    if (inAir(ui.done, 0.46f)) p.angle = -8 + 16 * clamp01((ui.done - 0.12f) / 0.46f);
  }
  halo(g, W / 2, 200, 4, bootBg, true);
  if (k > 0) shadow(g, p, NAVY_GROUND);
  drawOwl(g, p);
  if (done) confettiBurst(g, ui.done, W / 2, 120, 36, 300);

  // logo: huruf muncul satu per satu dengan pantulan; saat siap bergelombang
  useFont(g, logoFont);
  const char *logo = "EduPad";
  int x = W / 2 - g.textWidth(logo) / 2;
  for (int i = 0; logo[i]; i++) {
    char ch[2] = {logo[i], 0};
    float a = clamp01((t - 0.7f - i * 0.07f) / 0.35f);
    if (a > 0) {
      int dy = (int)((1 - easeOutBack(a)) * 26);
      if (done) dy -= (int)(fmaxf(0, sinf(ui.done * 9 - i * 0.7f)) * 8 * expf(-ui.done * 1.5f));
      say(g, ch, x, 232 + dy, mix(bootBg, i < 3 ? SNOW : GREEN, clamp01(a * 2)));
    }
    x += g.textWidth(ch);
  }

  // status + titik melompat + bar
  float a = clamp01((t - 0.9f) / 0.4f);
  if (a <= 0) return;
  useFont(g, textFont);
  std::string s = fitWidth(g, ui.status, W - 100);
  int tw = g.textWidth(s.c_str()), dots = done ? 0 : 3;
  int sx = W / 2 - (tw + (dots ? 8 + dots * 10 : 0)) / 2;
  uint16_t ink = mix(bootBg, NAVY_MUTED, a * 0.92f);
  say(g, s.c_str(), sx, 271, ink);
  for (int i = 0; i < dots; i++) {
    float b = fmaxf(0, sinf(t * 7 - i * 0.9f));
    smoothCircle(g, sx + tw + 12 + i * 10, 275 - (int)(b * 5), 3, ink);
  }
  pill(g, W / 2 - 140, 291, 280, 14, ui.progress, mix(bootBg, GREEN, a), mix(bootBg, NAVY_EDGE, a));
}

// ---------------------------------------------------------------- tidur & bangun

constexpr int BED_SCALE = 4;
constexpr int FLOOR_Y = 262;

void nightSky(lgfx::LovyanGFX &g, float t) {
  g.clearClipRect();
  g.fillScreen(NIGHT);
  rrect(g, {-30, FLOOR_Y, W + 60, 90}, 28, NIGHT_LIGHT);
  safeArea(g);
  static const int stars[][2] = {{40, 40}, {120, 90}, {70, 170}, {200, 30}, {300, 70}, {360, 24}, {450, 150}, {20, 110}};
  for (int i = 0; i < 8; i++) {
    float v = 0.5f + 0.5f * sinf(t * 2.3f + i * 1.7f);
    star4(g, stars[i][0], stars[i][1], 3 + v * 4, mix(NIGHT, rgb(0xC9D8FF), 0.4f + v * 0.6f));
  }
  smoothCircle(g, 414, 58, 26, MOON);
  smoothCircle(g, 426, 48, 23, NIGHT);
}

void bed(lgfx::LovyanGFX &g, bool awake, float breathT, float shake, float entry) {
  float sy = 1 + 0.02f * sinf(breathT * 1.7f) - wobble(entry, 0.12f, 16, 5);
  float sx = 1 + wobble(entry, 0.1f, 16, 5) * 0.8f;
  drawSpriteT(g, awake ? OWL_BED_AWAKE : OWL_BED, BED_W, BED_H, BED_W / 2.0f, BED_H, W / 2 + shake, FLOOR_Y + 8,
              BED_SCALE * sx, BED_SCALE * sy, 0);
}

const uint8_t *fallingAsleep(float t) {
  if (t < 0.3f) return alive(t, OWL_IDLE, false);
  if (t < 1.3f) return OWL_YAWN;
  if (t < 1.6f) return OWL_BLINK_HALF;
  return OWL_BLINK;
}

void sleepScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  if (t < SLEEP_ROOM_AT) {
    float dusk = smooth((t - 1.0f) / (SLEEP_ROOM_AT - 1.0f));
    uint16_t bg = mix(BG, NIGHT, dusk);
    fillBg(g, bg);
    Pose p;
    p.frame = fallingAsleep(t);
    if (t >= 0.3f && t < 1.3f) {  // menguap: memanjang, kepala mendongak
      float k = sinf(clamp01((t - 0.3f) / 1.0f) * PI_F);
      squash(p, -0.07f * k);
      p.angle = -5 * k;
    } else if (t >= 1.3f) {  // terkulai, terangguk-angguk
      float q = easeOutCubic((t - 1.3f) / 0.6f);
      squash(p, 0.09f * q + 0.03f * sinf(t * 5) * q);
      p.angle = 7 * q;
    } else {
      breathe(p, t);
    }
    shadow(g, p, mix(GROUND, NIGHT_LIGHT, dusk));
    drawOwl(g, p);
    useFont(g, headFont);
    say(g, "Hoaam... aku ngantuk", W / 2, 250, mix(MUTED, ZBLUE, dusk), middle_center);
    return;
  }
  float k = t - SLEEP_ROOM_AT;
  nightSky(g, t);
  bed(g, false, k, 0, k);
  // Z naik dari kepala, membesar, lalu memudar
  for (int i = 0; i < 3; i++) {
    float age = k - 0.4f - i * 1.0f;
    if (age < 0) continue;
    float a = fmodf(age, 3.0f);
    float alpha = a > 2.2f ? 1 - (a - 2.2f) / 0.8f : clamp01(a / 0.3f);
    useFont(g, a > 1.2f ? titleFont : headFont);
    say(g, "Z", 262 + (int)(a * 18 + sinf(a * 3) * 5), 104 - (int)(a * 22), mix(NIGHT, ZBLUE, alpha), middle_center);
  }
  useFont(g, textFont);
  say(g, "Sampai jumpa lagi!", W / 2, 294, mix(NIGHT_LIGHT, ZBLUE, clamp01(k / 0.6f)), middle_center);
}

// ---------------------------------------------------------------- siap

constexpr Rect ASK_BUTTON{56, 226, 368, 58};

// Tombol "tahan" yang ditekan-dilepas berulang: penjelas cara bertanya.
void askButton(lgfx::LovyanGFX &g, float t, int dy) {
  float c = fmodf(t, 2.6f);
  float press = clamp01((c - 1.0f) / 0.07f) * (1 - clamp01((c - 2.0f) / 0.1f));
  Rect r = ASK_BUTTON;
  r.y += dy;
  int cy = button3d(g, r, GREEN, GREEN_DARK, press, 16);
  useFont(g, headFont);
  const char *label = "TAHAN UNTUK BERTANYA";
  int tw = g.textWidth(label), x = W / 2 - (tw + 34) / 2;
  micIcon(g, x + 10, cy - 1, 1.6f, SNOW);
  say(g, label, x + 34, cy + 1, SNOW);
  if (press > 0.5f) {  // gelombang suara keluar dari tombol saat ditahan
    for (int i = 0; i < 2; i++) {
      float a = fmodf(c - 1.0f + i * 0.35f, 0.7f) / 0.7f;
      uint16_t col = mix(GREEN_DARK, BG, 1 - a);
      g.fillArc(r.x + r.w + 4, cy + 2, 8 + (int)(a * 14), 11 + (int)(a * 14), 300, 60, col);
      g.fillArc(r.x - 4, cy + 2, 8 + (int)(a * 14), 11 + (int)(a * 14), 120, 240, col);
    }
  }
}

void homeHint(lgfx::LovyanGFX &g, int y) {
  useFont(g, smallFont);
  const char *a = "Tekan 1x: ulangi jawaban", *b = "Tekan 2x: topik baru";
  int wa = g.textWidth(a), wb = g.textWidth(b);
  int x = W / 2 - (wa + 26 + wb) / 2;
  say(g, a, x, y, MUTED);
  smoothCircle(g, x + wa + 13, y, 3, EDGE);
  say(g, b, x + wa + 26, y, MUTED);
}

// Pil status di atas: Wi-Fi terputus / peringatan / topik baru. Turun dengan pegas.
void statusPill(lgfx::LovyanGFX &g, const char *text, uint16_t fill, uint16_t shade, float age, bool wifi, float t) {
  useFont(g, smallFont);
  int tw = g.textWidth(text), w = tw + (wifi ? 56 : 32), h = 34;
  int y = 10 - (int)((1 - pop(age, 0.45f)) * 60);
  Rect r{W / 2 - w / 2, y, w, h + 4};
  int cy = button3d(g, r, fill, shade, 0, h / 2) + 1;
  int x = r.x + 16;
  if (wifi) {
    int lit = (int)(t * 3) % 4 - 1;  // mencari sinyal
    wifiIcon(g, x + 10, cy + 7, 1.25f, lit, SNOW, mix(fill, SNOW, 0.35f));
    x += 26;
  }
  say(g, text, x, cy, SNOW);
}

// Gerak di layar siap: bernapas, berkedip, dan siklus 10 s: lompat-lompat kecil, melambai
// sambil bergoyang, lalu memiringkan badan penasaran.
void homePose(Pose &p, float t) {
  float c = fmodf(t, 10.0f);
  p.frame = alive(t, OWL_IDLE);
  breathe(p, t);
  if (c > 2.4f && c < 3.8f) {
    float k = c - 2.4f;
    if (k < 0.62f) {
      jump(p, k, 14, 0.3f, 0.12f, 0.5f);
      if (inAir(k, 0.3f)) p.frame = OWL_HAPPY;
    } else {
      jump(p, k - 0.62f, 10, 0.26f, 0.12f, 0.5f);
      if (inAir(k - 0.62f, 0.26f)) p.frame = OWL_HAPPY;
    }
  } else if (c > 5.2f && c < 6.8f) {
    float k = c - 5.2f;
    p.frame = waveFrame(k);
    p.angle = sinf(k * 7) * 6 * smooth(k / 0.2f) * smooth((1.6f - k) / 0.2f);
  } else if (c > 8.0f && c < 9.8f) {
    float k = c - 8.0f, e = smooth(k / 0.35f) * smooth((1.8f - k) / 0.35f);
    p.angle = 10 * e;
    if (k > 0.2f && k < 1.5f) p.frame = OWL_LOOK_R;
  }
}

// ---- kartu "kuliah berikutnya"

void duration(char *out, size_t n, int32_t s) {
  if (s < 60) {
    snprintf(out, n, "<1 menit");
    return;
  }
  int m = (s + 59) / 60, h = m / 60;
  if (h == 0) {
    snprintf(out, n, "%d menit", m);
  } else if (h < 10 && m % 60) {
    snprintf(out, n, "%d jam %d menit", h, m % 60);
  } else {
    snprintf(out, n, "%d jam", h);
  }
}

void nextChip(const Ui &ui, char *out, size_t n, bool &ongoing, bool &soon) {
  ongoing = soon = false;
  if (!ui.nowTs) {
    snprintf(out, n, "%s", ui.nextDay);
    return;
  }
  int32_t s = (int32_t)(ui.nextStart - ui.nowTs);
  if (s <= 0 && ui.nowTs < ui.nextEnd) {
    ongoing = true;
    snprintf(out, n, "BERLANGSUNG");
  } else if (s < 3600) {
    soon = s < 1800;
    snprintf(out, n, "%d MENIT LAGI", (int)((s + 59) / 60));
  } else if (!strcmp(ui.nextDay, "Hari ini")) {
    snprintf(out, n, "%d JAM LAGI", (int)(s / 3600));
  } else {
    snprintf(out, n, "%s", ui.nextDay);
  }
}

void nextCard(lgfx::LovyanGFX &g, const Ui &ui, int dx) {
  Rect r{196 + dx, 20, 270, 168};
  bubble(g, r, r.x - 18, 84);
  char chip[24];
  bool ongoing, soon;
  nextChip(ui, chip, sizeof chip, ongoing, soon);
  int x = r.x + 18;
  // ubin kalender + label kecil
  rrect(g, {x, r.y + 16, 30, 30}, 8, ongoing ? GREEN : BLUE);
  rrect(g, {x + 6, r.y + 24, 18, 16}, 3, SNOW);
  g.fillRect(x + 6, r.y + 24, 18, 5, ongoing ? GREEN_DARK : BLUE_DARK);
  useFont(g, smallFont);
  say(g, ongoing ? "SEDANG BERLANGSUNG" : "KULIAH BERIKUTNYA", x + 40, r.y + 32, ongoing ? (DARK ? GREEN : GREEN_DARK) : MUTED);
  useFont(g, titleFont);
  say(g, fitWidth(g, ui.nextName, r.w - 36).c_str(), x, r.y + 72, INK);
  useFont(g, headFont);
  say(g, ui.nextTime, x, r.y + 104, BLUE);
  int wt = g.textWidth(ui.nextTime);
  useFont(g, smallFont);
  say(g, fitWidth(g, ui.nextRoom, r.w - 46 - wt).c_str(), x + wt + 10, r.y + 105, MUTED);
  // chip sisa waktu: kuning berdenyut bila hampir mulai
  int cw = g.textWidth(chip) + 26;
  float beat = soon ? fmaxf(0, sinf(ui.t * 6)) : 0;
  Rect c{x, r.y + 122, cw, 32};
  uint16_t face = ongoing ? GREEN : soon ? YELLOW : RAISED, shade = ongoing ? GREEN_DARK : soon ? YELLOW_DARK : EDGE;
  int cy = button3d(g, c, face, shade, beat * 0.6f, 12);
  say(g, chip, c.x + cw / 2, cy + 1, ongoing ? SNOW : soon ? rgb(0x6B4A00) : MUTED, middle_center);
}

void homeScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  // dibangunkan: kaget di ranjang dulu
  if (ui.wake >= 0 && ui.wake < WAKE_ROOM_SECONDS) {
    nightSky(g, t);
    bed(g, true, 0, sinf(ui.wake * 70) * 4 * (1 - ui.wake / WAKE_ROOM_SECONDS), 0);
    float b = pop(ui.wake, 0.25f);
    useFont(g, titleFont);
    g.setTextColor(YELLOW);
    g.setTextDatum(middle_center);
    if (b > 0) g.drawString("!", 268, 40 - (int)(b * 12));
    return;
  }
  float wk = ui.wake >= 0 ? ui.wake - WAKE_ROOM_SECONDS : 99;
  fillBg(g, mix(NIGHT, BG, clamp01(wk / 0.35f)));

  Pose p;
  p.y = 210;
  bool hasNext = ui.hasNext;
  if (hasNext) {
    p.scale = 3;
    p.x = 100;
    p.y = 196;
  }
  homePose(p, t);
  if (!ui.online) {
    p.frame = alive(t, OWL_WORRIED, false);
    p.angle = sinf(t * 2.2f) * 4;
  }
  if (wk < 2.4f) {  // melompat keluar ranjang, menggeliat, melambai
    p = Pose();
    p.y = 210;
    if (hasNext) p.scale = 3, p.x = 100, p.y = 196;
    if (wk < 0.62f) {
      p.frame = OWL_SURPRISED;
      jump(p, wk, 18, 0.46f, 0.04f, 0.6f);
    } else if (wk < 1.3f) {
      p.frame = OWL_STRETCH;
      squash(p, -0.1f * sinf(clamp01((wk - 0.62f) / 0.68f) * PI_F));
    } else {
      p.frame = waveFrame(wk - 1.3f);
      p.angle = sinf((wk - 1.3f) * 7) * 6;
    }
  }
  halo(g, hasNext ? 100 : W / 2, hasNext ? 196 : 210, hasNext ? 3 : 4, mix(NIGHT, BG, clamp01(wk / 0.35f)));
  shadow(g, p, GROUND);
  drawOwl(g, p);

  int slide = wk < 99 ? (int)((1 - pop(wk - 0.3f, 0.5f)) * 130) : 0;
  if (hasNext) nextCard(g, ui, (int)((1 - pop(t - 0.15f, 0.5f)) * 300) + slide * 2);
  askButton(g, t, slide);
  if (slide < 60) homeHint(g, 300 + slide);

  if (!ui.online) {
    statusPill(g, "Wi-Fi terputus, menyambung ulang...", RED, RED_DARK, t, true, t);
  } else if (ui.warning[0]) {
    statusPill(g, ui.warning, ORANGE, ORANGE_DARK, t, false, t);
  } else if (ui.newSession) {
    statusPill(g, "Topik baru dimulai", BLUE, BLUE_DARK, t, false, t);
  }
}

// ---------------------------------------------------------------- mendengarkan

// Seberapa jelas suara terdengar; menentukan ekspresi, warna gelombang, dan pesan.
// Jelas = di atas ambang server (SPEECH_DBFS), kurang jelas = ada suara tapi pelan,
// hening = di bawah SILENT_DBFS.
enum class Hearing : uint8_t { Clear, Unclear, Silent };
constexpr float SILENT_DBFS = -52.0f;

Hearing hearing(const Ui &ui) {
  if (ui.level >= SPEECH_DBFS || (ui.quiet < 0.35f && ui.level >= SILENT_DBFS)) return Hearing::Clear;
  return ui.level >= SILENT_DBFS ? Hearing::Unclear : Hearing::Silent;
}

// Pil keadaan di bawah layar; muncul membal setiap keadaan berganti.
// icon: 0 = centang, 1 = tanda seru, 2 = mikrofon.
void hearingChip(lgfx::LovyanGFX &g, const char *text, uint16_t face, uint16_t shade, uint16_t ink, float age,
                 int icon) {
  useFont(g, smallFont);
  int w = g.textWidth(text) + 62;
  Rect r{W / 2 - w / 2, 268 + (int)((1 - pop(age, 0.35f)) * 50), w, 40};
  int cy = button3d(g, r, face, shade, 0, 18);
  int ix = r.x + 24;
  smoothCircle(g, ix, cy, 11, mix(face, SNOW, 0.85f));
  if (icon == 0) {
    checkMark(g, ix, cy, 0.5f, 1, 1.6f, shade);
  } else if (icon == 1) {
    rrect(g, {ix - 2, cy - 7, 4, 9}, 2, shade);
    smoothCircle(g, ix, cy + 5, 2, shade);
  } else {
    micIcon(g, ix, cy - 1, 0.7f, shade);
  }
  say(g, text, r.x + 44, cy + 1, ink);
}

void listenScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t, norm = clamp01((ui.level + 60) / 45);
  Hearing state = hearing(ui);
  // lama keadaan sekarang, untuk animasi pergantian ekspresi
  static Hearing last = Hearing::Silent;
  static float since = 0, prevT = 0;
  if (t < prevT || state != last) since = t, last = state;
  prevT = t;
  float age = t - since;
  bool waiting = ui.elapsedMs < 1200;  // baru mulai: wajar belum ada suara
  bool lost = state == Hearing::Silent && !waiting && age > 2.0f;  // lama tidak ada suara

  uint16_t bg = pale(BLUE);
  uint16_t accent = state == Hearing::Clear ? BLUE : state == Hearing::Unclear ? YELLOW : FAINT;
  fillBg(g, bg);
  int cx = W / 2, cy = 112;
  // gelombang memancar: tebal saat jelas, tipis saat pelan, tidak ada saat hening
  for (int k = 0; state != Hearing::Silent && k < 3; k++) {
    float a = fmodf(t + k * 0.5f, 1.5f) / 1.5f;
    int r = 76 + (int)(a * (12 + norm * 6)), th = state == Hearing::Clear ? 3 + (int)(norm * 5) : 2;
    g.fillArc(cx, cy, r, r + th, 0, 360, mix(accent, bg, 0.3f + a * 0.7f));
  }
  smoothCircle(g, cx, cy, 80 + (int)(norm * 8), mix(bg, accent, 0.16f));

  Pose p;
  switch (state) {
    case Hearing::Clear:  // senang mendengar: mengangguk, badan memanjang mengikuti keras suara
      p.frame = alive(t, OWL_LISTEN, false);
      p.angle = -3 + sinf(t * 1.3f) * 2;
      squash(p, -norm * 0.07f - fabsf(sinf(t * 9)) * norm * 0.04f);
      squash(p, wobble(age, 0.1f, 18, 6));  // sigap saat mulai terdengar
      break;
    case Hearing::Unclear:  // menajamkan telinga: condong ke samping, wajah bingung
      p.frame = alive(t, OWL_CONFUSED, false);
      p.angle = -10 * easeOutBack(age / 0.4f) + sinf(t * 3) * 2;
      squash(p, 0.03f);
      break;
    case Hearing::Silent:
      if (waiting) {  // menunggu dengan sabar
        p.frame = alive(t, OWL_LISTEN, false);
      } else if (!lost) {  // mencari asal suara: menoleh kiri-kanan
        bool right = (int)(age / 0.6f) % 2;
        p.frame = right ? OWL_LOOK_R : OWL_LOOK_L;
        p.angle = right ? 4 : -4;
      } else {  // tidak ada suara: cemas dan sedikit lesu
        p.frame = alive(t, OWL_WORRIED, false);
        squash(p, 0.05f * smooth((age - 2.0f) / 0.4f));
        p.angle = sinf(t * 1.5f) * 3;
      }
  }
  breathe(p, t, 0.015f);
  bool startled = ui.wake >= 0 && ui.wake < 1.0f;
  if (startled) {
    p = Pose();
    p.frame = OWL_SURPRISED;
    jump(p, ui.wake, 22, 0.34f, 0.04f, 0.5f);
  }
  shadow(g, p, mix(bg, BLUE, 0.25f));
  drawOwl(g, p);
  useFont(g, titleFont);
  if (startled) {
    say(g, "!", 350, 40 - (int)(pop(ui.wake, 0.25f) * 10), YELLOW_DARK, middle_center);
  } else if (state == Hearing::Unclear) {  // tanda tanya naik-turun di samping kepala
    float b = pop(age - 0.15f, 0.3f);
    say(g, "?", 338, 52 + (int)(sinf(t * 3) * 4), mix(bg, YELLOW_DARK, clamp01(b)), middle_center);
  } else if (state == Hearing::Clear && age < 0.6f) {  // kilau "aha" saat suara mulai jelas
    for (int i = 0; i < 3; i++) star4(g, 330 + i * 16, 40 + (i % 2) * 18, 9 * (1 - age / 0.6f), YELLOW);
  }

  // pil REKAM + waktu, petunjuk di kanan atas
  char timer[12];
  uint32_t s = ui.elapsedMs / 1000;
  snprintf(timer, sizeof timer, "%lu:%02lu", (unsigned long)(s / 60), (unsigned long)(s % 60));
  useFont(g, smallFont);
  int tw = g.textWidth("REKAM") + g.textWidth(timer) + 52;
  Rect pr{16, 14, tw, 38};
  int py = button3d(g, pr, RED, RED_DARK, 0, 17);
  if (fmodf(t, 1.0f) < 0.6f) smoothCircle(g, pr.x + 18, py, 5, SNOW);
  say(g, "REKAM", pr.x + 32, py + 1, SNOW);
  say(g, timer, pr.x + 40 + g.textWidth("REKAM"), py + 1, mix(RED, SNOW, 0.75f));
  say(g, "Lepas tombol untuk kirim", W - 16, py + 1, MUTED, middle_right);

  // batang gelombang suara: warna mengikuti keadaan, datar saat hening
  for (int i = 0; i < 25; i++) {
    float prof = 1 - fabsf(i - 12) / 14.0f;
    float wob = 0.45f + 0.55f * fabsf(sinf(t * 9 + i * 1.3f) * sinf(t * 3.1f + i * 0.7f));
    int h = state == Hearing::Silent ? 6 : 8 + (int)(norm * 40 * prof * wob);
    int x = W / 2 + (i - 12) * 14 - 4;
    rrect(g, {x, 238 - h / 2, 8, h}, 4, state == Hearing::Silent ? mix(bg, FAINT, 0.7f) : accent);
  }

  switch (state) {
    case Hearing::Clear:
      hearingChip(g, "Terdengar jelas", GREEN, GREEN_DARK, SNOW, age, 0);
      break;
    case Hearing::Unclear:
      hearingChip(g, "Kurang jelas, bicara lebih keras", YELLOW, YELLOW_DARK, rgb(0x6B4A00), age, 1);
      break;
    case Hearing::Silent:
      if (lost) {
        hearingChip(g, "Tidak ada suara, dekatkan ke mikrofon", ORANGE, ORANGE_DARK, SNOW, age - 2.0f, 1);
      } else {
        hearingChip(g, waiting ? "Ayo, mulai bicara" : "Belum terdengar suara...", RAISED, EDGE, MUTED, age, 2);
      }
  }
}

// ---------------------------------------------------------------- berpikir

const char *thinkText(uint32_t ms) {
  if (ms < 6000) return "Sebentar, aku pikirkan dulu...";
  if (ms < 15000) return "Masih mencari jawaban...";
  return "Hampir selesai, tunggu ya...";
}

void thinkScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  fillBg(g, BG);
  halo(g, W / 2, 208, 4);
  // ubin huruf mengorbit di belakang/depan burung hantu
  struct Orbit {
    const char *ch;
    uint16_t face, shade;
    float phase;
  };
  static const Orbit orbit[] = {{"?", BLUE, BLUE_DARK, 0}, {"!", ORANGE, ORANGE_DARK, 2.09f}, {"A", PURPLE, PURPLE_DARK, 4.19f}};
  auto tile = [&](const Orbit &o) {
    float a = t * 0.9f + o.phase;
    float depth = (sinf(a) + 1) / 2;
    int s = 24 + (int)(depth * 12);
    int x = W / 2 + (int)(cosf(a) * 158), y = 118 + (int)(sinf(a) * 28);
    int cy = button3d(g, {x - s / 2, y - s / 2, s, s + 5}, o.face, o.shade, 0, 8);
    useFont(g, depth > 0.5f ? headFont : smallFont);
    say(g, o.ch, x, cy + 1, SNOW, middle_center);
  };
  for (const Orbit &o : orbit)
    if (sinf(t * 0.9f + o.phase) < 0) tile(o);

  Pose p;
  p.y = 208;
  p.frame = fmodf(t + 1.0f, 3.0f) > 2.82f ? OWL_THINK_BLINK : OWL_THINK;
  p.angle = sinf(t * 1.7f) * 6;
  breathe(p, t);
  jump(p, fmodf(t, 2.4f), 7, 0.22f, 0.08f, 0.5f);  // mengetuk-ngetuk lantai
  shadow(g, p, GROUND);
  drawOwl(g, p);
  for (const Orbit &o : orbit)
    if (sinf(t * 0.9f + o.phase) >= 0) tile(o);

  // gelembung pikiran dengan titik mengetik
  auto blob = [&](int x, int y, int r) {
    smoothCircle(g, x, y, r + 2, EDGE);
    smoothCircle(g, x, y, r, SURFACE);
  };
  blob(318, 78, 5);
  blob(334, 58, 8);
  card(g, {342, 12, 122, 50}, SURFACE, EDGE, 24);
  for (int i = 0; i < 3; i++) {
    float b = fmaxf(0, sinf(t * 7 - i * 0.9f));
    smoothCircle(g, 383 + i * 20, 34 - (int)(b * 7), 6, mix(FAINT, BLUE, b));
  }

  useFont(g, headFont);
  say(g, thinkText(ui.elapsedMs), W / 2, 240, INK, middle_center);
  // bar menunggu: potongan hijau meluncur bolak-balik
  constexpr int BX = 90, BW = 300, BH = 16, LEN = 90;
  rrect(g, {BX, 270, BW, BH}, BH / 2, EDGE);
  int from = (int)((sinf(t * 2.2f) * 0.5f + 0.5f) * (BW - LEN));
  rrect(g, {BX + from, 270, LEN, BH}, BH / 2, GREEN);
  rrect(g, {BX + from + 8, 274, LEN - 16, 4}, 2, mix(GREEN, SNOW, 0.35f));
}

// ---------------------------------------------------------------- jawaban & Wi-Fi

bool mouthOpen(const Ui &ui) { return ui.voice > MOUTH_DBFS; }

// Burung hantu kecil (2x) kiri atas: melompat masuk dari kiri, lalu bicara/menunggu.
Pose cornerOwl(const Ui &ui, const uint8_t *rest) {
  float t = ui.t;
  Pose p;
  p.scale = 2;
  p.x = 66;
  p.y = 104;
  if (t < 0.6f) {
    p.x = -40 + 106 * easeOutCubic(t / 0.5f);
    jump(p, t, 12, 0.42f, 0.02f, 0.6f);
    p.frame = inAir(t, 0.42f, 0.02f) ? OWL_HAPPY : rest;
    return p;
  }
  jump(p, t, 12, 0.42f, 0.02f, 0.6f);  // pantulan pendaratan berlanjut
  if (ui.speaking) {
    p.frame = mouthOpen(ui) ? OWL_TALK : alive(t, OWL_IDLE, false);
    p.angle = sinf(t * 5) * 4;
    if (mouthOpen(ui)) squash(p, -0.06f);
  } else {
    p.frame = alive(t, rest);
    breathe(p, t);
  }
  return p;
}

constexpr Rect TITLE_BUBBLE{132, 10, 336, 82};

void titleBubble(lgfx::LovyanGFX &g, float age, const char *title, const char *sub, uint16_t subColor, int reserve = 0) {
  if (age < 0) return;
  int dx = (int)((1 - pop(age, 0.4f)) * 70);
  Rect r = TITLE_BUBBLE;
  r.x += dx;
  bubble(g, r, 112 + dx / 2, 52);
  int x = r.x + 18, maxW = r.w - 36 - reserve;
  bool hasSub = sub && *sub;
  useFont(g, headFont);
  say(g, fitWidth(g, title, maxW).c_str(), x, hasSub ? 34 : 48, INK);
  if (hasSub) {
    useFont(g, smallFont);
    say(g, fitWidth(g, sub, maxW).c_str(), x, 64, subColor);
  }
}

const uint16_t BADGE[][2] = {{GREEN, GREEN_DARK}, {BLUE, BLUE_DARK}, {PURPLE, PURPLE_DARK}, {ORANGE, ORANGE_DARK}};

void answerScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  fillBg(g, BG);
  Pose p = cornerOwl(ui, OWL_IDLE);
  halo(g, 66, 104, 2);
  shadow(g, p, GROUND);
  drawOwl(g, p);
  char sub[110] = "";
  if (ui.subtitle[0]) snprintf(sub, sizeof sub, "Kamu: %s", ui.subtitle);
  titleBubble(g, t - 0.15f, ui.title, sub, MUTED);

  // satukan baris server jadi butir: "- " memulai butir, "  " melanjutkan
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
  Rect c{12, 104, 456, 206};
  float ca = pop(t - 0.3f, 0.45f);
  if (ca <= 0) return;
  c.y += (int)((1 - ca) * 120);
  card(g, c);
  constexpr int PAD = 18, BULLET = 34;
  int textW = c.w - 2 * PAD - BULLET, top = c.y + 14, availH = c.h - 30;
  Font *font = &textFont;
  int lineH = 27;
  for (int pass = 0; pass < 2; pass++) {
    useFont(g, *font);
    int total = 0;
    for (int i = 0; i < n; i++) total += wrap(g, items[i].c_str(), textW, nullptr, 0);
    if (total * lineH <= availH || pass == 1) break;
    font = &smallFont;
    lineH = 22;
  }
  int maxRows = availH / lineH, row = 0;
  for (int i = 0; i < n && row < maxRows; i++) {
    float a = clamp01((t - 0.55f - i * 0.16f) / 0.35f);
    useFont(g, *font);
    std::string parts[MAX_LINES * 2];
    int count = wrap(g, items[i].c_str(), textW, parts, MAX_LINES * 2);
    int dx = (int)((1 - easeOutBack(a)) * 30);
    for (int k = 0; k < count && k < MAX_LINES * 2 && row < maxRows; k++, row++) {
      if (a <= 0) continue;
      int y = top + row * lineH + lineH / 2;
      if (k == 0) {
        float b = pop(t - 0.55f - i * 0.16f, 0.3f);
        int r = (int)(11 * b);
        smoothCircle(g, c.x + PAD + 11, y + 2, r, BADGE[i % 4][1]);
        smoothCircle(g, c.x + PAD + 11, y, r, BADGE[i % 4][0]);
        if (b > 0.8f) {
          char num[4];
          snprintf(num, sizeof num, "%d", i + 1);
          useFont(g, smallFont);
          say(g, num, c.x + PAD + 11, y + 1, SNOW, middle_center);
          useFont(g, *font);
        }
      }
      std::string s = parts[k];
      bool cut = row == maxRows - 1 && (k < count - 1 || i < n - 1);
      if (cut) s = fitWidth(g, (s + "...").c_str(), textW);
      say(g, s.c_str(), c.x + PAD + BULLET + dx, y, mix(SURFACE, INK, clamp01(a * 1.6f)));
    }
  }
}

// Ubin kata (seperti pilihan jawaban Duolingo) yang sesekali "ditekan".
int chip(lgfx::LovyanGFX &g, int x, int y, const char *text, uint16_t color, float press) {
  useFont(g, headFont);
  int w = g.textWidth(text) + 28;
  Rect r{x, y, w, 42};
  constexpr int DEPTH = 4;
  int off = (int)roundf(clamp01(press) * DEPTH);
  rrect(g, {r.x, r.y + DEPTH, r.w, r.h - DEPTH}, 12, EDGE);
  rrect(g, {r.x, r.y + off, r.w, r.h - DEPTH}, 12, EDGE);
  rrect(g, {r.x + 2, r.y + off + 2, r.w - 4, r.h - DEPTH - 4}, 10, SURFACE);
  say(g, text, r.x + 14, r.y + off + (r.h - DEPTH) / 2 + 1, color);
  return w;
}

void portalScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  fillBg(g, BG);
  Pose p = cornerOwl(ui, OWL_CONFUSED);
  if (t > 0.6f) {  // celingak-celinguk mencari sinyal
    p.angle = sinf(t * 2.0f) * 7;
    float c = fmodf(t, 3.2f);
    if (c > 2.4f) jump(p, c - 2.4f, 10, 0.28f, 0.12f, 0.6f);
  }
  halo(g, 66, 104, 2);
  shadow(g, p, GROUND);
  drawOwl(g, p);

  char sub[128];
  if (ui.subtitle[0]) snprintf(sub, sizeof sub, "Gagal tersambung ke %s", ui.subtitle);
  titleBubble(g, t - 0.15f, "Atur Wi-Fi dulu, ya", ui.subtitle[0] ? sub : "Belum ada Wi-Fi yang tersimpan",
              ui.subtitle[0] ? RED : MUTED, 46);
  if (t > 0.3f) {
    int dx = (int)((1 - pop(t - 0.15f, 0.4f)) * 70);
    int lit = (int)(t * 2.5f) % 5 - 1;
    wifiIcon(g, TITLE_BUBBLE.x + TITLE_BUBBLE.w - 38 + dx, 60, 2.2f, lit > 3 ? 3 : lit, BLUE, EDGE);
  }

  // langkah 1
  float a1 = pop(t - 0.35f, 0.45f);
  if (a1 > 0) {
    Rect r{12, 102 + (int)((1 - a1) * 220), 456, 104};
    card(g, r);
    numberBadge(g, r.x + 30, r.y + 28, "1", BLUE, BLUE_DARK);
    useFont(g, textFont);
    say(g, "Sambungkan HP ke Wi-Fi ini:", r.x + 56, r.y + 28, INK);
    float c = fmodf(t, 3.0f);
    int x = r.x + 56;
    x += chip(g, x, r.y + 48, ui.ssid, BLUE, c > 1.0f && c < 1.25f ? 1 : 0) + 12;
    useFont(g, smallFont);
    say(g, "sandi", x, r.y + 67, FAINT);
    x += g.textWidth("sandi") + 12;
    chip(g, x, r.y + 48, ui.password, INK, c > 1.5f && c < 1.75f ? 1 : 0);
  }
  // langkah 2
  float a2 = pop(t - 0.5f, 0.45f);
  if (a2 > 0) {
    Rect r{12, 212 + (int)((1 - a2) * 120), 456, 72};
    card(g, r);
    numberBadge(g, r.x + 30, r.y + 24, "2", BLUE, BLUE_DARK);
    useFont(g, textFont);
    say(g, "Halaman pengaturan terbuka sendiri", r.x + 56, r.y + 22, INK);
    useFont(g, smallFont);
    say(g, "atau buka", r.x + 56, r.y + 48, FAINT);
    char url[32];
    snprintf(url, sizeof url, "http://%s", ui.ip);
    useFont(g, textFont);
    say(g, url, r.x + 56 + g.textWidth("atau buka") - 4, r.y + 47, BLUE);
  }
  useFont(g, smallFont);
  say(g, "Tekan tombol untuk mencoba Wi-Fi lagi", W / 2, 300, FAINT, middle_center);
}

// ---------------------------------------------------------------- pesan

void noticeScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  bool error = ui.tone == Tone::Error, warn = ui.tone == Tone::Warn;
  uint16_t tone = error ? RED : warn ? YELLOW : GREEN;
  uint16_t band = pale(tone);
  uint16_t ink = DARK ? tone : error ? RED_DARK : warn ? YELLOW_TEXT : GREEN_DARK;
  fillBg(g, BG);
  halo(g, 106, 164, 3);

  Pose p;
  p.scale = 3;
  p.x = 106;
  p.y = 164;
  if (error) {  // terlonjak kaget, gemetar, keringat menetes
    p.frame = alive(t, OWL_WORRIED, false);
    p.x += wobble(t, 10, 34, 4) + (fmodf(t, 2.2f) < 0.35f ? sinf(t * 70) * 2 : 0);
    jump(p, t, 14, 0.26f, 0.03f);
    float k = fmodf(t, 1.4f) / 1.4f;
    int dx = 166, dy = 44 + (int)(k * 34);
    uint16_t c = mix(BLUE, BG, k * k);
    smoothCircle(g, dx, dy + 6, 6, c);
    g.fillTriangle(dx - 5, dy + 4, dx + 5, dy + 4, dx, dy - 7, c);
  } else if (warn) {  // bingung: kepala miring bolak-balik, tanda tanya bermunculan
    p.frame = alive(t, OWL_CONFUSED, false);
    p.angle = sinf(t * 2.2f) * 10;
    breathe(p, t);
    useFont(g, titleFont);
    for (int i = 0; i < 2; i++) {
      float a = fmodf(t + i * 0.8f, 1.6f) / 1.6f;
      float b = pop(a * 1.6f, 0.3f);
      say(g, "?", 170 + i * 22, 52 - (int)(a * 20) - i * 10, mix(BG, YELLOW_DARK, b * (1 - a * a)), middle_center);
    }
  } else {
    p.frame = alive(t, OWL_HAPPY);
    jump(p, fmodf(t, 1.8f), 16, 0.32f);
  }
  shadow(g, p, GROUND);
  drawOwl(g, p);

  // gelembung judul di kanan burung hantu
  float ba = pop(t - 0.1f, 0.4f);
  if (ba > 0) {
    std::string title[2];
    useFont(g, headFont);
    int nt = wrap(g, ui.title, 228, title, 2);
    if (nt > 2) nt = 2;
    Rect r{212 + (int)((1 - ba) * 60), 30, 256, nt > 1 ? 104 : 72};
    bubble(g, r, 186, 96);
    for (int i = 0; i < nt; i++) say(g, title[i].c_str(), r.x + 18, r.y + 34 + i * 30 - (nt - 1) * 2, INK);
  }

  // pita bawah berwarna seperti umpan balik jawaban Duolingo
  float a = easeOutBack(clamp01((t - 0.2f) / 0.45f));
  int top = 180 + (int)((1 - a) * 160);
  g.clearClipRect();
  g.fillRect(0, top, W, H - top + 40, band);
  safeArea(g);
  int ix = 46, iy = top + 42;
  smoothCircle(g, ix, iy, 26, BG);
  float s = pop(t - 0.45f, 0.35f);
  if (error) {
    crossMark(g, ix, iy, s, 3.5f * s, tone);
  } else if (warn) {
    rrect(g, {ix - 3, iy - 14, 7, (int)(18 * s)}, 3, YELLOW_DARK);
    smoothCircle(g, ix, iy + 12, (int)(4 * s), YELLOW_DARK);
  } else {
    checkMark(g, ix, iy, 1.1f, s, 3.5f, tone);
  }
  useFont(g, titleFont);
  say(g, error ? "Waduh!" : warn ? "Hmm..." : "Oke!", 88, top + 30, ink);
  useFont(g, textFont);
  int y = top + 64;
  for (int i = 0; i < ui.lineCount && i < 3; i++) {
    std::string part[2];
    int c = wrap(g, ui.lines[i], W - 104, part, 2);
    for (int k = 0; k < c && k < 2 && y <= 296; k++, y += 25) say(g, part[k].c_str(), 88, y, ink);
  }
}

// ---------------------------------------------------------------- perkenalan

int currentSegment(const Ui &ui) {
  if (ui.position < 0 || ui.segCount == 0) return -1;
  int k = 0;
  for (int i = 0; i < ui.segCount; i++)
    if (ui.position >= ui.segStart[i]) k = i;
  return k;
}

float segmentEnd(const Ui &ui, int i) { return i + 1 < ui.segCount ? ui.segStart[i + 1] : ui.duration; }

float since(const Ui &ui, Gesture gesture) {
  float s = -1;
  for (int i = 0; i < ui.segCount; i++)
    if (ui.segGesture[i] == gesture && ui.position >= ui.segStart[i]) s = ui.position - ui.segStart[i];
  return s;
}

int revealed(const Ui &ui, int seg) {
  if (seg < 0) return 0;
  int len = (int)strlen(ui.segText[seg]);
  float dur = segmentEnd(ui, seg) - ui.segStart[seg];
  if (dur <= 0.1f) return len;
  return (int)ceilf(clamp01((ui.position - ui.segStart[seg]) / (dur * 0.85f)) * len);
}

// Buku terbuka yang muncul membesar; halamannya berbalik.
void bookProp(lgfx::LovyanGFX &g, int cx, int cy, float age, float t) {
  float s = pop(age, 0.4f);
  if (s <= 0) return;
  cy += (int)(sinf(t * 2.6f) * 3);
  auto R = [&](float x, float y, float w, float h, int rad, uint16_t c) {
    rrect(g, {(int)(cx + x * s), (int)(cy + y * s), (int)(w * s), (int)(h * s)}, (int)(rad * s), c);
  };
  R(-42, -20, 84, 50, 8, BLUE_DARK);
  R(-40, -22, 84 - 4, 48, 8, BLUE);
  R(-36, -30, 35, 50, 6, SWAN);
  R(1, -30, 35, 50, 6, SWAN);
  R(-35, -30, 33, 47, 5, SNOW);
  R(2, -30, 33, 47, 5, SNOW);
  for (int r = 0; r < 4; r++) {
    R(-29, -21 + r * 9, r == 3 ? 14 : 22, 3, 1, SWAN);
    R(8, -21 + r * 9, r == 3 ? 14 : 22, 3, 1, SWAN);
  }
  float f = fmodf(age, 1.3f) / 0.5f;
  if (f < 1) {  // halaman berbalik
    float w = 33 * fabsf(cosf(f * PI_F));
    float x = f < 0.5f ? 2 : -2 - w;
    if (w > 2) R(x, -30, w, 47, 4, mix(SNOW, SWAN, 0.6f));
  }
}

// Papan klip: tiga tugas dicentang satu per satu (centang muncul membal).
void tasksProp(lgfx::LovyanGFX &g, int cx, int cy, float age) {
  float s = pop(age, 0.4f);
  if (s <= 0) return;
  auto X = [&](float v) { return (int)(cx + v * s); };
  auto Y = [&](float v) { return (int)(cy + v * s); };
  rrect(g, {X(-34), Y(-40), (int)(68 * s), (int)(84 * s)}, (int)(10 * s), ORANGE_DARK);
  rrect(g, {X(-34), Y(-42), (int)(68 * s), (int)(82 * s)}, (int)(10 * s), ORANGE);
  rrect(g, {X(-27), Y(-32), (int)(54 * s), (int)(66 * s)}, (int)(6 * s), SNOW);
  rrect(g, {X(-14), Y(-48), (int)(28 * s), (int)(14 * s)}, (int)(5 * s), EEL);
  for (int i = 0; i < 3; i++) {
    int by = Y(-18 + i * 20), bx = X(-16);
    float c = pop(age - 0.4f - i * 0.45f, 0.3f);
    smoothCircle(g, bx, by, (int)(7 * s), c > 0 ? GREEN : SWAN);
    if (c > 0) checkMark(g, bx, by, 0.42f * c, 1, 1.4f, SNOW);
    rrect(g, {X(-4), by - 2, (int)((i == 2 ? 16 : 24) * s), 4}, 2, SWAN);
  }
}

// Tombol prop yang ditekan berulang.
void buttonProp(lgfx::LovyanGFX &g, int cx, int cy, float age) {
  float s = pop(age, 0.35f);
  if (s <= 0) return;
  int w = (int)(112 * s), h = (int)(52 * s);
  float c = fmodf(age, 1.4f);
  float press = clamp01((c - 0.5f) / 0.06f) * (1 - clamp01((c - 1.1f) / 0.08f));
  int y = button3d(g, {cx - w / 2, cy - h / 2, w, h}, GREEN, GREEN_DARK, press, (int)(14 * s));
  if (s > 0.7f) {
    useFont(g, headFont);
    say(g, "TAHAN", cx, y + 1, SNOW, middle_center);
  }
}

void introScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  fillBg(g, BG);
  halo(g, W / 2, 206, 4);
  int seg = currentSegment(ui);
  Gesture gesture = seg >= 0 ? ui.segGesture[seg] : Gesture::Talk;
  float age = seg >= 0 ? ui.position - ui.segStart[seg] : 0;
  bool open = mouthOpen(ui);

  if (gesture == Gesture::Book || gesture == Gesture::Tasks) bookProp(g, 104, 112, since(ui, Gesture::Book), t);
  if (gesture == Gesture::Tasks) tasksProp(g, 382, 108, age);
  if (gesture == Gesture::Button) buttonProp(g, 380, 70, age);
  if (gesture == Gesture::Happy && age < 1.0f) {
    for (int i = 0; i < 6; i++) {
      float a = i * PI_F / 3 + 0.3f, d = 70 + easeOutCubic(age / 0.6f) * 60;
      star4(g, W / 2 + cosf(a) * d, 110 + sinf(a) * d * 0.7f, 10 * (1 - age), i % 2 ? YELLOW : BLUE);
    }
  }

  Pose p;
  p.y = 206;
  switch (gesture) {
    case Gesture::Wave:
      p.frame = waveFrame(age, open);
      p.angle = sinf(age * 6) * 6;
      jump(p, age, 12, 0.32f, 0.12f, 0.5f);
      break;
    case Gesture::Happy:
      p.frame = open ? OWL_HAPPY_TALK : OWL_HAPPY;
      jump(p, age, 14, 0.44f, 0.12f, 0.5f);
      break;
    case Gesture::Book:  // condong ke buku
      p.frame = open ? OWL_TALK : alive(t, OWL_LOOK_L, false);
      p.angle = -8 * easeOutBack(age / 0.45f);
      break;
    case Gesture::Tasks:  // condong ke papan tugas
      p.frame = open ? OWL_TALK : alive(t, OWL_LOOK_R, false);
      p.angle = 8 * easeOutBack(age / 0.45f);
      break;
    case Gesture::Button:  // mengangguk seirama tombol ditekan
      p.frame = open ? OWL_TALK : alive(t, OWL_IDLE, false);
      squash(p, 0.07f * fmaxf(0, sinf(age * PI_F / 0.7f)));
      p.angle = 4;
      break;
    case Gesture::Cheer:  // dua lompatan senang, badan miring kiri lalu kanan
      p.frame = open ? OWL_HAPPY_TALK : OWL_HAPPY;
      if (age < 0.8f) {
        jump(p, age, 14, 0.48f, 0.12f, 0.5f);
        if (inAir(age, 0.48f)) p.angle = -7 * sinf(clamp01((age - 0.12f) / 0.48f) * PI_F);
      } else {
        if (inAir(age - 0.8f, 0.36f)) p.angle = 6 * sinf(clamp01((age - 0.92f) / 0.36f) * PI_F);
        jump(p, age - 0.8f, 10, 0.36f, 0.12f, 0.5f);
      }
      break;
    default:
      p.frame = open ? OWL_TALK : alive(t, OWL_IDLE, false);
  }
  if (seg < 0) p.frame = alive(t, OWL_IDLE, false);
  if (open) squash(p, -0.04f);
  breathe(p, t, 0.015f);
  shadow(g, p, GROUND);
  drawOwl(g, p);
  if (gesture == Gesture::Cheer) confettiBurst(g, age, W / 2, 90, 40, 320);

  // teks yang diucapkan, diketik mengikuti suara
  Rect cap{16, 222, 448, 62};
  bubble(g, cap, W / 2, 212, true);
  if (seg >= 0) {
    useFont(g, headFont);
    std::string lines[3];
    int n = wrap(g, ui.segText[seg], cap.w - 40, lines, 3);
    if (n > 2) n = 2;
    int shown = revealed(ui, seg);
    int y = cap.y + (cap.h - 4) / 2 - (n - 1) * 13;
    for (int i = 0; i < n; i++, y += 26) {
      int x = W / 2 - g.textWidth(lines[i].c_str()) / 2;
      int take = shown < 0 ? 0 : (shown < (int)lines[i].size() ? shown : (int)lines[i].size());
      say(g, lines[i].substr(0, take).c_str(), x, y, INK);
      shown -= (int)lines[i].size() + 1;
    }
  }
  useFont(g, smallFont);
  say(g, "Tekan tombol untuk melewati", W / 2, 300, FAINT, middle_center);
}

// ---------------------------------------------------------------- pemberitahuan

int32_t secondsLeft(const Ui &ui) { return ui.nowTs && ui.alertTo ? (int32_t)(ui.alertTo - ui.nowTs) : INT32_MIN; }

const char *deadlineTitle(const Ui &ui) {
  if (!strncmp(ui.alertWhen, "Hari ini", 8)) return "Deadline hari ini!";
  if (!strncmp(ui.alertWhen, "Besok", 5)) return "Deadline besok!";
  return "Deadline mendekat";
}

void calendarIcon(lgfx::LovyanGFX &g, int cx, int cy, const Ui &ui, float shake) {
  static const char *const MONTHS[] = {"JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"};
  int x = cx - 30 + (int)shake, y = cy - 30;
  rrect(g, {x, y + 4, 60, 58}, 12, RED_DARK);
  rrect(g, {x, y, 60, 58}, 12, SNOW);
  rrect(g, {x, y, 60, 20}, 12, mix(RED, SNOW, 0.0f));
  g.fillRect(x, y + 12, 60, 8, RED);
  g.fillRect(x, y + 18, 60, 2, RED_DARK);
  if (!ui.alertTo) return;
  time_t local = (time_t)ui.alertTo + 7 * 3600;  // WIB
  struct tm tm;
  gmtime_r(&local, &tm);
  char day[4];
  snprintf(day, sizeof day, "%d", tm.tm_mday);
  useFont(g, smallFont);
  say(g, MONTHS[tm.tm_mon % 12], x + 30, y + 10, SNOW, middle_center);
  useFont(g, titleFont);
  say(g, day, x + 30, y + 39, EEL, middle_center);
}

void attendedScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  float t = ui.t;
  // Gelap: cap putih bercentang hijau. Terang: cap hijau bercentang putih. Keduanya bercahaya hijau.
  const uint16_t bg = BG, soft = DARK ? GREEN : GREEN_DARK;
  const uint16_t stampFace = DARK ? SNOW : GREEN, stampInk = DARK ? GREEN : SNOW;
  fillBg(g, bg);
  halo(g, 108, 236, 3);
  confettiRain(g, t, 26);
  confettiBurst(g, t - 0.4f, 352, 92, 30, 280);

  Pose p;
  p.scale = 3;
  p.x = 108;
  p.y = 236;
  p.frame = OWL_HAPPY;
  // dua lompatan senang, lalu hop kecil tiap 2 s; badan sedikit miring di udara
  float c = t < 1.9f ? fmodf(t, 0.95f) : fmodf(t - 1.9f, 2.0f);
  jump(p, c, t < 1.9f ? 22 : 10, 0.4f);
  if (inAir(c, 0.4f)) p.angle = -6 * sinf(clamp01((c - 0.12f) / 0.4f) * PI_F);
  breathe(p, t);
  shadow(g, p, GROUND);
  drawOwl(g, p);

  // cap centang: lingkaran membesar membal, centang tergores
  float s = pop(t - 0.1f, 0.45f);
  int cx = 352, cy = 92, r = (int)(56 * s);
  if (r > 0) {
    float ring = clamp01((t - 0.45f) / 0.6f);
    if (ring > 0 && ring < 1) {
      int rr = r + 6 + (int)(ring * 12);
      g.fillArc(cx, cy, rr, rr + 5, 0, 360, mix(stampFace, bg, ring));
    }
    smoothCircle(g, cx, cy + 3, r + 24, mix(BG, GREEN, DARK ? 0.14f : 0.16f));
    smoothCircle(g, cx, cy + 6, r, GREEN_DARK);
    smoothCircle(g, cx, cy, r, stampFace);
    checkMark(g, cx, cy + 2, 2.2f * s, clamp01((t - 0.35f) / 0.35f), 7 * s, stampInk);
  }
  float ta = pop(t - 0.55f, 0.4f);
  if (ta > 0) {
    int dy = (int)((1 - ta) * 30);
    const char *title = "Presensi tercatat!";
    constexpr int TEXT_W = 2 * (W - MARGIN - 352);  // berpusat di x 352
    useFont(g, titleFont);
    if (g.textWidth(title) > TEXT_W) useFont(g, headFont);
    say(g, title, cx, 182 + dy, INK, middle_center);
    useFont(g, textFont);
    say(g, fitWidth(g, ui.alertCourse, TEXT_W).c_str(), cx, 214 + dy, soft, middle_center);
    char sub[sizeof ui.alertWhen + sizeof ui.alertDetail + 4];
    snprintf(sub, sizeof sub, "%s%s%s", ui.alertWhen, ui.alertDetail[0] ? " - " : "", ui.alertDetail);
    useFont(g, smallFont);
    say(g, fitWidth(g, sub, TEXT_W).c_str(), cx, 240 + dy, MUTED, middle_center);
  }
  useFont(g, smallFont);
  say(g, "Tekan tombol untuk menutup", W / 2, 300, FAINT, middle_center);
}

void alertScreen(lgfx::LovyanGFX &g, const Ui &ui) {
  if (ui.alert == Alert::Attended) {
    attendedScreen(g, ui);
    return;
  }
  float t = ui.t;
  bool attend = ui.alert == Alert::Attendance;
  uint16_t band = attend ? ORANGE : RED, bandDark = attend ? ORANGE_DARK : RED_DARK;
  fillBg(g, BG);
  halo(g, 380, 222, 3);

  // pita atas turun dari atas
  int off = (int)((1 - easeOutCubic(t / 0.3f)) * -100);
  g.clearClipRect();
  g.fillRect(0, off, W, 88, band);
  g.fillRect(0, off + 88, W, 5, bandDark);
  safeArea(g);
  if (attend) {
    // berdering 0,9 s tiap 3 s; riak hanya saat berdering
    float ph = fmodf(t, 3.0f);
    bool ringing = ph < 0.9f;
    float swing = ringing ? sinf(t * 18) * 6 * (1 - ph / 0.9f) : 0;
    for (int k = 0; ringing && k < 2; k++) {
      float a = clamp01((ph - k * 0.3f) / 0.6f);
      int r = 31 + (int)(a * 4);
      if (a > 0 && a < 1) g.fillArc(54, 48 + off, r, r + 3, 0, 360, mix(SNOW, band, a));
    }
    smoothCircle(g, 54, 50 + off, 30, bandDark);
    smoothCircle(g, 54, 48 + off, 30, SNOW);
    bellIcon(g, 54, 50 + off, 0.75f, swing, YELLOW, YELLOW_DARK);
  } else {
    float b = fmodf(t, 1.2f);
    calendarIcon(g, 54, 46 + off, ui, b < 0.3f ? sinf(t * 60) * 3 : 0);
  }
  useFont(g, titleFont);
  say(g, attend ? "PRESENSI DIBUKA!" : deadlineTitle(ui), 100, 34 + off, SNOW);
  useFont(g, textFont);
  say(g, fitWidth(g, ui.alertCourse, 200).c_str(), 100, 66 + off, mix(band, SNOW, 0.85f));

  // burung hantu di kanan, menimpa tepi pita
  Pose p;
  p.scale = 3;
  p.x = 380;  // sayap melambai sampai kolom 58 sprite: kanan 380 + 29 * 3 = 467
  p.y = 222;
  if (attend) {  // sekali melompat sambil melambai saat muncul, lalu tenang dan sesekali melambai
    float c = fmodf(t, 4.0f);
    p.frame = alive(t, OWL_IDLE);
    breathe(p, t);
    if (t < 1.1f) {
      p.frame = waveFrame(t, true);
      jump(p, t, 14, 0.34f, 0.1f, 0.6f);
    } else if (c > 2.6f && c < 3.8f) {
      p.frame = waveFrame(c - 2.6f);
      p.angle = sinf((c - 2.6f) * 5) * 3;
    }
    star4(g, 318, 132, 4 + 2 * sinf(t * 2.2f), YELLOW);
    star4(g, 462, 160, 3 + 2 * sinf(t * 2.2f + 2), BLUE);
  } else {  // cemas: gemetar, sesekali menelan ludah, keringat
    p.frame = alive(t, OWL_WORRIED, false);
    p.x += sinf(t * 45) * 1.5f;
    squash(p, wobble(fmodf(t, 1.6f), 0.1f, 18, 5));
    float k = fmodf(t, 1.4f) / 1.4f;
    int dx = 446, dy = 110 + (int)(k * 30);
    uint16_t c = mix(BLUE, BG, k * k);
    smoothCircle(g, dx, dy + 6, 6, c);
    g.fillTriangle(dx - 5, dy + 4, dx + 5, dy + 4, dx, dy - 7, c);
  }
  shadow(g, p, GROUND);
  drawOwl(g, p);

  // kartu rincian masuk dari kiri
  float ca = pop(t - 0.15f, 0.45f);
  if (ca > 0) {
    Rect r{16 - (int)((1 - ca) * 330), 106, 292, 118};
    card(g, r);
    int x = r.x + 50, w = r.w - 64;
    useFont(g, textFont);
    if (attend) {
      pinIcon(g, r.x + 24, r.y + 26, 1.3f, RED);
      say(g, fitWidth(g, ui.alertDetail[0] ? ui.alertDetail : "Ruang kelas", w).c_str(), x, r.y + 26, INK);
      if (ui.alertQr) {  // kode QR kecil
        int qx = r.x + 14, qy = r.y + 46;
        rrect(g, {qx, qy, 20, 20}, 3, INK);
        g.fillRect(qx + 3, qy + 3, 6, 6, SURFACE);
        g.fillRect(qx + 11, qy + 3, 6, 6, SURFACE);
        g.fillRect(qx + 3, qy + 11, 6, 6, SURFACE);
        g.fillRect(qx + 12, qy + 12, 4, 4, SURFACE);
      } else {
        rrect(g, {r.x + 16, r.y + 44, 14, 24}, 3, INK);
        g.fillRect(r.x + 18, r.y + 48, 10, 14, SURFACE);
      }
      say(g, ui.alertQr ? "Scan QR di kelas" : "Isi di portal SATU", x, r.y + 56, INK);
      clockIcon(g, r.x + 24, r.y + 88, 11, t * 0.5f, ORANGE);
      useFont(g, headFont);
      say(g, ui.alertWhen, x, r.y + 88, ORANGE_DARK);
    } else {
      std::string lines[3];
      int n = wrap(g, ui.alertDetail, r.w - 32, lines, 3);
      if (n > 2) lines[1] = fitWidth(g, (lines[1] + " " + lines[2]).c_str(), r.w - 32);
      for (int i = 0; i < n && i < 2; i++) say(g, lines[i].c_str(), r.x + 16, r.y + 24 + i * 26, INK);
      clockIcon(g, r.x + 26, r.y + 88, 11, t * 0.5f, RED);
      useFont(g, headFont);
      say(g, ui.alertWhen, r.x + 46, r.y + 88, RED_DARK);
    }
  }

  // sisa waktu: teks + bar menyusut yang berubah warna makin mendesak
  int32_t s = secondsLeft(ui);
  float total = attend ? (ui.alertTo > ui.alertFrom ? (float)(ui.alertTo - ui.alertFrom) : 1800) : 48 * 3600;
  float frac = s == INT32_MIN ? 1 : clamp01(s / total);
  char text[40], d[24];
  if (s == INT32_MIN) {
    snprintf(text, sizeof text, "%s", ui.alertWhen);
  } else if (s <= 0) {
    snprintf(text, sizeof text, attend ? "Presensi sudah tutup" : "Sudah lewat");
  } else {
    duration(d, sizeof d, s);
    snprintf(text, sizeof text, attend ? "Sisa %s" : "%s lagi", d);
  }
  uint16_t color = frac > 0.5f ? GREEN : frac > 0.2f ? ORANGE : RED;
  float fa = clamp01((t - 0.35f) / 0.3f);
  if (fa > 0) {
    clockIcon(g, 30, 246, 12, t, mix(BG, color, fa));
    useFont(g, headFont);
    say(g, text, 50, 247, mix(BG, color, fa));
    pill(g, 16, 266, 448, 18, frac * fa, color, EDGE);
  }
  useFont(g, smallFont);
  say(g, "Tekan tombol untuk menutup", W / 2, 300, FAINT, middle_center);
}

// ---------------------------------------------------------------- notifikasi kecil

void toast(lgfx::LovyanGFX &g, const Ui &ui) {
  if (ui.toastT < 0 || ui.toastT >= TOAST_SECONDS || !ui.toast[0]) return;
  float in = pop(ui.toastT, 0.35f), out = clamp01((TOAST_SECONDS - ui.toastT) / 0.25f);
  useFont(g, smallFont);
  int w = g.textWidth(ui.toast) + 40;
  Rect r{W / 2 - w / 2, H - 50 + (int)((1 - in * out) * 60), w, 38};
  int cy = button3d(g, r, DARK ? RAISED : EEL, DARK ? EDGE : rgb(0x2E2E2E), 0, 17);
  say(g, ui.toast, W / 2, cy + 1, SNOW, middle_center);
}

}  // namespace

void begin(bool) {
  load(logoFont, new_ui_logo, sizeof new_ui_logo);
  load(titleFont, new_ui_title, sizeof new_ui_title);
  load(headFont, new_ui_head, sizeof new_ui_head);
  load(textFont, new_ui_text, sizeof new_ui_text);
  load(smallFont, new_ui_small, sizeof new_ui_small);
}

void background(lgfx::LovyanGFX &g) { g.fillScreen(BG); }

void render(lgfx::LovyanGFX &canvas, const Ui &ui, bool, void (*push)(const Rect &area)) {
  safeArea(canvas);
  switch (ui.kind) {
    case Kind::Boot: bootScreen(canvas, ui); break;
    case Kind::Home: homeScreen(canvas, ui); break;
    case Kind::Listen: listenScreen(canvas, ui); break;
    case Kind::Think: thinkScreen(canvas, ui); break;
    case Kind::Answer: answerScreen(canvas, ui); break;
    case Kind::Portal: portalScreen(canvas, ui); break;
    case Kind::Notice: noticeScreen(canvas, ui); break;
    case Kind::Sleep: sleepScreen(canvas, ui); break;
    case Kind::Alert: alertScreen(canvas, ui); break;
    case Kind::Intro: introScreen(canvas, ui); break;
  }
  toast(canvas, ui);
  canvas.clearClipRect();
  push({0, 0, W, H});
}

}  // namespace scene
