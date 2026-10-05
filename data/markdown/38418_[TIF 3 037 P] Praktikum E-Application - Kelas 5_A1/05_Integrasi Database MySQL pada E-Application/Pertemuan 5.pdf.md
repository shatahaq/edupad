---
course_id: "38418"
course: "[TIF 3 037 P] Praktikum E-Application - Kelas 5/A1"
pertemuan: 5
section: "Integrasi Database MySQL pada E-Application"
section_index: 5
title: "pertemuan 5"
type: "resource"
source_file: "38418_[TIF 3 037 P] Praktikum E-Application - Kelas 5_A1/05_Integrasi Database MySQL pada E-Application/Pertemuan 5.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/636508/mod_resource/content/1/Pertemuan%205.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=208453"
converter: "pymupdf4llm+ocr(5 hal)"
---

<!-- halaman 1 (OCR) -->

Aslab Teknik **HOME** Informatika K **Pertemuan 5 Praktikum E-Application**

**Nadya Lahfah Dhea Tri Lova Simanjuntak**

**HOME**

ABOUT

MORE

<!-- halaman 2 (OCR) -->

**HOME**

MORE

# VIrorikadAslab Teknik

ABOUT

#### mysql-connector-python
<!-- halaman 3 -->

**HOME** ABOUT

MORE

### penjelasan singkat :
Dalam Python, kita membutuhkan sebuah penghubung agar program bisa berbicara dengan database MySQL. Penghubung itu disebut MySQL Connector. Fungsinya mirip seperti kabel yang menghubungkan komputer ke server database. tanpa kabel, data tidak bisa mengalir. Dengan connector, Python dapat melakukan koneksi, mengirim query SQL, dan mengambil hasil query dari MySQL.

Di pertemuan sebelumnya kita menyimpan data menggunakan file .txt. Sekarang penyimpanan datanya kita pindahkan ke database MySQL supaya pengelolaan data lebih terstruktur

<!-- halaman 4 -->

**HOME**

ABOUT

MORE

#### Apa Itu MySQL Connector?
MySQL Connector adalah library yang digunakan agar program Python dapat berkomunikasi dengan database MySQL. Dengan connector, Python dapat:

Terhubung ke MySQL Mengirim query SQL Mengambil hasil query Menambah data Mengubah data Menghapus data

<!-- halaman 5 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT

MORE

### Instalasi MySQL Connector pip install mysql-connector-python
C:\Users\HP>pip install mysql-connector-python Collecting mysql-connector-python Downloading mysql_connector_python-26.7.0-cp313-cp313-win_amd64.whl.metadata (11 kB) Downloading mysql_connector_python-26.7.0-cp313-cp313-win_amd64.whl (17.7 MB) 17.7/17.7 MB 981.5 kB/s0:00:18 Installing collected packages: mysql-connector-python Successfully installed mysql-connector-python-26.7.0

Kemudian: **pip show mysql-connector-python**

<!-- halaman 6 -->

**HOME**

ABOUT

MORE

**KONEKSI PYTHON DAN MYSQL** Untuk menghubungkan Python dengan MySQL, kita membutuhkan beberapa informasi:

|**Parameter**|**Fungsi**|
|---|---|
|host|Alamat server MySQL|
|user|Username MySQL|
|password|Password MySQL|
|database|Database yang digunakan|

<!-- halaman 7 (OCR) -->

Aslab Teknik Informatika

MORE

**HOME**

ABOUT

**Apa Itu Cursor?** Cursor digunakan untuk menjalankan perintah SQL dari Python

cursor= db .cursor

Kemudian query dapat dijalankan menggunakan:

cursor.execute("SELECT* FROM users

<!-- halaman 8 -->

MORE

HOME

###### ABOUT

#### CRUD
##### Database biasanya memiliki empat operasi utama yang dikenal sebagai CRUD:

|**Operasi**|**SQL**|**Fungsi**|
|---|---|---|
|Create|INSERT|Menambah data|
|Read|SELECT|Membaca data|
|Update|UPDATE|Mengubah data|
|Delete|DELETE|Menghapus data|

<!-- halaman 9 (OCR) -->

## K IlnrotikaAslab Teknik

Thank You!

**HOME**

ABOUT

MORE
