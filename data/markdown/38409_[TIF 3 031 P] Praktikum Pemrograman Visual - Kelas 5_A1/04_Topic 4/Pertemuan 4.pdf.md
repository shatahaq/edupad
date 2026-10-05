---
course_id: "38409"
course: "[TIF 3 031 P] Praktikum Pemrograman Visual - Kelas 5/A1"
pertemuan: 4
section: "Topic 4"
section_index: 4
title: "Pertemuan 4"
type: "resource"
source_file: "38409_[TIF 3 031 P] Praktikum Pemrograman Visual - Kelas 5_A1/04_Topic 4/Pertemuan 4.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/642203/mod_resource/content/1/Pertemuan%204.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=213238"
converter: "pymupdf4llm+ocr(6 hal)"
---

<!-- halaman 1 (OCR) -->

#### <mark>ooo</mark>

## Struktur Perulangan
PEMROGRAMAN VISUAL

**Shata Diyaul Haq**

<!-- halaman 2 -->

## Pembahasan
Pengenalan Perulangan Jenis Perulangan

<!-- halaman 3 -->

## Perulangan (Looping)
**Perulangan adalah struktur kontrol yang menjalankan sebuah blok instruksi berulang kali selama kondisi tertentu terpenuhi (boolean true) atau sebanyak jumlah pengulangan yang ditetapkan. Tujuan utamanya adalah untuk mengautomasi tugas berulang, memproses koleksi data (array/list), dan mengurangi duplikasi kode.**

<!-- halaman 4 -->

**Fungsi dan Manfaat Mempermudah dan Mempercepat Pekerjaan Berulang Menghindari Penulisan Kode Manual Pengolahan Data dalam Jumlah Besar Meningkatkan Struktur dan Pemeliharaan Kode Fleksibilitas**

<!-- halaman 5 -->

## Tipe Perulangan
**Counted Loop**

**Jumlah pengulangan sudah diketahui atau terhitung, misalnya perulangan menggunakan For dimana ada batas mulai dan akhir tertentu.**

**Uncounted Loop**

**Jumlah pengulangan tidak diketahui, perulangan dilakukan selama kondisi tertentu bernilai benar, misalnya menggunakan While atau Do Loop yang bergantung pada kondisi yang diuji selama pemrosesan.**

<!-- halaman 6 -->

## For-Next
**For-Next digunakan untuk mengulang perintah dengan jumlah pengulangan yang sudah pasti atau telah ditentukan di awal. Ini memungkinkan pelaksanaan blok kode secara sistematis sebanyak jumlah iterasi yang diinginkan tanpa perlu menentukan kondisi secara eksplisit dalam blok perulangan.**

<!-- halaman 7 -->

## Penggunaan Variabel Pengontrol
**Variabel pengontrol adalah variabel yang mengatur jumlah pengulangan. Penentuan nilai awal, nilai akhir, dan langkah perulangan (step) harus sesuai kebutuhan, contohnya: Nilai awal 1 sampai 10 dengan step 1 untuk menaikkan nilai variabel setiap iterasi. Nilai awal 10 sampai 1 dengan step -1 untuk menurunkan nilai variabel setiap iterasi.**

<!-- halaman 8 (OCR) -->

### Do-Loop
**Do-Loop adalah jenis perulangan yang digunakan untuk kasus pengulangan dengan jumlah iterasi tidak diketahui sebelumnya. Perulangan terus berlanjut hingga kondisi berhenti terpenuhi.**

Mulai
VB
1 Do
Lakukan
2
perintah yang diulang perintah
3 misalnya menambah nilai
4 Loop While kondisi
5
Kondisi
True?
Hasil (contoh)
Blok perintah akan diulang
selama kondisi bernilai True. Tidak
Perulangan berhenti ketika 1
kondisi bernilai False. 2
Selesai
34
5

<!-- halaman 9 (OCR) -->

### While
##### Kondisi Dicek di Awal (While)
**Perulangan hanya dijalankan jika kondisi awal bernilai true. Jika kondisi awal false, perulangan tidak akan dijalankan sama sekali.**

Mulai
Sintaks While
Inisialisasi
VB variabel
Output (contoh)
1 1
Dim i As Integer = 1 Lakukan
Ya
2
2 While i <= 10
perintah
3 Kondisi
3 ListBox1.Items.Add(i)
4 Truue
4 i = i + 1
5
5 End While
Tidak
10
Blok perintah akan dijalankan
selama kondisi bernliai True. Selesai

<!-- halaman 10 (OCR) -->

### Do - While
##### Kondisi Dicek di Akhir (Do While)
**Perulangan dijalankan minimal satu kali, karena kondisi dicek setelah blok perintah dieksekusi.**

Mulai
Sintaks Do While
VB
Kondisi
True
1 Do While kondisi
2
perintah yang diulang
3 misalnya menambah nilai
Ya Tidak
4 update variabel
5 Loop Output (contoh)
1 Lakukan
2 perintah
Blok perintah akan dijalankan 3
selama kondisi bernilai True.
4
Kondisi diperiksa di awal.
5
Selesai

<!-- halaman 11 (OCR) -->

### Nested Loop
**Nested Loop adalah perulangan yang terdapat di dalam perulangan lainnya. Perulangan luar akan menjalankan perulangan dalam secara lengkap pada setiap iterasinya.**

Ulangi untuk setiap i
Perulangan Luar (i)
VB
i=1 i=2 i = 3
1 For i As Integer = 1 To 3 Perulangan Dalam (j) Perulangan Dalam (j) Perulangan Dalam (j)
2 For j As Integer = 1 To 3 j=1 j=1 j=1
3 ListBox1.Items.Add( j=2 j=2 j=2
4 i &" & j) j=3 j=3 j=3
5 Next
6 Next
Output (contoh)
1- 1
1 - 2
1 - 3
2 - 1
Perulangan dalam (inner loop)
2 - 2
akan dijalankan secara lengkap 2 - 3
3 - 1
untuk setiap iterasi perulangan
3 - 2
luar (outer loop).
3 - 3

<!-- halaman 12 (OCR) -->

#### <mark>ooo</mark>

# Let’s Try
