"""Ubah <nama>.rgb dari preview menjadi <nama>.gif dan satu PNG (frame 2/3) per layar.

python3 make_gif.py out_dir [fps]
"""

import sys
from pathlib import Path

from PIL import Image

W, H = 480, 320
out = Path(sys.argv[1])
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
size = W * H * 3
for src in sorted(out.glob("*.rgb")):
    # dibaca per frame dan langsung dijadikan warna berindeks supaya hemat memori
    frames = []
    with src.open("rb") as f:
        while len(data := f.read(size)) == size:
            frame = Image.frombytes("RGB", (W, H), data)
            frames.append(frame.quantize(256, method=Image.Quantize.FASTOCTREE))
    frames[0].save(
        src.with_suffix(".gif"),
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / fps),
        loop=0,
    )
    frames[len(frames) * 2 // 3].convert("RGB").save(src.with_suffix(".png"))
    src.unlink()
    print(f"{src.stem}: {len(frames)} frame")
