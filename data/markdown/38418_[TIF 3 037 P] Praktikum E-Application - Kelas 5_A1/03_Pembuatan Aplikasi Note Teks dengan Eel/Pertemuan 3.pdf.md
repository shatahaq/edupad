---
course_id: "38418"
course: "[TIF 3 037 P] Praktikum E-Application - Kelas 5/A1"
pertemuan: 3
section: "Pembuatan Aplikasi Note Teks dengan Eel"
section_index: 3
title: "pertemuan 3"
type: "resource"
source_file: "38418_[TIF 3 037 P] Praktikum E-Application - Kelas 5_A1/03_Pembuatan Aplikasi Note Teks dengan Eel/Pertemuan 3.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/636504/mod_resource/content/1/Pertemuan%203.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=208449"
converter: "pymupdf4llm+ocr(11 hal)"
---

<!-- halaman 1 (OCR) -->

Aslab Teknik **HOME** Informatika K **Pertemuan 3 Praktikum E-Application**

**Nadya Lahfah Dhea Tri Lova Simanjuntak**

**HOME**

ABOUT

MORE

<!-- halaman 2 -->

**HOME**

ABOUT

MORE

## Pembuatan Aplikasi Note Teks (.txt)

### penjelasan singkat :
Di pertemuan sebelumnya kita sudah belajar bagaimana JavaScript dan Python bisa saling berkomunikasi menggunakan Eel. Nah, sekarang kita akan memanfaatkan komunikasi tersebut untuk membuat aplikasi yang lebih nyata, yaitu aplikasi catatan atau Mini Notebook.

<!-- halaman 3 (OCR) -->

**HOME**

ABOUT

MORE

#### 1.Fitur Mini Notebook

**membaca Note**

**membuat Note menyimpan note**

**rename note**

**delete note**

<!-- halaman 4 (OCR) -->

Aslab Teknik
Informatika

Mulai Aplikasi
Tampilkan
Daftar Catatan
Pilih Catatan
SelesalTutup Aplikasi
Buat Baru
Buka Catatan &
Tampilkan Isi Input Judul & Selesai / Tutup Aplikasi
Isi Catatan
Aksi User
Simpan Hapus
Rename
Save Note Rename Note Delete Note
via main.py via main.py via main.py
Update Daftar Catatan

**HOME**

###### ABOUT

###### MORE

Diagram Alur Kerja Aplikasi

<!-- halaman 5 -->

**HOME**

ABOUT

MORE

## 2. Apa Itu @eel.expose?

@eel.expose adalah dekorator di Python yang digunakan untuk membuka (expose) sebuah fungsi Python agar bisa dipanggil dari JavaScript melalui Eel. fungsi Python hanya bisa dipanggil oleh Python sendiri. Dengan @eel.expose, fungsi tersebut menjadi seperti API internal yang dapat diakses langsung dari kode JavaScript/HTML

### Kenapa ini penting ?
@eel.expose adalah jembatan komunikasi Python ↔ JavaScript. Semua interaksi backend (Python) dengan frontend (HTML/JS) lewat Eel harus dimulai dengan fungsi yang di-expose Tanpa ini, JS tidak bisa tahu fungsi apa yang tersedia di Python

<!-- halaman 6 (OCR) -->

## Aslab Teknik KInformatika

**HOME**

ABOUT

###### MORE

#### JOMM PRAKTIK
<!-- halaman 7 -->

**HOME**

ABOUT

MORE

**Inisialisasi Front End dan Lokasi Penyimpanan**

Kode tersebut menyiapkan aplikasi Eel dan folder catatan. eel.init("web") menunjuk folder antarmuka web, sedangkan NOTES_DIR menentukan tempat penyimpanan catatan. Jika folder belum ada, otomatis dibuat dengan os.makedirs().

<!-- halaman 8 -->

**HOME**

ABOUT

#### MORE

**Mengambil data yang ada dalam folder dan menampilkannya didalam Aplikasi**

Fungsi get_notes() di-expose agar bisa dipanggil dari JavaScript. Fungsinya mengambil daftar file .txt dalam folder NOTES_DIR, lalu menghapus ekstensi .txt sehingga hanya nama catatan saja yang dikembalikan sebagai daftar.

<!-- halaman 9 -->

**HOME**

ABOUT

MORE

**Menampilkan semua Note yang ada, menampilkan judulnya saja**

