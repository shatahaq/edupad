---
course_id: "38408"
course: "[TIF 3 031] Pemrograman Visual - Kelas 5/B"
pertemuan: 5
section: "Pertemuan 5-Percabangan If-Else"
section_index: 5
title: "Percabangan If-Else"
type: "resource"
source_file: "38408_[TIF 3 031] Pemrograman Visual - Kelas 5_B/05_Pertemuan 5-Percabangan If-Else/Pertemuan_5_Struktur_Percabangan_If_Else_Pemrograman_Vis.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/638375/mod_resource/content/1/Pertemuan_5_Struktur_Percabangan_If_Else_Pemrograman_Visual.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=210017"
converter: "pymupdf4llm+ocr(8 hal)"
---

<!-- halaman 1 (OCR) -->

## PEMROGRAMAN VISUAL
Pertemuan 5

**Struktur Percabangan If–Else**

Membuat aplikasi visual yang dapat mengambil keputusan berdasarkan kondisi

**Insidini Fawwaz, M.Kom**

<!-- halaman 2 -->

**KONSEP**

# Mengapa Program Membutuhkan Percabangan?
**Tanpa percabangan** Program selalu menjalankan instruksi yang sama, apa pun kondisi inputnya.

**Dengan percabangan Contoh** Program memeriksa Jika nilai ≥ 60 → Lulus. kondisi terlebih dahulu, Jika tidak → Tidak Lulus. lalu memilih tindakan yang sesuai.

3

<!-- halaman 3 -->

**KONSEP**

# Analogi Percabangan dalam Kehidupan
Percabangan = memilih tindakan berdasarkan suatu kondisi.

Lihat kondisi cuaca

Apakah hujan? Ya → bawa payung Tidak → tanpa payung

**Inti konsep**

Program juga melakukan hal yang sama: mengevaluasi kondisi yang bernilai True atau False, kemudian menentukan blok kode yang dijalankan.

4

<!-- halaman 4 -->

**KONSEP**

# Konsep Dasar If–Else
- Program akan **mengecek suatu kondisi terlebih dahulu** .

- Hasil kondisi tersebut hanya ada dua: True (benar) atau False (salah).

**IF** Memeriksa kondisi. `If nilai >= 75 Then` **ELSE** `MessageBox.Show("Lulus") Else` Alternatif ketika kondisi tidak terpenuhi. `MessageBox.Show("Tidak Lulus") End If` **END IF** Menandai akhir struktur percabangan.

5

<!-- halaman 5 -->

**SINTAKS**

# Bentuk 1 — If...Then
Dipakai jika kita **hanya ingin melakukan sesuatu ketika kondisi benar** . Kalau kondisi salah, tidak melakukan apa-apa.

```
If kondisiThen
perintah
End If
```

**Kapan digunakan?** Ketika program tidak perlu melakukan tindakan khusus saat kondisi bernilai False.

```
Contoh:
```

```
If umur>= 17 Then
lblStatus.Text= "Bolehmembuat
SIM"
End If
```

6

<!-- halaman 6 -->

**CONTOH**

# Contoh If...Then pada Form
Klik tombol untuk memeriksa jumlah pembelian.

**Komponen Form** TextBox: txtJumlah Button: btnCek Label: lblInfo

```
Private Sub btnCek_Click(...) Handles
btnCek.Click
Dim jumlahAs Integer =
CInt(txtJumlah.Text)
If jumlah>= 5 Then
lblInfo.Text= "Dapatdiskon10%"
End If
End Sub
```

- **Yang membedakannya dengan If...Else** . Karena kode ini **tidak memiliki Else** , ketika syarat tidak terpenuhi program tidak memberikan aksi alternatif.

- Dim jumlah As Integer → deklarasi variabel jumlah bertipe Integer.

- txtJumlah.Text → mengambil nilai yang dimasukkan pengguna dari TextBox.

- CInt(...) → mengubah input tersebut menjadi Integer.

7

<!-- halaman 7 -->

**SINTAKS**

# Bentuk 2 — If...Then...Else
Digunakan ketika ada dua kemungkinan hasil.

