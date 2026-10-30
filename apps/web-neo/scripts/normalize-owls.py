#!/usr/bin/env python3
"""Rapikan owl hasil generator agar tujuh-tujuhnya sejajar saat dipasang berjajar.

Masukan : web-neo/art-src/owls-raw/<nama>.png  (hasil mentah dari codex/imagegen)
Keluaran: web-neo/public/owls/<nama>.png       (dipotong ke isi, dipusatkan, ukuran sama)

Dipakai sekali setiap kali ada owl baru:
    ~/.venvs/onetake/bin/python -I web-neo/scripts/normalize-owls.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OWLS = ["nova", "pixel", "sora", "tempo", "metric", "koin", "nexus"]
# Owl tampil paling besar 96 px di layar; 384 px sudah tajam di layar retina dan ringan.
CANVAS = 384
# Tinggi isi yang sama untuk semua owl; sisanya jadi ruang kosong atas-bawah.
CONTENT_HEIGHT = 330

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "art-src" / "owls-raw"
OUT = ROOT / "public" / "owls"


def normalize(name: str) -> str:
    source = RAW / f"{name}.png"
    image = Image.open(source).convert("RGBA")
    box = image.getbbox()
    if box is None:
        raise SystemExit(f"{source}: gambar kosong")
    content = image.crop(box)

    scale = CONTENT_HEIGHT / content.height
    size = (max(1, round(content.width * scale)), CONTENT_HEIGHT)
    if size[0] > CANVAS:  # owl yang melebar (mis. membawa rak) tetap muat
        scale = CANVAS / content.width
        size = (CANVAS, max(1, round(content.height * scale)))
    content = content.resize(size, Image.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(content, ((CANVAS - size[0]) // 2, (CANVAS - size[1]) // 2), content)
    # Gambarnya warna datar: 64 warna sudah cukup dan berkasnya jadi jauh lebih kecil.
    canvas = canvas.quantize(colors=64, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    OUT.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT / f"{name}.png", optimize=True)
    kb = (OUT / f"{name}.png").stat().st_size // 1024
    return f"{name}: isi {box[2] - box[0]}x{box[3] - box[1]} -> {size[0]}x{size[1]} di {CANVAS}x{CANVAS} ({kb} KB)"


def main() -> int:
    missing = [owl for owl in OWLS if not (RAW / f"{owl}.png").exists()]
    if missing:
        print(f"belum ada di {RAW}: {', '.join(missing)}", file=sys.stderr)
    for owl in OWLS:
        if (RAW / f"{owl}.png").exists():
            print(normalize(owl))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
