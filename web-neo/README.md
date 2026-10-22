# web-neo — halaman depan EduPad versi kedua

Tema **neo-brutalism**: bidang warna datar, garis tepi hitam, bayangan blok, huruf tebal.
Versi pertama (pixel art) ada di [`../web`](../web) dan **tidak diubah**; keduanya bisa jalan
berdampingan.

```bash
cd web-neo && npm install
npm run dev          # http://localhost:5180
```

`/api` dan `/auth` diteruskan ke `python -m edupad serve` (port 8000), sama seperti versi
pertama, jadi tombol **Masuk** dan pengecekan sesi bisa diuji dari sini.

## Isi halaman

Semua teks, contoh ucapan, angka UNESCO, dan dua bahasa (ID/EN) dibaca langsung dari
[`../web/src/landing/copy.ts`](../web/src/landing/copy.ts). Klip suara, tombol putar, dan bunyi
penanda Mode Suara juga memakai modul versi pertama (`AudioButton`, `cues`, `useLang`).
Jadi isi kedua versi tidak akan pernah berbeda — yang berbeda hanya rupanya.

Satu-satunya teks milik versi ini ada di `LOCAL` pada `src/pages/Landing.tsx`: keterangan
ilustrasi perangkat dan keterangan bingkai tangkapan layar dashboard.

## Aturan desain

Ada di [DESIGN.md](DESIGN.md) — palet, skala huruf, bentuk, gerak, dan syarat kelulusan aset
gambar. Satu hal yang sengaja diperbaiki dari versi pertama: **angka tidak pernah memakai huruf
judul**, karena di Pixelify Sans angka "2" terbaca seperti "8" (mis. "21 Okt" terbaca "81 Okt").

## Aset gambar

Dibuat dengan codex (model `gpt-6.1-sol`, skill `imagegen`), lalu dirapikan sendiri:

| Berkas mentah | Perintah | Hasil |
|---|---|---|
| `art-src/owls-raw/*.png` | `~/.venvs/onetake/bin/python -I scripts/normalize-owls.py` | `public/owls/*.png` — 7 owl, 384×384, isi sama tinggi, latar transparan |
| `art-src/art-raw/*.png` | `~/.venvs/onetake/bin/python -I scripts/normalize-art.py` | `public/art/*.png` — ilustrasi perangkat & "di balik layar", 64 warna |

`public/art/office-neo.png` adalah tangkapan layar asli dari `dashboard-neo`, bukan gambar buatan.

Yang belum ada: foto perangkat sungguhan (sekarang dipakai ilustrasi; alt-text menyebutnya
ilustrasi, bukan foto).
