# EduPad AI Office Frontend

React + TypeScript + Vite, Tailwind CSS, dan Phaser 3.

```powershell
npm install
npm run dev
```

Untuk memeriksa map dan animasi PIXEL tanpa koneksi backend, buka URL Vite dengan
`?preview=1`, misalnya `http://localhost:5173/?preview=1`. Mode ini tidak mengirim task ke API.

Vite meneruskan `/api` ke Office API di `http://127.0.0.1:8001`. Bila API belum aktif,
dashboard menampilkan data preview dengan label yang jelas. Saat API aktif, snapshot dan SSE
menjadi sumber status robot, tugas, dan activity feed.

Untuk vertical slice indexing, jalankan juga `python -m edupad office-worker` dari root proyek.
Task `index` akan di-claim worker, menjalankan fungsi indexing EduPad yang asli, lalu mengirim
status PIXEL dan workstation `knowledge-index-01` ke Phaser.

Kantor owl terbaru memakai peta struktural `edupad-office-empty-v2.png`; meja, rak server,
tanaman, dan sofa adalah 16 sprite transparan terpisah di `public/assets/office/furniture-muted/`.
Masing-masing dipasang dengan rasio asli agar tidak gepeng. Area di luar peta mengikuti lantai
kotak-kotak abu-abu kantor. Aset kantor lama tetap disimpan.

Tujuh owl menggunakan spritesheet per karakter. Saat tanpa tugas, mereka bergantian membaca,
beristirahat, dan berjalan melewati koridor lalu kembali ke tempat kerja. Gerak memakai A* di
`src/game/owlLayout.ts`, dengan batas badan, furnitur, tembok, dan celah pintu. Furnitur dapat
diletakkan di area lantai; bila titik klik mengenai rintangan, editor memilih posisi aman
terdekat. Jalur ke seluruh meja kerja tetap divalidasi agar owl tidak terkurung. Fasad tembok
menutupi owl yang sedang berjalan di belakangnya.

Klik ikon kursi di panel luar kantor untuk membuka Studio furnitur. Pilih objek, klik lantai kosong,
atau seret objek yang ada. Katalog dapat diciutkan dan dibuka lagi. Objek terpilih bisa dihapus;
klik `Selesai` untuk kembali menjelajah. Susunan disimpan otomatis di `localStorage` browser
(`edupad-owl-furniture-v2`), bukan di Office API atau Supabase. Klik objek di luar mode edit
untuk melihat gambar serta keterangannya. Gerak dan tabrakan diuji dengan
`node scripts/test-owl-navigation.mjs`.

State pekerjaan tetap berasal dari backend. Event baru menghentikan kegiatan santai dan
mengantar owl ke workstation. PIXEL menuju Knowledge Server saat indexing, bekerja selama
proses berjalan, menampilkan tanda gagal singkat saat ada masalah, lalu kembali ke pola santai
jika tidak ada tugas baru. Animasi santai dan error hanya tampilan visual, bukan status palsu
di backend. Nama ruangan muncul saat diarahkan pointer dan detail agent/ruangan terbuka saat
diklik.