## 1. If kondisi Then
```
If kondisiThen
perintahJikaBenar
Else
```

```
perintahJikaSalah
End If
```

Program **memeriksa suatu kondisi** . Kondisi tersebut akan menghasilkan True atau False.

## 2. perintahJikaBenar
Jika kondisi **True (benar)** , bagian ini yang dijalankan.

## 3. Else
Artinya **“jika tidak”** . Jadi Else **tidak memiliki kondisi baru** . Ia dijalankan jika kondisi pada If tadi bernilai False. **4. perintahJikaSalah**

Dijalankan ketika kondisi pada If **False (salah)** . **5. End If**

Menandai bahwa percabangan selesai.

8

<!-- halaman 8 -->

# Contoh lain— If...Then...Else
- Digunakan ketika ada dua kemungkinan hasil.

- Satu kondisi, dua kemungkinan output.

```
Dim nilaiAs Integer =
CInt(txtNilai.Text)
If nilai>= 60 Then
lblHasil.Text= "Lulus"
Else
lblHasil.Text= "Tidak Lulus"
End If
```

**Input** nilai

**Kondisi** nilai >= 60

**Output** Lulus / Tidak Lulus

9

<!-- halaman 9 (OCR) -->

**FLOWCHART**

## Alur — If...Then...Else
Mulai
True False
nilai >= 60 ?
Lulus Tidak Lulus
Selesai

10

<!-- halaman 10 (OCR) -->

**OPERATOR**

## Operator Perbandingan dalam Kondisi
= <> >
sama dengan tidak sama dengan lebih besar
< >= <=
lebih kecil lebih besar atau sama lebih kecil atau sama

11

<!-- halaman 11 -->

**OPERATOR**

# Operator Logika
## Digunakan ketika keputusan melibatkan lebih dari satu kondisi.

**And**

**Or**

**Not**

True hanya jika SEMUA kondisi True jika SALAH SATU kondisi True. Membalik nilai kondisi. True. **True → False** hari = "Sabtu" Or hari = "Minggu" **False → True** member = True And subtotal >= 150000 Jadi kalau hari **Sabtu → True** . stokHabis = False Kalau hari **Minggu → True** . Artinya stok **tidak habis** . **AND = semuanya harus** Kalau hari **Senin → False** . **terpenuhi.**

12

<!-- halaman 12 -->

**CONTOH**

# Contoh Kondisi dengan And
Dua syarat harus terpenuhi secara bersamaan.

```
If isMember= True And subtotal >=
150000D Then
diskonMember= subtotal * 0.05D
End If
```

**Syarat 1** Pengguna adalah member. **Syarat 2** Subtotal minimal Rp150.000.

**Hasil** Tambahan diskon 5%.

13

<!-- halaman 13 -->

**SINTAKS**

# Bentuk 3 — If...ElseIf...Else
Digunakan ketika pilihan hasil lebih dari dua.

**Prinsip**

```
If kondisi1 Then
perintah1
ElseIfkondisi2 Then
perintah2
ElseIfkondisi3 Then
perintah3
Else
perintahLain
End If
```

Kondisi diperiksa dari atas ke bawah. Ketika satu kondisi True, cabang berikutnya tidak diperiksa lagi.

14

<!-- halaman 14 -->

**CONTOH**

# Contoh: Kategori Nilai
```
If nilai>= 85 Then
grade = "A"
ElseIfnilai>= 75 Then
grade = "B"
ElseIfnilai>= 65 Then
grade = "C"
ElseIfnilai>= 50 Then
grade = "D"
Else
grade = "E"
End If
```

ElseIf artinya **“jika kondisi sebelumnya tidak terpenuhi, periksa kondisi berikutnya.”**

15

<!-- halaman 15 -->

**PENTING**

# Urutan Kondisi: Benar vs Salah
ElseIf berhenti pada kondisi pertama yang bernilai True.

**Benar Bermasalah** If nilai >= 85 Then If nilai >= 65 Then A C ElseIf nilai >= 75 Then ElseIf nilai >= 75 Then B B ElseIf nilai >= 65 Then ElseIf nilai >= 85 Then C A

