"""Burung hantu EduPad sebagai pixel art (badan ~40 px, ditampilkan 4x), digambar per bagian
supaya tiap pose (berkedip, melambai, senang, ...) memakai bentuk yang persis sama.

  python3 owl.py out_dir                 -> out_dir/<pose>.png dan out_dir/sheet.png (diperbesar)
  python3 owl.py --header owl_sprites.h  -> semua pose sebagai array C untuk firmware
"""

import math
import sys
from pathlib import Path

from PIL import Image

W, H = 60, 52  # kanvas lebih lebar dari badan supaya sayap yang terangkat muat
OX, OY = 10, 3  # geser koordinat rancangan (badan 40 lebar) ke tengah kanvas
CX = 20.0  # sumbu simetri rancangan (di antara piksel 19 dan 20)

PAL = {
    "out": (8, 10, 24),
    "t": (28, 207, 183),  # tosca
    "tl": (126, 230, 204),  # tosca terang
    "td": (14, 160, 144),  # tosca bayangan
    "ew": (255, 248, 232),  # putih mata
    "ink": (10, 12, 26),
    "wh": (255, 255, 255),
    "or": (255, 140, 36),
    "ord": (214, 86, 26),
    "pink": (255, 143, 163),
    "cr": (253, 227, 176),
    "crd": (236, 196, 140),
    "cap": (44, 46, 74),
    "capl": (70, 74, 110),
    "capd": (24, 26, 44),
    "gold": (255, 200, 61),
    "goldd": (216, 144, 31),
    # adegan tidur: bantal dan selimut
    "pil": (214, 220, 240),
    "pild": (160, 170, 206),
    "bl": (44, 60, 150),
    "bld": (72, 94, 196),
    "blh": (112, 136, 228),
}


