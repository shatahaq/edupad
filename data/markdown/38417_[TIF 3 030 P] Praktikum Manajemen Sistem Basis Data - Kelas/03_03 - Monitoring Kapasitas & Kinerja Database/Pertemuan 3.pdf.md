---
course_id: "38417"
course: "[TIF 3 030 P] Praktikum Manajemen Sistem Basis Data - Kelas 5/A"
pertemuan: 3
section: "03 - Monitoring Kapasitas & Kinerja Database"
section_index: 3
title: "Pertemuan 3"
type: "resource"
source_file: "38417_[TIF 3 030 P] Praktikum Manajemen Sistem Basis Data - Kelas/03_03 - Monitoring Kapasitas & Kinerja Database/Pertemuan 3.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/637143/mod_resource/content/2/Pertemuan%203.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=209010"
converter: "pymupdf4llm+ocr(5 hal)"
---

<!-- halaman 1 (OCR) -->

## Aslab Teknik **`Praktikum Manajemen Sistem Basis Data`**

Monitoring Kapasitas & Kinerja Database Asisten Laboratorium: Bernita Agustien P Habeahan

<!-- halaman 2 -->

### `Database Juga Perlu Dipantau`
Database bukan sesuatu yang cukup dibuat lalu dibiarkan begitu saja. Selama aplikasi berjalan, database terus bekerja aktif untuk melayani setiap permintaan data.

Menyimpan data

Menerima query

Melayani koneksi

Membaca & menulis data

<!-- halaman 3 -->

### `Apa itu Monitoring Database?`
Monitoring database adalah proses mengamati kondisi dan aktivitas database untuk mengetahui apakah database bekerja normal, mengalami beban tinggi, atau memiliki masalah performa.

Performance

Capacity

Apakah kapasitas Apakah query penyimpanan masih berjalan dengan cukup? cepat?

Access Pattern Bagaimana tabel sering diakses?

Query Activity Query mana yang paling banyak menggunakan resource?

<!-- halaman 4 -->

### `Apa yang Kita Monitor?`
Database Size Ukuran keseluruhan database.

Table Size Ukuran masing-masing tabel.

Table Access Bagaimana PostgreSQL membaca data.

Query Performance Query mana yang sering / berat dijalankan..

<!-- halaman 5 -->

### `Memulai dari Gambaran Besar`
Sebelum menganalisis tabel atau query satu per satu, kita perlu melihat kondisi database secara umum terlebih dahulu.

Monitoring database dapat membantu kita melihat:

Penggunaan resource

Aktivitas database

Jumlah koneksi

Kondisi performa

<!-- halaman 6 -->

### `Seberapa Besar Database Kita?`
```
query.sql
select pg_size_pretty(
 pg_database_size(current_database())
) as db_size;
```

OUTPUT
db_size
26 MB

Database size menunjukkan total ruang penyimpanan yang digunakan oleh seluruh database.

<!-- halaman 7 -->

### `Tabel Mana yang Paling Banyak Menggunakan Storage?`
```
query.sql
```

```
select
 relname as table_name,
 pg_size_pretty(
   pg_total_relation_size(relid)
 ) as total_size
from pg_catalog.pg_statio_user_tables
order by pg_total_relation_size(relid) desc;
```

**`relname`** Nama tabel.

**`pg_total_relation_size( )`** Menghitung total ukuran tabel, termasuk data, index, dan data tambahan terkait. **`order by ... desc`** Mengurutkan hasil dari tabel terbesar ke terkecil.

<!-- halaman 8 (OCR) -->

### `Bagaimana PostgreSQL Membaca Data?`
Sequential Scan

Index Scan

PostgreSQL membaca data secara berurutan dari awal sampai akhir tabel.

PostgreSQL menggunakan index untuk membantu menemukan data secara langsung dan lebih cepat.

1 2 4 5

XEX ⇒ DATA YANG DICARI

Dibaca satu per satu secara urut

Langsung menuju lokasi data

Seperti mencari nama di daftar panjang dengan membaca satu per satu, dari awal hingga ketemu.

Seperti mencari kata melalui indeks pada buku, langsung menuju halaman yang tepat.

<!-- halaman 9 -->

### `Melihat Pola Akses Tabel`
`query.sql select relname, seq_scan, idx_scan, n_live_tup, n_dead_tup from pg_stat_user_tables order by seq_scan desc;` Angka monitoring tidak selalu berarti masalah. Data harus dibaca bersama kondisi dan aktivitas tabel, seq_scan tinggi bukan berarti database rusak.

<!-- halaman 10 (OCR) -->

### `Query Mana yang Paling Membebani Database?`
Calls Tinggi

Query sangat sering dijalankan.

Total Time Tinggi

Total waktu eksekusi yang digunakan besar.

Mean Time Tinggi

Setiap eksekusi query relatif lama.

Query Query A Query B

Calls Total Time 500 Tinggi 10 Tinggi

Mean Time

Rendah Tinggi

Query A: sering dipanggil, namun tiap eksekusi relatif ringan.

Oue e  s des det ed ue : erat

<!-- halaman 11 (OCR) -->

### `Hubungan Semua Hasil Monitoring`
Monitoring dilakukan secara bertahap, satu temuan mengarahkan kita ke langkah pemeriksaan berikutnya.

V

Database

Table Size

Access Pattern

Query Performance

Identify Problem

CONTOH ALUR PEMERIKSAAN

> 1 2 3 4 5 Database besar K Cari tabel terbesar Lihat pola akses Periksa query terkait → Tentukan perlu tabel optimasi

<!-- halaman 12 (OCR) -->

# `THANKS!`
@nitagustienp