16

<!-- halaman 16 -->

**KONSEP**

# Nested If — Percabangan Bersarang
If dapat ditempatkan di dalam If lain atau percabangan bertingkat.

```
If nilai >= 60 Then
    If kehadiran >= 75 Then
        lblHasil.Text = "Lulus"
    Else
        lblHasil.Text = "Tidak Lulus karena
kehadiran"
    End If
Else
```

```
    lblHasil.Text = "Tidak Lulus karena
nilai"
End If
```

**Gunakan seperlunya** Nested If cocok untuk keputusan bertingkat, tetapi terlalu banyak tingkat akan membuat kode sulit dibaca.

17

<!-- halaman 17 -->

**VISUAL BASIC**

# If–Else di Dalam Event
Pada aplikasi visual, percabangan biasanya dijalankan ketika event terjadi.

User isi input Klik Button

Label menampilkan
Button_Click If–Else
hasil

Pola umum

Input dari kontrol → konversi tipe data → evaluasi kondisi → proses → tampilkan output.

18

<!-- halaman 18 -->

**PRAKTIK**

# Contoh Form: Cek Bilangan
Kasus sederhana untuk memahami hubungan kontrol dan kode.

**Desain Form** Label: Masukkan angka TextBox: txtAngka `Dim angka As Integer = CInt(txtAngka.Text)` Button: btnCek Label hasil: lblHasil `If angka Mod 2 = 0 Then lblHasil.Text = "Bilangan Genap" Else lblHasil.Text = "Bilangan Ganjil" End If`

Misal:

- 8 Mod 2 = 0

- 7 Mod 2 = 1

19

<!-- halaman 19 -->

**PRAKTIK BAIK**

# Validasi Input Sebelum Percabangan
• TryParse artinya mencoba mengubah input. Kalau berhasil menghasilkan True dan nilainya disimpan; kalau gagal menghasilkan False tanpa membuat program langsung error.

• Input pengguna tidak selalu sesuai yang kita harapkan.

**Mengapa TryParse?**

Mencegah aplikasi error ketika pengguna mengetik huruf, simbol, atau mengosongkan input.

```
Dim nilaiAs Integer
```

```
If Integer.TryParse(txtNilai.Text, nilai)
Then
```

```
lblHasil.Text= "Input valid"
Else
```

```
lblHasil.Text= "Masukkan angkayang
benar"
End If
```

21

<!-- halaman 20 (OCR) -->

#### Ilustrasi Validasi Input dengan TryParse

Contoh 1: Input valid
Kode Program (VB) Pengguna memasukkan angka (misal 80)
Dimnilai As Integer Masukkan nilai:
80 Cek
If Integer.TryParse(txtNilai.Text, nilai) Then
1blHasil.Text = "Input valid"
Else
Integer.TryParse("80", nilai)
lblHasil.Text = "Masukkan angka yang benar"
t ut
Berhasil
(True)
Tampilan Form Variabel nilai berisi 80
IblHasil.Text = "Input valid"
Masukkan nilai:
80 Cek
Hasil di Form
Hasil:
Hasil:
Input valid
Input valid

Contoh 2: Input tidak valid
Pengguna memasukkan huruf (misal abc)
Masukkan nilai:
abc Cek
Integer.TryParse("abc", nilai)
Gagal
(False)
Variabel nilai tidak berubah
IblHasil.Text = "Masukkan angka
yang benar"
Hasil di Form
Hasil:
Masukkan angka yang benar

Kesimpulan: • TryParse mencoba mengubah input menjadi Integer. • Jika berhasil → True dan nilai disimpan ke variabel. i ad e s   roa e iead eas sa ← Jeaa a •

<!-- halaman 21 (OCR) -->

### Perbedaan Deklarasi, Clnt, dan TryParse

###### Deklarasi Variabel

Menyiapkan tempat penyimpanan.

###### Dim nilai As Integer