class Canvas:
    """Kotak piksel berisi kunci warna PAL (None = transparan). Koordinat gambar digeser
    (ox, oy); bawaan sesuai rancangan burung hantu 40 px di kanvas W x H."""

    def __init__(self, w=W, h=H, ox=OX, oy=OY):
        self.w, self.h, self.ox, self.oy = w, h, ox, oy
        self.px = [[None] * w for _ in range(h)]

    def set(self, x, y, c):
        x, y = x + self.ox, y + self.oy
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def blob(self, cx, cy, rx, ry, c, n=2.0, angle=0.0, where=None):
        """Superelips |u/rx|^n + |v/ry|^n <= 1 (n=2 elips, makin besar makin kotak)."""
        cs, sn = math.cos(angle), math.sin(angle)
        r = int(max(rx, ry)) + 2
        for y in range(int(cy) - r, int(cy) + r + 1):
            for x in range(int(cx) - r, int(cx) + r + 1):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                u, v = dx * cs + dy * sn, -dx * sn + dy * cs
                if abs(u / rx) ** n + abs(v / ry) ** n <= 1.0 and (where is None or where(x, y)):
                    self.set(x, y, c)

    def poly(self, pts, c):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if inside(pts, x + 0.5, y + 0.5):
                    self.set(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            self.set(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), c)

    def outline(self, c="out"):
        """Garis luar 1 piksel di sekeliling semua piksel terisi (4 arah)."""

        def at(x, y):
            return self.px[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

        add = [
            (x, y)
            for y in range(self.h)
            for x in range(self.w)
            if self.px[y][x] is None
            and any(
                at(x + dx, y + dy) not in (None, c) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
        ]
        for x, y in add:
            self.px[y][x] = c

    def stamp(self, other, dx=0, dy=0):
        """Tempel piksel terisi `other` dengan geser (dx, dy)."""
        for y in range(other.h):
            for x in range(other.w):
                c = other.px[y][x]
                if c is not None and 0 <= x + dx < self.w and 0 <= y + dy < self.h:
                    self.px[y + dy][x + dx] = c

    def image(self):
        img = Image.new("RGBA", (self.w, self.h))
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x]:
                    img.putpixel((x, y), PAL[self.px[y][x]] + (255,))
        return img


def inside(pts, x, y):
    hit = False
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def mirror(x):
    """Piksel kembaran di sisi kanan sumbu simetri."""
    return int(2 * CX) - 1 - x


BODY = (CX, 26, 17, 17)  # tengah x, tengah y, rx, ry


def body(c):
    bx, by, rx, ry = BODY
    # jambul telinga
    for side in (-1, 1):
        c.poly([(CX + side * 10, 12), (CX + side * 17.5, 5), (CX + side * 16.5, 14)], "t")
    c.blob(bx, by, rx, ry, "t", n=2.3)
    # bayangan bawah dan sisi, kilau kiri atas
    c.blob(
        bx, by, rx, ry, "td", n=2.4, where=lambda x, y: abs(x + 0.5 - bx) / rx > 0.78 and y > by - 4
    )
    c.blob(bx, by, rx, ry, "td", n=2.4, where=lambda x, y: y + 0.5 > by + ry - 3)
    c.blob(
        bx, by, rx, ry, "tl", n=2.4, where=lambda x, y: y + 0.5 < by - ry + 3 and x + 0.5 < bx - 4
    )
    # perut dengan sisik bulu
    c.blob(CX, 35.5, 9.5, 6.5, "cr")
    c.blob(CX, 35.5, 9.5, 6.5, "crd", where=lambda x, y: y >= 40)
    for x0, y0 in ((14, 34), (22, 34), (18, 37)):
        c.set(x0, y0, "crd")
        c.set(x0 + 1, y0 + 1, "crd")
        c.set(x0 + 2, y0 + 1, "crd")
        c.set(x0 + 3, y0, "crd")


def feet(c):
    for x0 in (11, 24):
        for dx in range(5):
            c.set(x0 + dx, 42, "or")
            if dx in (0, 2, 4):
                c.set(x0 + dx, 43, "or")
        c.set(x0 + 4, 42, "ord")
        c.set(x0 + 4, 43, "ord")


EYE_Y = 22.0


def face(c, eyes="open", look=0, look_y=0, brows=None, beak="closed"):
    """look/look_y: arah lirikan (-1..1). brows: None, "confused" (satu alis naik) atau
    "worried" (ujung dalam alis naik). beak: "closed" atau "open" (bicara)."""
    for side in (-1, 1):
        ex = CX + side * 7
        if eyes == "open":
            c.blob(ex, EYE_Y, 6.8, 6.8, "ew")
            px, py = ex + look + side * 0.5, EYE_Y + 0.5 + look_y
            c.blob(px, py, 4.3, 4.5, "ink")
            hx, hy = math.floor(px) - 2, math.floor(py) - 2
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                c.set(hx + dx, hy + dy, "wh")
            c.set(math.floor(px) + 1, math.floor(py) + 1, "wh")
        elif eyes == "wide":  # kaget: mata membesar, pupil mengecil
            c.blob(ex, EYE_Y, 7.3, 7.3, "ew")
            px = ex + side * 0.5
            c.blob(px, EYE_Y + 0.5, 2.6, 2.8, "ink")
            c.set(math.floor(px) - 1, int(EYE_Y) - 1, "wh")
        elif eyes == "squeeze":  # terpejam rapat saat menguap: > <
            tip = int(ex) + (2 if side < 0 else -3)  # ujung runcing mengarah ke paruh
            for i in range(4):
                x = tip + (-i if side < 0 else i)
                c.set(x, int(EYE_Y) - i, "out")
                c.set(x, int(EYE_Y) + i, "out")
        elif eyes == "half":  # menyipit di tengah kedipan
            c.blob(ex, EYE_Y + 1, 6.8, 2.8, "ew")
            c.blob(ex + side * 0.5, EYE_Y + 1, 4.3, 2.2, "ink")
            for dx in range(-5, 5):
                c.set(int(ex) + dx, int(EYE_Y) - 2, "out")
        elif eyes in ("closed", "sleep"):  # garis melengkung ke bawah
            for dx in range(-4, 4):
                c.set(int(ex) + dx, int(EYE_Y) + (1 if -3 <= dx <= 2 else 0), "out")
            if eyes == "sleep":  # bulu mata di ujung luar
                c.set(int(ex) + (-5 if side < 0 else 4), int(EYE_Y) + 1, "out")
        elif eyes == "happy":  # ^ ^ tebal
            for dx in range(-4, 4):
                lift = 2 if -2 <= dx <= 1 else (1 if -3 <= dx <= 2 else 0)
                c.set(int(ex) + dx, int(EYE_Y) + 1 - lift, "out")
                c.set(int(ex) + dx, int(EYE_Y) + 2 - lift, "out")
    # semu pink di bawah luar mata
    for x in (9, 10, 11):
        c.set(x, 29, "pink")
        c.set(mirror(x), 29, "pink")
    # paruh; saat terbuka tampak mulut gelap dan lidah
    if beak == "yawn":  # mulut terbuka lebar
        rows = (
            (22, 2, "or"),
            (23, 2, "or"),
            (24, 3, "ink"),
            (25, 3, "ink"),
            (26, 3, "ink"),
            (27, 3, "ink"),
            (28, 2, "ink"),
            (29, 2, "or"),
            (30, 1, "or"),
        )
    elif beak == "open":
        rows = (
            (23, 2, "or"),
            (24, 2, "or"),
            (25, 2, "ink"),
            (26, 2, "ink"),
            (27, 2, "ink"),
            (28, 1, "or"),
            (29, 1, "or"),
        )
    else:
        rows = (
            (24, 2, "or"),
            (25, 2, "or"),
            (26, 2, "or"),
            (27, 2, "or"),
            (28, 1, "or"),
            (29, 1, "or"),
        )
    for y, half, col in rows:
        for x in range(int(CX) - half, int(CX) + half):
            c.set(x, y, col)
    if beak == "yawn":
        for x in range(int(CX) - 2, int(CX) + 2):
            c.set(x, 27, "pink")
        c.set(int(CX), 30, "ord")
    elif beak == "open":
        c.set(int(CX) - 1, 27, "pink")
        c.set(int(CX), 27, "pink")
        c.set(int(CX), 24, "ord")
        c.set(int(CX), 29, "ord")
    else:
        for x, y in ((21, 26), (21, 27), (20, 28), (20, 29)):
            c.set(x, y, "ord")


def brow(c, brows):
    """Alis di atas mata, digambar setelah toga supaya tidak tertutup."""
    if brows == "confused":  # alis kiri naik miring, kanan datar
        for i, y in enumerate((15, 14, 14, 13, 13, 13)):
            c.set(8 + i, y, "out")
        for i in range(6):
            c.set(mirror(8 + i), 15, "out")
    elif brows == "up":  # kedua alis terangkat tinggi (kaget)
        for i, y in enumerate((14, 13, 13, 13, 13, 14)):
            c.set(8 + i, y, "out")
            c.set(mirror(8 + i), y, "out")
    elif brows == "worried":  # ujung dalam naik
        for i, y in enumerate((16, 16, 15, 15, 14, 14)):
            c.set(8 + i, y, "out")
            c.set(mirror(8 + i), y, "out")


def wing(c, side, raise_=0.0):
    """Sayap kiri (side=-1) atau kanan (+1); raise_ 0 = diam menempel, 1 = terangkat melambai,
    negatif = berputar ke dalam (-0.6: ujung sayap di dagu, pose berpikir)."""
    a = (0.1 + raise_ * 2.3) * side
    px, py = CX + side * 15, 28
    cx = px + math.sin(a) * 6
    cy = py + math.cos(a) * 6
    w = Canvas()
    w.blob(cx, cy, 3.6, 7.5, "td", angle=-a)
    w.blob(cx - side * 0.8 * math.cos(a), cy - 1.2, 2.2, 5.5, "t", angle=-a)
    w.outline()
    c.stamp(w)


def cap(c, tassel=0):
    # papan toga (belah ketupat), sisi bawah, dan topi bagian kepala
    c.poly([(CX - 8, 9), (CX + 8, 9), (CX + 7, 12.5), (CX - 7, 12.5)], "capd")
    c.poly([(CX - 13, 6), (CX, 0.5), (CX + 13, 6), (CX, 11.5)], "cap")
    c.poly([(CX - 13, 6), (CX, 0.5), (CX + 2, 1.5), (CX - 10, 6.5)], "capl")
    c.set(int(CX), 5, "gold")
    c.set(int(CX) - 1, 5, "gold")
    # tali dari tengah ke ujung kanan papan, lalu menggantung (tassel geser ujung -1..1)
    c.line(int(CX) + 1, 5, int(CX) + 11, 6, "gold")
    c.line(int(CX) + 12, 7, int(CX) + 12 + tassel, 11, "gold")
    bx = int(CX) + 12 + tassel
    for dy in range(4):
        c.set(bx, 12 + dy, "gold")
        c.set(bx + 1, 12 + dy, "goldd")
    c.set(bx, 15, "goldd")


def owl(**kw):
    return owl_canvas(**kw).image()


def owl_canvas(
    eyes="open", wing_l=0.0, wing_r=0.0, tassel=0, look=0, look_y=0, brows=None, beak="closed"
):
    c = Canvas()
    body(c)
    feet(c)
    face(c, eyes, look, look_y, brows, beak)
    cap(c, tassel)
    brow(c, brows)
    c.outline()
    wing(c, -1, wing_l)
    wing(c, 1, wing_r)
    return c


POSES = {
    "idle": dict(),
    "blink_half": dict(eyes="half"),
    "blink": dict(eyes="closed"),
    "wave_1": dict(wing_r=0.55, tassel=1),
    "wave_2": dict(wing_r=1.0, tassel=1),
    "happy": dict(eyes="happy", wing_l=0.85, wing_r=0.85, tassel=-1),
    "look_l": dict(look=-1),
    "look_r": dict(look=1),
    "listen": dict(look_y=-1.5),
    "talk": dict(beak="open"),
    "think": dict(wing_r=-0.5, look=1, look_y=-1.5),
    "think_blink": dict(wing_r=-0.5, eyes="closed"),
    "confused": dict(brows="confused", look=-1, look_y=-1),
    "worried": dict(brows="worried", look_y=1),
    # variasi paruh terbuka untuk gerakan sambil bicara (perkenalan diri)
    "wave_1_talk": dict(wing_r=0.55, tassel=1, beak="open"),
    "wave_2_talk": dict(wing_r=1.0, tassel=1, beak="open"),
    "happy_talk": dict(eyes="happy", wing_l=0.85, wing_r=0.85, tassel=-1, beak="open"),
    # tidur & bangun
    "yawn": dict(eyes="squeeze", beak="yawn", wing_l=0.25, wing_r=0.25),
    "surprised": dict(eyes="wide", brows="up", beak="open", wing_l=0.3, wing_r=0.3, tassel=1),
    "stretch": dict(eyes="squeeze", beak="yawn", wing_l=1.05, wing_r=1.05, tassel=-1),
}


# ---------------------------------------------------------------- adegan tidur

BED_W, BED_H = 84, 60


def scale2x(px):
    """Perbesar 2x dengan EPX/Scale2x: tepi diagonal pixel art tetap tajam."""
    h, w = len(px), len(px[0])
    out = [[None] * (2 * w) for _ in range(2 * h)]
    for y in range(h):
        for x in range(w):
            p = px[y][x]
            a = px[y - 1][x] if y > 0 else p
            b = px[y][x + 1] if x < w - 1 else p
            c = px[y][x - 1] if x > 0 else p
            d = px[y + 1][x] if y < h - 1 else p
            out[2 * y][2 * x] = a if c == a and c != d and a != b else p
            out[2 * y][2 * x + 1] = b if a == b and a != c and b != d else p
            out[2 * y + 1][2 * x] = c if d == c and d != b and c != a else p
            out[2 * y + 1][2 * x + 1] = d if b == d and b != a and d != c else p
    return out


def rotsprite(canvas, angle):
    """Putar pixel art tanpa garis tepi bergerigi (RotSprite): perbesar 8x dengan Scale2x,
    putar, lalu ambil kembali satu titik per piksel. angle dalam radian, positif = searah jarum
    jam di layar."""
    big = scale2x(scale2x(scale2x(canvas.px)))
    w, h = canvas.w, canvas.h
    cs, sn = math.cos(angle), math.sin(angle)
    ow, oh = int(abs(w * cs) + abs(h * sn)) + 2, int(abs(w * sn) + abs(h * cs)) + 2
    out = Canvas(ow, oh, 0, 0)
    for y in range(oh):
        for x in range(ow):
            dx, dy = x + 0.5 - ow / 2, y + 0.5 - oh / 2
            sx, sy = dx * cs + dy * sn + w / 2, -dx * sn + dy * cs + h / 2
            bx, by = int(sx * 8), int(sy * 8)
            if 0 <= bx < 8 * w and 0 <= by < 8 * h:
                out.px[y][x] = big[by][bx]
    return out


def bed(**face):
    """Burung hantu berbaring miring di bantal, berselimut sampai bahu. `face`: argumen wajah
    owl_canvas (bawaan: tidur)."""
    c = Canvas(BED_W, BED_H, 0, 0)
    # bantal
    c.blob(18, 41, 17, 9, "pil", n=2.6)
    c.blob(18, 41, 17, 9, "pild", n=2.6, where=lambda x, y: y >= 45 or x <= 3)
    # burung hantu, kepala miring ke bantal
    sleeper = rotsprite(owl_canvas(**({"eyes": "sleep"} | face), tassel=-1), -0.38)
    c.stamp(sleeper, -10, -5)
    # selimut: tepi atas melengkung dari bantal ke kanan, bertotol, dengan lipatan terang
    top = [(0, 56), (12, 51), (28, 46), (42, 42), (56, 39), (68, 39), (76, 42), (81, 48), (83, 54)]
    edge = top + [(84, 60), (0, 60)]
    blanket = Canvas(BED_W, BED_H, 0, 0)
    blanket.poly(edge, "bl")
    for y in range(BED_H):
        for x in range(BED_W):
            if blanket.px[y][x] and (x + 3 * (y // 4)) % 8 == 0 and y % 4 == 1:
                blanket.px[y][x] = "bld"
    for x in range(BED_W):  # garis tepi + lipatan di bawahnya
        column = [y for y in range(BED_H) if blanket.px[y][x]]
        if column:
            y0 = column[0]
            blanket.px[y0][x] = "out"
            for k in (1, 2):
                if y0 + k < BED_H:
                    blanket.px[y0 + k][x] = "blh"
            if y0 + 3 < BED_H:
                blanket.px[y0 + 3][x] = "bl"
    c.stamp(blanket)
    c.outline()
    return c


def sprite_data(canvas):
    keys = list(PAL)
    return [0 if k is None else 1 + keys.index(k) for row in canvas.px for k in row]


def write_header(path):
    """Semua pose sebagai array C: palet RGB565 (indeks 0 = transparan) + indeks per piksel."""
    rgb565 = [
        "0x%04X" % (((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)) for r, g, b in PAL.values()
    ]
    lines = [
        "// Dibuat oleh firmware/art/owl/owl.py, jangan diedit manual.",
        "#pragma once",
        "",
        "#include <stdint.h>",
        "",
        f"constexpr int OWL_W = {W};",
        f"constexpr int OWL_H = {H};",
        "// Indeks 0 transparan; indeks n memakai OWL_PAL[n - 1].",
        f"static const uint16_t OWL_PAL[] = {{{', '.join(rgb565)}}};",
        "",
    ]
    sprites = [(f"OWL_{name.upper()}", owl_canvas(**kw)) for name, kw in POSES.items()]
    sprites.append(("OWL_BED", bed()))
    sprites.append(("OWL_BED_AWAKE", bed(eyes="wide", brows="up", beak="open")))
    for name, canvas in sprites:
        data = sprite_data(canvas)
        if name == "OWL_BED":
            lines += [f"constexpr int BED_W = {BED_W};", f"constexpr int BED_H = {BED_H};"]
        lines.append(f"static const uint8_t {name}[] = {{")
        for i in range(0, len(data), canvas.w):
            lines.append("  " + ",".join(str(v) for v in data[i : i + canvas.w]) + ",")
        lines.append("};")
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--header":
        write_header(sys.argv[2])
        return
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    zoom = 4
    sheet = Image.new("RGBA", ((W * zoom + 8) * len(POSES) + 8, H * zoom + 16), (22, 30, 74, 255))
    for i, (name, kw) in enumerate(POSES.items()):
        img = owl(**kw)
        img.save(out / f"{name}.png")
        sheet.alpha_composite(
            img.resize((W * zoom, H * zoom), Image.NEAREST), (8 + i * (W * zoom + 8), 8)
        )
    sheet.save(out / "sheet.png")
    bed().image().save(out / "bed.png")
    bed(eyes="wide", brows="up", beak="open").image().save(out / "bed_awake.png")


if __name__ == "__main__":
    main()
