---
course_id: "38406"
course: "[TIF 3 030 P] Praktikum Manajemen Sistem Basis Data - Kelas 5/B"
pertemuan: 4
section: "04 - Tata Kelola Data (Data Dictionary)"
section_index: 4
title: "Pertemuan 4"
type: "resource"
source_file: "38406_[TIF 3 030 P] Praktikum Manajemen Sistem Basis Data - Kelas/04_04 - Tata Kelola Data (Data Dictionary)/Pertemuan 4.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/639629/mod_resource/content/2/Pertemuan%204.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=211079"
converter: "pymupdf4llm+ocr(5 hal)"
---

<!-- halaman 1 (OCR) -->

## Aslab Teknik **`Praktikum Manajemen Sistem Basis Data`**

Tata Kelola Data (Data Dictionary) Asisten Laboratorium: Bernita Agustien P Habeahan

<!-- halaman 2 -->

#### `Kenapa Database Perlu Didokumentasikan?`
Database bukan hanya soal menyimpan data. Tim yang bekerja dengannya juga perlu memahami struktur dan makna setiap kolom di dalamnya.

Tabel apa saja yang tersedia?

Kolom tersebut menyimpan data apa?

Apa tipe datanya?

Apakah kolom boleh NULL?

Apa arti kolom tersebut dalam konteks bisnis?

<!-- halaman 3 (OCR) -->

### `Apa itu Data Dictionary?`
Data Dictionary adalah dokumentasi yang berisi informasi atau metadata tentang struktur data dalam database.

CONTOH ENTRI DATA DICTIONARY DATA i  usa — minuns a  is Nama tabel products pada stock_quantity. Nama kolom stock_quantity METADATA Tipe data integer # Informasi tentang data itu – misalnya nama Nullable NO kolom, tipe data, dan apakah boleh NULL. Default 0 Keterangan Jumlah stok tersedia Metadata = data tentang data.

DATA i  usa — minuns a  is pada stock_quantity.

<!-- halaman 4 -->

### `Data Dictionary dari Metadata Database`
PostgreSQL menyediakan metadata yang dapat diambil menggunakan information_schema. Informasi yang dapat diambil:

table_name

column_name

data_type

is_nullable

column_default

<!-- halaman 5 -->

### `Generate Daftar Kolom`
Buka Supabase → SQL Editor → jalankan query berikut.

```
query.sql
```

```
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
```

```
where table_schema = 'public'
```

```
 and table_name in ('orders', 'order_items', 'products', 'customers')
order by table_name, ordinal_position;
```

###### Amati hasilnya:

<!-- halaman 6 (OCR) -->

### `Metadata Saja Belum Cukup`
STRUKTUR KOLOM
products
# stock_quantity integer

**"Apakah kita langsung tahu apa arti stock_quantity?"** Struktur database memberi tahu bentuk data, tetapi belum tentu menjelaskan makna bisnisnya.

DARI STRUKTUR MENUJU MAKNA

Struktur Kolom Nama, tipe data, dan aturan teknis lainnya.

? Belum tentu menjelaskan konteks bisnis.

Business Meaning Makna kolom dalam proses bisnis nyata.

Kita membutuhkan dokumentasi tambahan.

<!-- halaman 7 -->

### `COMMENT ON`
PostgreSQL menyediakan COMMENT ON untuk menyimpan keterangan langsung pada tabel atau kolom.

```
comment_on.sql
```

```
comment on table products
is 'Master data produk yang dijual di bearkerb';
```

```
comment on column products.stock_quantity
is 'Jumlah stok tersedia saat ini; tidak boleh negatif
(dijaga CHECK constraint)';
```

<!-- halaman 8 -->

### `Tambahkan Dokumentasi Bisnis`
business_docs.sql

```
comment on table products
is 'Master data produk yang dijual di bearkerb';
comment on column products.stock_quantity
is 'Jumlah stok tersedia saat ini; tidak boleh negatif (dijaga CHECK constraint)';
```

```
comment on table order_items
```

```
is 'Rincian item per pesanan (relasi many-to-many antara orders dan products)';
```

```
comment on column order_items.unit_price
is 'Harga produk SAAT pesanan dibuat — sengaja disimpan terpisah dari
 products.price supaya histori transaksi tidak berubah kalau harga
 produk naik/turun di kemudian hari';
```