Membuat variabel bernama nilai dengan tipe data Integer. Belum ada nilai yang disimpan. Inisialisasi Variabel 2 Memberi nilai awal. Dim nilai As Integer = 80 Membuat variabel nilai bertipe Integer dan langsung memberi nilai 80. Nilai bisa diganti nanti sesuai kebutuhan.

- Inti Perbedaan

- Deklarasi = menyiapkan tempat penyimpanan (membuat variabel). Inisialisasi = memberi nilai awal. CInt = mengubah input menjadi tipe tertentu, tetapi tidak aman jika input salah. TryParse = mencoba mengubah input dan mengecek apakah berhasil. Jika gagal, hasilnya False sehingga kita bisa menangani kesalahan.

Menggunakan Clnt Menggunakan TryParse
Mengubah input menjadi Integer Mencoba mengubah input dan mengecek
(tetapi tidak aman jika input salah). apakah berhasil.
Dim nilai As Integer
Dim nilai As Integer = CInt(txtNilai.Text) If Integer.TryParse(txtNilai.Text, nilai) Then
lblHasil.Text = "Input valid"
Else
Contoh Input Valid Contoh Input Tidak Valid lblHasil.Text = "Masukkan angka yang benar"
End If
Pengguna memasukkan angka. Pengguna memasukkan huruf.
Masukkan nilai: Masukkan nilai:
Contoh Input Valid Contoh Input Tidak Valid
123 Proses abc Proses
Pengguna memasukkan angka. Pengguna memasukkan huruf.
Masukkan nilai: Masukkan nilai:
123 Proses abc Proses
CInt("123") CInt("abc")
Berhasil diubah Terjadi error
menjadi Integer. (FormatException). Integer.TryParse("123", nilai) Integer.TryParse("abc", nilai)
Hasil: True Hasil: False
nilai = 123 nilai tidak berubah
nilai = 123 Program berhenti
dan menampilkan
Program berjalan normal. Program berjalan normal Masuk ke blok Else
pesan error.
dan bisa melanjutkan proses Menampilkan pesan:
menggunakan nilai. "Masukkan angka yang benar".
CInt tidak mengecek input terlebih dahulu.
Jika input tidak sesuai, program bisa mengalami error TryParse lebih aman karena tidak menimbulkan error.
(FormatException) dan berhenti. Program tetap berjalan dan kita bisa menangani input yang salah.

<!-- halaman 22 -->

**STUDI KASUS**

# Kasus: Diskon Pemesanan Makanan
Menerapkan operator dan percabangan pada kasus yang lebih realistis.

Harga makanan = Rp35.000/porsi. Minimal 5 porsi → diskon 10%. Member DAN subtotal ≥ Rp150.000 → tambahan diskon 5%. Total diskon maksimal 15%. Setelah diskon dikenakan biaya layanan 5%. Jika total setelah diskon < Rp200.000 → ongkir Rp10.000.

22

<!-- halaman 23 -->

**STUDI KASUS**

# Kasus Diskon — Input, Proses, Output
Pisahkan kebutuhan program sebelum menulis kode.

INPUT PROSES OUTPUT
jumlahPorsi subtotal subtotal
isMember diskon diskon
totalSetelahDiskon
totalBayar
biayaLayanan
ongkir

23

<!-- halaman 24 (OCR) -->

# Kasus Diskon — Percabangan 10%

###### Kode Program (VB)

Dim diskonPersen As Decimal = 0D

- If jumlahPorsi >= 5Then diskonPersen = diskonPersen +0.1D

- End If

##### Penjelasan Singkat

diskonPersen dibuat dengan nilai awal 0 (belum ada diskon).

2 Cek apakah jumlahPorsi ≥ 5.

3 Jika True, diskon ditambah 0.1 (10%).
4 Jika False, blok If dilewati dan
diskon tetap 0%.

Contoh 1: jumlahPorsi ≥ 5
Mendapat diskon 10%

Contoh 2: jumlahPorsi < 5
Tidak mendapat diskon

Input jumlah porsi:
jumlahPorsi Hasil
6
>= 5 ?
diskonPersen = 0.1
True
Diskon 10%
diskonPersen = diskonPersen + 0.1D
(0 + 0.1 = 0.1)

