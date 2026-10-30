#!/usr/bin/env python3
"""Perkecil ilustrasi hasil generator agar ringan dibuka di halaman depan.

Masukan : web-neo/art-src/art-raw/<nama>.png  (hasil mentah dari codex/imagegen, ~1 MB)
Keluaran: web-neo/public/art/<nama>.png       (ukuran tampil, 64 warna)

    ~/.venvs/onetake/bin/python -I web-neo/scripts/normalize-art.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

# nama berkas -> lebar tampil terbesar di halaman (dikali 2 untuk layar retina)
TARGET_WIDTH = {
    "device.png": 900,
    "behind-1.png": 760,
    "behind-2.png": 760,
    "behind-3.png": 760,
    "behind-4.png": 760,
}

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "art-src" / "art-raw"
OUT = ROOT / "public" / "art"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = []
    for name, width in TARGET_WIDTH.items():
        source = RAW / name
        if not source.exists():
            missing.append(name)
            continue
        image = Image.open(source).convert("RGB")
        if image.width > width:
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
        # Ilustrasi warna datar: 64 warna sudah cukup.
        image = image.quantize(colors=64, method=Image.Quantize.FASTOCTREE)
        image.save(OUT / name, optimize=True)
        kb = (OUT / name).stat().st_size // 1024
        print(f"{name}: {image.width}x{image.height} ({kb} KB)")
    for name in missing:
        print(f"belum ada: {RAW / name}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