```
comment on column orders.status
is 'Status pesanan: pending | completed | cancelled';
```

<!-- halaman 9 -->

### `Dari Metadata + Komentar Menjadi Data Dictionary`
Metadata memberikan informasi struktur, sedangkan COMMENT ON memberikan keterangan atau makna bisnis.

<!-- halaman 10 -->

### `Tampilkan Data Dictionary`
```
select
```

```
    c.table_name,
    c.column_name,
    c.data_type,
    pgd_table.description as komentar_tabel,
    pgd_column.description as komentar_kolom
from information_schema.columns c
left join pg_catalog.pg_statio_all_tables st
    on c.table_name = st.relname
    and c.table_schema = st.schemaname
left join pg_catalog.pg_description pgd_table
    on pgd_table.objoid = st.relid
    and pgd_table.objsubid = 0
left join pg_catalog.pg_description pgd_column
    on pgd_column.objoid = st.relid
    and pgd_column.objsubid = c.ordinal_position
where c.table_schema = 'public'
  and c.table_name in (
      'orders',
      'order_items',
      'products',
      'customers'

order by c.table_name, c.ordinal_position
```

data_dictionary.sql

<!-- halaman 11 -->

### `Audit Naming Convention`
Nama tabel menggunakan snake_case dan bentuk jamak Foreign key menggunakan nama yang sama dengan primary key yang direferensikan Kolom tanggal murni berakhiran _date

Primary key menggunakan format <table_singular>_id Kolom timestamp berakhiran _at

Nilai status/enum terdokumentasi dengan jelas

<!-- halaman 12 -->

### `Database Detective`
Buat data dictionary untuk tabel:

addresses
payments reviews
shipments
1
Tampilkan nama kolom, tipe data, nullable, default, serta komentar tabel dan kolom.

Gabungkan hasilnya menjadi satu data dictionary untuk 8 tabel:

orders order_items
customers
products
2
addresses
payments shipments reviews

Tambahkan COMMENT ON untuk:
3
departments  employees  categories  reviews

<!-- halaman 13 -->

### `Database Detective`
- Temukan 1 kolom yang namanya masih dapat menimbulkan salah pemahaman.

- **4** Pilih selain unit_price

Jelaskan mengapa kolom tersebut dapat disalahpahami, lalu buat COMMENT ON **5** COLUMN untuk memperjelas maknanya.

<!-- halaman 14 (OCR) -->

```
QUIZS
```

<!-- halaman 15 -->

##### Apa tujuan utama Data Dictionary?
A. Menyimpan seluruh data transaksi B. Menjelaskan struktur dan metadata database C. Menghapus data yang tidak digunakan D. Mempercepat semua query database

**Jawaban: B**

<!-- halaman 16 -->

**information_schema digunakan untuk apa?** A. Menyimpan data pelanggan B. Menyimpan hasil backup database C. Menyediakan informasi tentang struktur database D. Menjalankan aplikasi web

**Jawaban: C**

<!-- halaman 17 -->

##### Apa fungsi WHERE pada query berikut?
```
select table_name, column_name
from information_schema.columns
where table_schema = 'public';
```

##### Apa yang dihasilkan query tersebut?
A. Isi seluruh record dari semua tabel B. Daftar tabel, kolom, dan tipe data kolom C. Daftar komentar pada tabel D. Daftar user yang memiliki akses database **Jawaban: C**

<!-- halaman 18 -->

##### Perhatikan kode berikut:
```
comment on table products
is 'Master data produk yang dijual di SIMTOKO';
```

**Kode tersebut digunakan untuk...**

A. Menambahkan kolom baru ke products B. Memberikan komentar pada tabel products C. Memberikan komentar pada seluruh data produk D. Mengubah nama tabel products

**Jawaban: C**

<!-- halaman 19 -->

**Kalau ingin memberikan keterangan pada kolom stock_quantity, syntax yang tepat adalah...** A. `comment on table products.stock_quantity is 'Jumlah stok tersedia';` B. `comment products.stock_quantity` **Jawaban: C** `is 'Jumlah stok tersedia';` C. `comment on column products.stock_quantity is 'Jumlah stok tersedia';` D. `comment on row products.stock_quantity is 'Jumlah stok tersedia';`

**Jawaban: C**

<!-- halaman 20 (OCR) -->

# `THANKS!`
@nitagustienp
