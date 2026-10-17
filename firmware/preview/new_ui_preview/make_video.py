"""Gabungkan <nama>.rgb + <nama>.pcm dari `preview OUT VOICE_DIR` menjadi video bersuara.

python3 make_video.py out_dir [fps]

Hasil: out_dir/<nama>.mp4 per layar dan out_dir/demo.mp4 (semua layar berurutan seperti alur
pemakaian). Gambar diperbesar 2x tanpa dihaluskan (piksel LCD tetap tajam). .pcm dihapus,
.rgb dibiarkan untuk make_gif.py. Butuh ffmpeg.
"""

import subprocess
import sys
from pathlib import Path

W, H = 480, 320
RATE = 16000
# urutan demo.mp4: menyala -> perkenalan -> bertanya -> gagal -> kabar dari server -> tidur
ORDER = [
    "boot", "intro", "home", "listen", "think", "answer", "no_speech", "error", "home_next",
    "alert_presensi", "alert_hadir", "alert_deadline", "home_offline", "sleep", "wake", "portal",
]  # fmt: skip

out = Path(sys.argv[1])
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30


def encode(video: str, audio: Path, dst: Path, stdin=None) -> subprocess.Popen:
    cmd = ["ffmpeg", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", video,
           "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", str(audio),
           "-vf", "scale=iw*2:ih*2:flags=neighbor",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
           "-movflags", "+faststart", str(dst)]  # fmt: skip
    return subprocess.Popen(cmd, stdin=stdin)


scenes = sorted(p.stem for p in out.glob("*.pcm") if p.with_suffix(".rgb").exists())
for name in scenes:
    if encode(str(out / f"{name}.rgb"), out / f"{name}.pcm", out / f"{name}.mp4").wait():
        sys.exit(f"ffmpeg gagal: {name}")
    seconds = (out / f"{name}.pcm").stat().st_size / (RATE * 2)
    print(f"{name}.mp4: {seconds:.1f} s")

# demo: suara digabung di berkas sementara (kecil), gambar dialirkan langsung ke ffmpeg
demo = [n for n in ORDER if n in scenes] + [n for n in scenes if n not in ORDER]
if demo:
    audio = out / "demo.pcm.tmp"
    audio.write_bytes(b"".join((out / f"{n}.pcm").read_bytes() for n in demo))
    proc = encode("pipe:0", audio, out / "demo.mp4", stdin=subprocess.PIPE)
    for name in demo:
        with (out / f"{name}.rgb").open("rb") as f:
            while chunk := f.read(W * H * 3 * 30):
                proc.stdin.write(chunk)
    proc.stdin.close()
    if proc.wait():
        sys.exit("ffmpeg gagal: demo")
    print(f"demo.mp4: {audio.stat().st_size / (RATE * 2):.1f} s, {len(demo)} layar")
    audio.unlink()

for name in scenes:
    (out / f"{name}.pcm").unlink()