untuk membaca isi catatan Fungsi read_note(title) digunakan berdasarkan judul. Pertama, dibuat path file dengan menambahkan txt pada judul. Jika file ada, isinya dibuka dan dibaca dengan encoding UTF8, lalu dikembalikan sebagai teks. Jika tidak ditemukan, fungsi mengembalikan string kosong.

<!-- halaman 10 (OCR) -->

Aslab Teknik Iroike

**HOME**

ABOUT

MORE

3. apa itu UTF-8

UTF-8 (Unicode Transformation Format - 8-bit) adalah standar pengodean karakter yang paling umum digunakan di web untuk menyimpan dan menukar teks secara digital.

<!-- halaman 11 -->

**HOME**

ABOUT

MORE

**Menyimpan dan memperbarui note yang diubah didalam**

Fungsi save_note(title, content) berfungsi menyimpan atau memperbarui catatan. File akan dibuat dengan nama sesuai judul dan berekstensi .txt, lalu isinya ditulis ulang menggunakan encoding UTF-8. Jika berhasil, fungsi mengembalikan True sebagai tanda penyimpanan sukses.

<!-- halaman 12 -->

**HOME**

ABOUT

#### MORE

**Menyimpan dan memperbarui note yang diubah didalam**

Fungsi rename_note(old_title, new_title) dipakai untuk mengganti nama catatan. Pertama dibuat path lama dan path baru dengan ekstensi .txt. Jika file lama ada, maka os.rename akan mengubahnya menjadi nama baru, lalu mengembalikan True. Jika file lama tidak ditemukan, fungsi mengembalikan False.

<!-- halaman 13 -->

**HOME**

ABOUT

MORE

### Menghapus dan melakukan Remove File
Fungsi delete_note(title) digunakan untuk menghapus catatan. Pertama dibuat path file berdasarkan judul dengan ekstensi .txt. Jika file tersebut ada, maka os.remove akan menghapusnya dan fungsi mengembalikan True. Jika tidak ditemukan, fungsi mengembalikan False.

<!-- halaman 14 -->

**HOME**

ABOUT

MORE

Kode eel.start(...) ini digunakan untuk menjalankan aplikasi Eel. File awal yang dibuka adalah index.html dengan ukuran jendela 800x600 piksel.  Parameter block=True menjaga program tetap berjalan sampai jendela ditutup. Untuk menambahkan logo atau ikon aplikasi, bisa dilakukan saat proses build menggunakan PyInstaller dengan menyertakan file icon.

<!-- halaman 15 (OCR) -->

## Aslab Teknik KInformatika

**HOME**

ABOUT

###### MORE

#### JOMM KUIS
<!-- halaman 16 -->

**HOME**

ABOUT

MORE

## QUIZ TIME 1
A. Python save_note() B. User mengetik catatan C. File .txt tersimpan

### Susun Alur Aplikasi
D. JavaScript saveNote() E. eel.save_note(title, content)

pertanyaan :

"Urutkan proses ketika user mengetik catatan lalu menekan tombol Save sampai menjadi file .txt."

<!-- halaman 17 -->

**HOME**

ABOUT

## QUIZ TIME 1
### Susun Alur Aplikasi
A. Python save_note() B. User mengetik catatan C. File .txt tersimpan D. JavaScript saveNote() E. eel.save_note(title, content)

**JAWABAN : B → D → E → A → C**

#### MORE

pertanyaan :

"Urutkan proses ketika user mengetik catatan lalu menekan tombol Save sampai menjadi file .txt."

<!-- halaman 18 (OCR) -->

## Aslab Teknik KInformatika

#### QUIZ TIME 2
**@eel.exposedef save_note(title, content):**

**HOME**

ABOUT

MORE

**.....**

pertanyaan : Fungsi ini berada di bagian mana?

A. HTML B. CSS

C. JavaScript

D. Python

<!-- halaman 19 (OCR) -->

## Aslab Teknik KInformatika

#### QUIZ TIME 2
**@eel.exposedef save_note(title, content):**

**HOME**

ABOUT

MORE

**.....**

pertanyaan : Fungsi ini berada di bagian mana?

A. HTML B. CSS

C. JavaScript

D. Python

**JAWABAN: D. PYTHON**

<!-- halaman 20 (OCR) -->

### Aslab Teknik KInrotika

#### QUIZ TIME 3
   - Python

##### Susun Alur
**HOME**

ABOUT

###### MORE

● JavaScript

● User

● Eel

File TXT