Input jumlah porsi:
jumlahPorsi Hasil
3
>= 5 ?
diskonPersen = 0
False
Diskon 0%
Blok If dilewati
(tidak ada penambahan diskon)

Kesimpulan

Kalau beli minimal 5 porsi, dapat diskon 10%. Kalau kurang dari 5, tidak ada diskon.

<!-- halaman 25 -->

**STUDI KASUS**

# Kasus Diskon — Percabangan 10%
Kondisi pertama bergantung pada jumlah porsi.

**Makna**

```
Dim diskonPersenAs Decimal = 0D
```

```
If jumlahPorsi>= 5 Then
diskonPersen= diskonPersen+
0.1D
End If
```

Jika jumlah porsi minimal 5, persentase diskon bertambah 10%. Jika tidak, nilainya tetap 0.

24

<!-- halaman 26 -->

**STUDI KASUS**

# Kasus Diskon — Tambahan Member 5%
Gunakan And karena kedua syarat harus benar.

### Contoh
```
If isMemberAnd subtotal >= 150000D
Then
```

```
diskonPersen= diskonPersen+
0.05D
End If
```

Member + subtotal Rp175.000 → dapat tambahan 5%.

Bukan member + subtotal Rp175.000 → tidak dapat tambahan 5%.

25

<!-- halaman 27 -->

**STUDI KASUS**

# Kasus Diskon — Membatasi Maksimal 15%
Percabangan juga dapat digunakan untuk menetapkan batas.

**Tujuan**

```
If diskonPersen> 0.15D Then
diskonPersen= 0.15D
End If
```

Apa pun kombinasi aturan diskon, program memastikan total persentase diskon tidak melebihi 15%.

26

<!-- halaman 28 -->

**STUDI KASUS**

# Kasus Diskon — Menentukan Ongkir
Ongkir hanya muncul jika total setelah diskon masih di bawah Rp200.000.

```
If totalSetelahDiskon< 200000D
Then
ongkir= 10000D
Else
ongkir= 0D
End If
```

**Dua hasil** True → ongkir Rp10.000 False → ongkir Rp0

27

<!-- halaman 29 (OCR) -->

###### Studi Kasus: Diskon Pemesanan Makanan

###### Ketentuan

###### Contoh Tampilan Form (GUI)

Harga makanan = Rp35.000/porsi. Minimal 5 porsi → diskon 10%. Member DAN subtotal ≥ Rp150.000 → tambahan diskon 5%. Total diskon maksimal 15%. Setelah diskon dikenakan biaya layanan 5%. Jika total setelah diskon < Rp200.000 → ongkir Rp10.000.

###### Kode Program (VB.NET)

Private Sub btnHitung_Click(sender As Object, e As EventArgs)

Handles btnHitung.Click

Hitung total setelah diskon totalSetelahDiskon = subtotal (subtotal * diskonPersen)

'Deklarasi variabel Dim jumlahPorsi As Integer Dim harga As Decimal = 35000D Dim diskonPersen As Decimal = 0D Dim subtotal As Decimal Dim totalSetelahDiskon As Decimal

Biaya layanan 5%

biayaLayanan = totalSetelahDiskon * 0.05D

Dim biayaLayanan As Decimal Dim ongkir As Decimal = 0D Dim totalBayar As Decimal

- 'Ongkir Rp10.000 jika total setelah diskon < 200.000

If totalSetelahDiskon < 200000D Then ongkir = 10000D End If

Validasi input

If Not Integer.TryParse(txtJumlah.Text, jumlahPorsi) Then MessageBox.Show("Masukkan jumlah porsi yang benar.") Exit Sub End If

'Total pembayaran totalBayar = totalSetelahDiskon + biayaLayanan + ongkir

'Hitung subtotal subtotal = jumlahPorsi * harga

   - 'Tampilkan hasil lblSubtotal.Text = "Subtotal: Rp" & subtotal.ToString("N0")

   - lblDiskon.Text = "Diskon: " &

