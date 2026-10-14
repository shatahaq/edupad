"""Ubah font TTF jadi font VLW (huruf halus/anti-aliasing) untuk LovyanGFX, sebagai array C.

Contoh:
  python3 make_font.py fonts/Nunito.ttf ../edupad/ui_fonts.h \
      ui_black_44=Black:44:EduPad ui_semibold_19=SemiBold:19

Tiap argumen setelah file keluaran: nama_array=Ketebalan:ukuran_piksel[:huruf]. Ketebalan
hanya untuk font variabel (lihat nama yang tersedia lewat pesan galat bila salah). Tanpa
[:huruf], semua ASCII 0x20-0x7E disertakan; dengan [:huruf] hanya huruf itu (font judul).
"""

import struct
import sys

from PIL import Image, ImageDraw, ImageFont

ASCII = "".join(chr(c) for c in range(0x20, 0x7F))


def vlw(path: str, weight: str, size: int, chars: str = ASCII) -> bytes:
    font = ImageFont.truetype(path, size)
    names = (
        [n.decode() for n in font.get_variation_names()]
        if hasattr(font, "get_variation_names")
        else []
    )
    if names:
        if weight not in names:
            sys.exit(f"Ketebalan {weight!r} tidak ada; pilih salah satu: {', '.join(names)}")
        font.set_variation_by_name(weight)
    ascent, descent = font.getmetrics()

    headers, bitmaps = [], []
    chars = sorted(set(chars))
    for ch in chars:
        advance = round(font.getlength(ch))
        x0, y0, x1, y1 = font.getbbox(ch, anchor="ls")  # relatif ke garis dasar
        w, h = max(x1 - x0, 0), max(y1 - y0, 0)
        if ch == " " or not w or not h:
            w = h = 0
            x0 = y0 = 0
        else:
            img = Image.new("L", (w, h), 0)
            ImageDraw.Draw(img).text((-x0, -y0), ch, font=font, fill=255, anchor="ls")
            bitmaps.append(img.tobytes())
        # unicode, tinggi, lebar, xAdvance, jarak atas dari garis dasar, geser kiri, cadangan
        headers.append(struct.pack(">7i", ord(ch), h, w, advance, -y0, x0, 0))

    head = struct.pack(">6i", len(chars), 11, size, 0, ascent, descent)
    return head + b"".join(headers) + b"".join(bitmaps)


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    ttf, out, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
    lines = [
        "// Dibuat oleh firmware/tools/make_font.py, jangan diedit manual.",
        "// Font Nunito (SIL Open Font License 1.1), https://fonts.google.com/specimen/Nunito",
        "#pragma once",
        "",
        "#include <stdint.h>",
        "",
    ]
    for spec in specs:
        name, rest = spec.split("=")
        weight, size, *chars = rest.split(":", 2)
        data = vlw(ttf, weight, int(size), chars[0] if chars else ASCII)
        lines.append(f"// {weight} {size} px, {len(data)} byte")
        lines.append(f"static const uint8_t {name}[] = {{")
        for i in range(0, len(data), 24):
            lines.append("  " + ",".join(str(b) for b in data[i : i + 24]) + ",")
        lines.append("};")
        lines.append("")
        print(f"{name}: {len(data)} byte")
    with open(out, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
