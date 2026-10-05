---
course_id: "38408"
course: "[TIF 3 031] Pemrograman Visual - Kelas 5/B"
pertemuan: 4
section: "Pertemuan 4-Operator dan Ekspresi pada Aplikasi Visual"
section_index: 4
title: "Operator dan Ekspresi pada Aplikasi Visual"
type: "resource"
source_file: "38408_[TIF 3 031] Pemrograman Visual - Kelas 5_B/04_Pertemuan 4-Operator dan Ekspresi pada Aplikasi Visual/Pertemuan4_Pemrograman Visual.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/635140/mod_resource/content/1/Pertemuan4_Pemrograman%20Visual.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=207380"
converter: "pymupdf4llm+ocr(2 hal)"
---

<!-- halaman 1 (OCR) -->

**OPERATOR & EKSPRESI dalam Visual Basic .NET Insidini Fawwaz, M.Kom** <mark>H</mark>

**Pemrograman Visual**

<!-- halaman 2 -->

**2**

## Apa itu Operator?
### Simbol yang melakukan operasi terhadap satu atau lebih nilai.

Operator

- Operand: nilai yang dioperasikan

- Operator: simbol operasinya

**25.000   × 4   =   100.000**

   - Hasil: nilai setelah operasi

- × adalah operator perkalian

Pemrograman Visual • VB.NET

<!-- halaman 3 -->

**3**

## Jenis Operator di VB.NET
Empat kelompok utama yang paling sering dipakai dalam aplikasi visual.

**Aritmatika**

**+  −  *  /  \ Mod**

**Logika And  Or  Not  Xor**

**Perbandingan =  <>  >  <  >=  <=**

**Penggabungan &**

Pemrograman Visual • VB.NET

<!-- halaman 4 -->

**4**

## Operator Aritmatika
Digunakan untuk perhitungan numerik.

Harga Jumlah
→ × → → = → 100.000
25.000 4

Contoh penggunaan lainnya: subtotal belanja, rata-rata nilai, diskon, pajak, konversi suhu.

Pemrograman Visual • VB.NET

<!-- halaman 5 -->

**5**

## Daftar Operator Aritmatika
Perhatikan perbedaan /, \ dan Mod.