- 'Diskon 10% jika minimal 5 porsi If jumlahPorsi >= 5 Then

(diskonPersen *100).ToString("0") & "%" lblSetelahDiskon.Text = "Total Setelah Diskon: Rp"& totalSetelahDiskon.ToString("Ne")

diskonPersen = diskonPersen + 0.1D End If

1blLayanan.Text = "Biaya Layanan (5%): Rp" & biayaLayanan.ToString("Ne") lbl0ngkir.Text = "Ongkir: Rp" & ongkir.ToString("Ne")

'Tambahan diskon 5% jika member DAN subtotal >= 150.000 If chkMember.Checked And subtotal >= 150000D Then diskonPersen = diskonPersen + 0.05D End If

- 1blTotal.Text = "Total Bayar: Rp" & totalBayar.ToString("Ne")

'Batas maksimal diskon 15% If diskonPersen > 0.15D Then diskonPersen = 0.15D

End Sub

End If

Pemesanan Makanan □ ×

Jumlah Porsi: Hasil Perhitungan 5 Subtotal : Rp175.000 Diskon : 15% (Rp26.250) Member Total Setelah Diskon : Rp148.750 Biaya Layanan (5%) : Rp7.438 Hitung Ongkir : Rp10.000 Total Bayar : Rp166.188

Contoh Perhitungan (5 porsi, member) Subtotal 5 × Rp35.000 = Rp175.000 Diskon

- Minimal 5 porsi → 10% Member DAN subtotal ≥ Rp150.000 → 5% Total diskon = 10% + 5% = 15% (maksimal 15%) Nilai diskon = 15% × Rp175.000 = Rp26.250

3 Total setelah diskon Rp175.000 - Rp26.250 = Rp148.750

- 4 Biaya layanan 5% 5% × Rp148.750 = Rp7.437,50 (≈ Rp7.438)

5 Ongkir Rp148.750 < Rp200.000 → ongkir = Rp10.000 Total bayar Rp148.750 + Rp7.438 + Rp10.000 = Rp166.188

###### Kesimpulan

Program menggunakan operator aritmatika, perbandingan, dan logika (And). Diskon dihitung bertahap dan dibatasi maksimal 15%. Biaya layanan dikenakan setelah diskon. Ongkir hanya ditambahkan jika total setelah diskon < Rp200.000.

<!-- halaman 30 (OCR) -->

**LATIHAN**

## Simulasi Kasus 1
Pesanan 4 porsi, bukan member.

**4 × 35.000**

**Subtotal 140.000**

Diskon 0%

Ongkir 10.000 Total + layanan

**Diskusikan** Berapa biaya layanan 5% dan total bayar akhirnya?

29

<!-- halaman 31 -->

**LATIHAN**

# Simulasi Kasus 2
Pesanan 5 porsi dan member.

**5 × 35.000**

**Subtotal 175.000**

Setelah diskon
Diskon 15% Ongkir 10.000
148.750

**Pertanyaan** Mengapa diskon menjadi 15%? Berapa biaya layanan dan total bayar?

30

<!-- halaman 32 -->

**LATIHAN**

# Mini Challenge — Aplikasi Tarif Parkir
Rancang logika sebelum menulis kode. Input: lama parkir (jam). 1–2 jam → Rp5.000. 3–5 jam → Rp10.000. > 5 jam → Rp15.000. Jika member, potongan Rp2.000. Tampilkan tarif akhir pada Label.

**Pertanyaan pemantik** Percabangan apa yang paling cocok? Di mana operator And diperlukan? Bagaimana memastikan lama parkir tidak negatif?

37

<!-- halaman 33 -->

**PENUTUP**

# Praktik Mandiri
Bangun satu aplikasi sederhana menggunakan percabangan.

**Pilihan kasus**

1. Tarif laundry 2. Belanja Toko

3. Penyewaan Mobil 4. Pemesanan Tiket Bioskop 5. Tarif Hotel

**Wajib ada**

Minimal 2 input Minimal 1 Button If/ElseIf/Else Validasi input Output pada Label atau MessageBox

40
