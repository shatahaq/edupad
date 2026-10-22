# dashboard-neo — dashboard EduPad versi kedua

Tema **neo-brutalism** untuk dashboard. Halaman, data, dan logikanya tetap milik
[`../dashboard`](../dashboard) versi pertama — yang ditambahkan hanya satu lapis tema.

```bash
cd dashboard-neo
npm run dev                       # http://localhost:5184/dashboard-neo/
VITE_DATA_SOURCE=mock npm run dev # data contoh, tanpa server
```

`node_modules` adalah symlink ke `../dashboard/node_modules`, jadi tidak perlu `npm install`
terpisah. Data diambil dari Office API (port 8001) lewat proxy, sama seperti versi pertama.

## Cara kerjanya

```
src/main.tsx
  ├─ ../dashboard/src/styles.css      struktur & tata letak   (versi pertama)
  ├─ ../dashboard/src/readability.css
  ├─ ../dashboard/src/theme.css       tema pixel art          (versi pertama)
  └─ src/neo-theme.css                HANYA rupa: warna, tepi, bayangan, huruf
```

`src/App.tsx` adalah salinan kerangka versi pertama dengan satu perbedaan: halaman **AI Office**
memakai `src/office/NeoOffice.tsx` (denah kantor berupa blok) dan bukan kantor Phaser. Dua belas
halaman lain (`HomePage`, `TasksPage`, `TutorPage`, …) diimpor apa adanya dari `../dashboard/src`,
jadi isinya selalu sama dengan versi pertama.

Owl di `public/assets/agents/owls/avatar/` adalah owl neo-brutalism dengan **nama berkas yang
sama** seperti versi pertama, sehingga seluruh halaman lama otomatis memakai gambar baru tanpa
satu pun perubahan kode di `dashboard/`.

## Yang sengaja diperbaiki dari versi pertama

| Masalah di versi pertama | Perbaikan di sini |
|---|---|
| Angka memakai huruf Pixelify: "21 Okt" terbaca "81 Okt", "62%" terbaca "68%" | semua angka memakai huruf teks dengan lebar tetap (`tabular-nums`) |
| Tabel perangkat di Monitoring terpotong di kolom sempit (kolom "Latensi" & "Status" tersembunyi) | baris yang memuat tabel dibuat satu kolom penuh |
| AI Office diam-diam menampilkan data contoh saat server tidak terhubung | ada pemberitahuan tegas "Kantor belum terhubung ke server EduPad" |
| Menu samping di layar kecil: isi di belakangnya ikut tergulir | gulir isi dikunci selama menu terbuka |

## Catatan

Warna seri grafik Recharts masih memakai nilai dari `../dashboard/src/lib/chart.ts` (dipakai
bersama kedua versi); lapisan tema hanya mengubah warna garis bantu dan teks sumbu.