|**Operator**|**Fungsi**|**Contoh**|**Hasil**|
|---|---|---|---|
|**+**|**Penjumlahan**|**10 + 5**|**15**|
|**-**|**Pengurangan**|**10 - 5**|**5**|
|*****|**Perkalian**|**10 * 5**|**50**|
|**/**|**Pembagian biasa**|**10 / 4**|**2,5**|
|**\**|**Pembagian bulat**|**10 \ 4**|**2**|
|**Mod**|**Sisa pembagian**|**10 Mod 4**|**2**|
|**^**|**Pangkat**|**2 ^ 3**|**8**|

Pemrograman Visual • VB.NET

<!-- halaman 6 -->

**6**

## Contoh: Menghitung Total Belanja
Operator aritmatika membentuk proses dari input menuju output.

Harga Jumlah Subtotal
→ × → → = →
50.000 3 150.000
Contoh VB.NET
subtotal = harga * jumlah

Pemrograman Visual • VB.NET

<!-- halaman 7 -->

**7**

## / vs \ vs Mod
Tiga operator pembagian, tiga tujuan berbeda.

/ \
Pembagian biasa Pembagian bulat
10 / 4 10 \ 4
Hasil: 2,5 Hasil: 2

**Mod Sisa pembagian** 10 Mod 4 **Hasil: 2**

Pemrograman Visual • VB.NET

<!-- halaman 8 -->

**8**

## Contoh Mod: Bilangan Genap atau Ganjil
Jika sisa pembagian oleh 2 adalah 0, bilangan tersebut genap.

Angka Sisa
→ Mod 2 → → GENAP
18 0
Contoh VB.NET
18 Mod 2 = 0

###### Pertanyaan: bagaimana hasilnya jika angkanya 17?
Pemrograman Visual • VB.NET

<!-- halaman 9 -->

**9**

## Operator Perbandingan
Membandingkan dua nilai dan menghasilkan Boolean: True atau False.

80  >=  75
Hasil: True

60  >=  75
Hasil: False

Pemrograman Visual • VB.NET

<!-- halaman 10 -->

**10**

## Daftar Operator Perbandingan
Digunakan pada keputusan, validasi, filter, dan kondisi.

Operator Arti Contoh
= Sama dengan nilai = 75
<> Tidak sama dengan status <> "Aktif"
> Lebih besar nilai > 75
< Lebih kecil stok < 5
>= Lebih besar/sama nilai >= 75
<= Lebih kecil/sama umur <= 17

Pemrograman Visual • VB.NET

<!-- halaman 11 -->

**11**

## Contoh Perbandingan: Status Kelulusan
Satu kondisi sederhana dapat menentukan keluaran aplikasi.

Nilai
→ >= 75 → True → LULUS
82

#### Ekspresi kondisi: nilai >= 75
Operator tidak menghitung nilai baru, tapi mengevaluasi hubungan dua nilai.

Pemrograman Visual • VB.NET

<!-- halaman 12 -->

**12**

## Operator Logika
Menggabungkan atau membalik kondisi Boolean.

And
Semua kondisi harus True
Not
Membalik True  False

Or
Minimal satu kondisi True
Xor
Tepat satu kondisi True

Pemrograman Visual • VB.NET

<!-- halaman 13 -->

**13**

## AND: Semua Syarat Harus Terpenuhi
Cocok ketika keputusan membutuhkan lebih dari satu syarat wajib.

Nilai >= 75 Kehadiran >= 80%
→ AND → → LULUS
True True
Kondisi A Kondisi B A And B
True True True
True False False
False True False
False False False

Pemrograman Visual • VB.NET

<!-- halaman 14 -->

**14**

## Contoh AND pada Aplikasi Akademik
Mahasiswa lulus jika nilai dan kehadiran memenuhi syarat.

**Syarat 1 Nilai ≥ 75 Syarat 2 Kehadiran ≥ 80%**

**Contoh VB.NET** `lulus = (nilai >= 75) And (kehadiran >= 80)` **Jika salah satu False → hasil False**

Pemrograman Visual • VB.NET

<!-- halaman 15 -->

**15**

## OR: Cukup Salah Satu Syarat
Cocok ketika ada beberapa alternatif yang sama-sama dapat memenuhi keputusan.

Member Belanja ≥ 500rb
→ OR → → DAPAT DISKON
True False
Kondisi A Kondisi B A Or B
True True True
True False True
False True True
False False False

Pemrograman Visual • VB.NET

<!-- halaman 16 -->

**16**

## XOR: Tepat Satu Kondisi True
Berbeda dari OR: jika keduanya True, XOR menghasilkan False.

A B A Xor B
True True False
True False True
False True True
False False False

##### Ingat: XOR = 'salah satu, tetapi bukan keduanya'.
Pemrograman Visual • VB.NET

<!-- halaman 17 -->

**17**

## NOT: Membalik Nilai Logika
True menjadi False, dan False menjadi True.

isLogin
→ NOT → False
True
Ekspresi Not Ekspresi
True False
False True

Pemrograman Visual • VB.NET

<!-- halaman 18 -->

**18**

## AndAlso: AND dengan Short-Circuit
Kondisi kedua tidak dievaluasi jika kondisi pertama sudah False.

**Kondisi 1 Kondisi 2 → AndAlso → → False False Dilewati**

##### Mengapa berguna?
- Lebih efisien

- Dapat mencegah evaluasi yang tidak perlu

- Sering lebih aman pada kondisi bertingkat

Pemrograman Visual • VB.NET

<!-- halaman 19 -->

**19**

## OrElse: OR dengan Short-Circuit
Kondisi kedua tidak dievaluasi jika kondisi pertama sudah True.

Kondisi 1 Kondisi 2
→ OrElse → → True
True Dilewati

##### Prinsipnya: begitu hasil akhir sudah dapat dipastikan, evaluasi berhenti.
Pemrograman Visual • VB.NET

<!-- halaman 20 (OCR) -->

**20**

# Operator Assignment
Memberikan atau memperbarui nilai pada variabel.

total = 100000 total += 5000
Nilai 100000 disimpan Artinya:
ke variabel total. total = total + 5000

Pemrograman Visual • VB.NET

<!-- halaman 21 -->

**21**

## Operator Penggabungan String: &
Digunakan untuk menggabungkan teks.

"Selamat
"Selamat " → & → "Datang" → = →
Datang"
Contoh VB.NET
pesan = "Halo, " & nama

###### Untuk teks, gunakan & agar maksud penggabungan lebih jelas.
Pemrograman Visual • VB.NET

<!-- halaman 22 -->

**22**

## Mengapa & Lebih Aman untuk String?
Tanda + dapat membingungkan antara penjumlahan dan penggabungan.

**"22" & "33" "22" + "33" Hasil → "2233" Makna dapat bergantung pada tipe data/konversi.** Jelas: menggabungkan teks

Pemrograman Visual • VB.NET

<!-- halaman 23 -->

**23**

## Apa itu Ekspresi?
### Kombinasi operand dan operator yang menghasilkan sebuah nilai.

**subtotal + (subtotal * 0.11)**

(subtotal ×
subtotal → + → → = → total
0,11)

Ekspresi dapat sederhana atau terdiri dari beberapa operasi sekaligus.

Pemrograman Visual • VB.NET

<!-- halaman 24 -->

**24**

## Prioritas Operator
Urutan evaluasi memengaruhi hasil ekspresi.

10 + 2 × 5 (10 + 2) × 5
= 10 + 10 = 12 × 5
= 20 = 60

###### Gunakan tanda kurung jika ingin memperjelas urutan proses.
Pemrograman Visual • VB.NET

<!-- halaman 25 -->

**25**

## Urutan Prioritas yang Perlu Diingat
Dari yang dievaluasi lebih dahulu menuju yang lebih akhir.

**1 ( )** Tanda kurung **2 ^** Pangkat **3 * / \ Mod** Kali & bagi **4 + -** Tambah & kurang **5 Perbandingan** = <> > < >= <= **6 Not → And → Or** Logika

Pemrograman Visual • VB.NET

<!-- halaman 26 -->

**26**

## Studi Kasus: Diskon + PPN
Beberapa operator dapat bekerja dalam satu alur komputasi.

Setelah
Subtotal Diskon PPN Total
→ → diskon → →
200.000 10% 11% 199.800
180.000
Contoh VB.NET
diskon = subtotal * 0.10
total = (subtotal - diskon) * 1.11

###### Aritmatika membentuk nilai; perbandingan/logika menentukan kapan aturan diterapkan.
Pemrograman Visual • VB.NET

<!-- halaman 27 -->

**27**

## Pilih Operator yang Tepat
Fokus pada logika, bukan menghafal sintaks.

Menghitung subtotal harga × jumlah *
Mengecek nilai minimal 75 >=
And /
Dua syarat wajib terpenuhi
AndAlso
Salah satu dari dua syarat cukup Or / OrElse
Mengecek genap atau ganjil Mod
Menggabungkan nama depan & belakang &

Pemrograman Visual • VB.NET

<!-- halaman 28 -->

**28**

## Ringkasan
Operator adalah alat; ekspresi adalah cara kita menyusun logika komputasi.

Aritmatika Perbandingan Logika String
menggabungkan
menghitung menilai kondisi menggabungkan teks
kondisi
Pahami masalah → pilih operator → susun ekspresi → evaluasi hasil

Pemrograman Visual • VB.NET

<!-- halaman 29 -->

**29**

# <u>Tugas: Analisis Operator dan Ekspresi pada Aplikasi</u>
Sebuah aplikasi pemesanan makanan memiliki ketentuan berikut:

- Harga makanan adalah **Rp35.000/porsi** . Pengguna dapat memesan beberapa porsi. Jika membeli **minimal 5 porsi** , mendapat diskon **10%** . Jika pengguna merupakan **member DAN subtotal minimal Rp150.000** , mendapat tambahan diskon **5%** . Total diskon maksimal **15%** . Setelah diskon, dikenakan biaya layanan **5%** . Jika total setelah diskon masih **kurang dari Rp200.000** , dikenakan ongkir **Rp10.000** .

Mahasiswa diminta:

- Tentukan **input, proses, dan output** dari aplikasi tersebut.

- Identifikasi operator yang diperlukan (*, +, >=, <, And, dan sebagainya) dan **jelaskan fungsi masingmasing** .

- Buat ekspresi untuk menghitung: subtotal, diskon , totalSetelahDiskon, biayaLayanan, ongkir, dan totalBayar

- Tuliskan kondisi logika untuk menentukan:

   - ✓ diskon 10%;

   - ✓ tambahan diskon member 5%;

   - ✓ pemberian ongkir Rp10.000.

- Buat **diagram sederhana** :

**Input → Perhitungan → Pemeriksaan Kondisi → Output**

Ketentuan:

- Tugas diketik di word

- Dikumpulkan di kelas USU

- Paling lambat hari Jumat, tgl 18 September.

Pemrograman Visual • VB.NET