<!-- halaman 21 (OCR) -->

Aslab Teknik KInrotika

#### QUIZ TIME 3
Python

● JavaScript

● User ● Eel

File TXT

**Susun Alur**

**HOME**

ABOUT

MORE

**JAWABAN**

**USER ↓**

**JAVASCRIPT**

**↓ EEL ↓ PYTHON**

**↓ FILE TXT**

<!-- halaman 22 -->

**HOME**

MORE

ABOUT

## QUIZ TIME 4
Urutkan proses yang terjadi ketika pengguna mengetik teks di area editor sampai diagram batang berubah secara real-time!

A. JavaScript mengeksekusi updateChart() B. Nilai data diagram diperbarui dan chartInstance.update() dipanggil C. Event oninput terpicu pada elemen <textarea>

D. Pengguna mengetik atau menambahkan karakter di editor E. Panjang karakter (text.length) dan jumlah kata dihitung

<!-- halaman 23 -->

MORE

**HOME**

ABOUT

## QUIZ TIME 4
Urutkan proses yang terjadi ketika pengguna mengetik teks di area editor sampai diagram batang berubah secara real-time!

A. JavaScript mengeksekusi updateChart() B. Nilai data diagram diperbarui dan chartInstance.update() dipanggil C. Event oninput terpicu pada elemen <textarea> D. Pengguna mengetik atau menambahkan karakter di editor E. Panjang karakter (text.length) dan jumlah kata dihitung

**D → C → A → E → B**

**JAWABAN**

<!-- halaman 24 -->

**HOME**

ABOUT

#### MORE

## QUIZ TIME 5
Urutkan langkah-langkah kerja sistem dari saat pengguna memilih judul catatan di sidebar sampai isi catatan dan diagram statistik muncul di layar!

A. Backend Python membaca berkas dengan open() dan mengembalikan teks via file.read()

B. JavaScript menjalankan fungsi updateChart() untuk memperbarui grafik statistik teks C. Pengguna mengklik salah satu judul catatan di sidebar (onclick = buka(item)) D. Nilai judul dan isi catatan dimasukkan ke form input #judul dan #isi

E. JavaScript memanggil backend secara asinkron lewat await eel.baca_isi_catatan(judul)()

<!-- halaman 25 -->

**HOME**

ABOUT

MORE

## QUIZ TIME 5
Urutkan langkah-langkah kerja sistem dari saat pengguna memilih judul catatan di sidebar sampai isi catatan dan diagram statistik muncul di layar!

A. Backend Python membaca berkas dengan open() dan mengembalikan teks via file.read()

B. JavaScript menjalankan fungsi updateChart() untuk memperbarui grafik statistik teks C. Pengguna mengklik salah satu judul catatan di sidebar (onclick = buka(item)) D. Nilai judul dan isi catatan dimasukkan ke form input #judul dan #isi

E. JavaScript memanggil backend secara asinkron lewat await eel.baca_isi_catatan(judul)()

**C → E → A → D → B**

**JAWABAN**

<!-- halaman 26 -->

**HOME**

ABOUT

#### MORE

## QUIZ TIME 6
Urutkan proses penghapusan catatan dari sisi pengguna hingga berkas fisik hilang dan daftar antarmuka diperbarui!

A. JavaScript memanggil loadList() untuk me-refresh daftar catatan di sidebar B. Tombol hapus (btn-delete) pada baris catatan diklik oleh pengguna

C. JavaScript memicu fungsi Python dengan await eel.hapus_catatan(item)() D. Konfirmasi penghapusan disetujui (confirm())

E. Backend Python mengeksekusi os.remove(path) pada folder notes/

<!-- halaman 27 -->

**HOME**

ABOUT

MORE

## QUIZ TIME 6
Urutkan proses penghapusan catatan dari sisi pengguna hingga berkas fisik hilang dan daftar antarmuka diperbarui!

A. JavaScript memanggil loadList() untuk me-refresh daftar catatan di sidebar B. Tombol hapus (btn-delete) pada baris catatan diklik oleh pengguna

C. JavaScript memicu fungsi Python dengan await eel.hapus_catatan(item)() D. Konfirmasi penghapusan disetujui (confirm())

E. Backend Python mengeksekusi os.remove(path) pada folder notes/

**JAWABAN**

**B → D → C → E → A**

<!-- halaman 28 (OCR) -->

# K IlnrotikaAslab Teknik

Thank You!

**HOME**

ABOUT

MORE
