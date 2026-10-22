# EduPad NEO — kontrak desain

Versi kedua web EduPad. Versi pertama (pixel art) ada di `web/` dan **tidak diubah**.
Isi teks, klip suara, dan angka diambil dari sumber yang sama supaya kedua versi tidak pernah
berbeda isi — hanya berbeda rupa.

## Prinsip

1. **Neo-brutalism yang disiplin, bukan tempelan.** Bidang warna datar, garis tepi hitam 3 px,
   bayangan blok keras 6 px, sudut siku. Tidak ada gradasi, bayangan kabur, atau kaca buram.
2. **Warna dipakai per bidang, bukan per elemen.** Satu bagian = satu warna dasar. Warna owl
   hanya untuk identitas owl (kartu owl & ikon), tidak dipakai sebagai hiasan di tempat lain.
3. **Isi dulu.** Angka UNESCO, kalimat batasan, dan contoh ucapan ditulis apa adanya dari
   `web/src/landing/copy.ts`. Tidak ada kalimat pemasaran tambahan, testimoni, atau logo palsu.
4. **Tanpa hiasan kosong:** tanpa emoji, tanpa ikon acak, tanpa bagian pengisi, tanpa animasi
   yang tidak menjelaskan apa pun.

## Warna

| Peran | Nilai | Dipakai untuk |
|---|---|---|
| `paper` | `#FFFDF5` | latar utama, kartu |
| `bone` | `#F3EADA` | latar bagian selang-seling |
| `ink` | `#111111` | teks, semua garis tepi, bidang gelap |
| `pop-yellow` | `#FFD400` | bidang "Cara kerja", tombol utama |
| `pop-cyan` | `#35C8F3` | aksen data/grafik |
| `pop-red` | `#FF5A5F` | peringatan & angka ketimpangan |
| `owl.*` | lihat `tailwind.config.js` | kepala kartu owl saja |

Teks di atas warna pop selalu `ink`. Teks di atas `ink` selalu `paper`. Tidak ada teks abu muda
di atas warna terang.

## Huruf

- Judul: **Archivo Black** (`font-display`). Hanya untuk h1–h3 dan label kecil huruf besar.
- Teks: **Space Grotesk** (`font-sans`), 17 px, tinggi baris 1.6, lebar baris maksimal ~68 karakter.
- Angka selalu memakai `font-sans` dengan `tabular-nums` — tidak pernah memakai font judul.
  (Pelajaran dari versi pertama: angka di font hias salah dibaca, "21 Okt" terbaca "81 Okt".)

## Bentuk

- Garis tepi: `border-3 border-ink` (`border-5` untuk bingkai besar).
- Bayangan: `shadow-neo` (6 px). Kartu kecil `shadow-neo-sm` (4 px).
- Sudut: siku. Satu-satunya pengecualian: tombol pil pada pemilih bahasa.
- Jarak antar bagian: 80 px (mobile 56 px). Ritme spasi kelipatan 8.

## Gerak

- Tombol & kartu yang bisa ditekan: naik 2 px saat hover, turun ke 2 px bayangan saat ditekan.
- Baris berjalan (marquee) hanya di satu tempat, berhenti saat `prefers-reduced-motion`.
- Tidak ada animasi masuk saat gulir.

## Aset gambar (dibuat codex + imagegen)

Syarat lulus sebelum dipakai:

1. PNG RGBA, latar benar-benar transparan (alpha minimum 0).
2. Outline hitam dengan ketebalan seragam antar aset.
3. Tanpa gradasi dan tanpa bayangan kabur yang ikut terbakar di gambar
   (bayangan datang dari CSS supaya bisa dipasang di atas warna apa pun).
4. Setelah jadi: dirapikan dengan `scripts/normalize-owls.py` → dipotong ke isi, dipusatkan,
   dan disamakan ukurannya (1024×1024) supaya tujuh owl sejajar dalam satu baris.
5. Aset yang bentuknya aneh (jari/sayap ganda, mata tidak sejajar, aksesori salah) dibuat ulang,
   tidak "diperbaiki" dengan memperkecil ukurannya.

## Aksesibilitas

- Kontras teks minimal 4.5:1; garis tepi hitam membantu, tetapi bukan pengganti kontras teks.
- `:focus-visible` tebal (3 px) dengan offset, terlihat di atas warna terang maupun gelap.
- Setiap bagian punya judul yang dirujuk `aria-labelledby`.
- Grafik dibangun dari SVG dengan ringkasan teks untuk pembaca layar.
