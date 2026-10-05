---
course_id: "38429"
course: "[TIF 3 029] Sistem Pendukung Keputusan - Kelas 5/A"
pertemuan: 1
section: "Pengantar SPK"
section_index: 1
title: "Pengantar SPK"
type: "resource"
source_file: "38429_[TIF 3 029] Sistem Pendukung Keputusan - Kelas 5_A/01_Pengantar SPK/1-2 Pengantar SPK.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/620845/mod_resource/content/2/1-2%20Pengantar%20SPK.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=198302"
converter: "pymupdf4llm+ocr(2 hal)"
---

<!-- halaman 1 (OCR) -->

Universitas Transformation Kampus Sumatera Utara Towards the Ultimate Merdeka INDONES

 PENGANTAR SPK Kuliah ke-1&2 Teknik Informatika – Program D3

Dr. Esther Nababan, M.Sc.

<!-- halaman 2 -->

# PENDAHULUAN

- Pengambil keputusan dihadapkan dengan lingkungan yang semakin penuh tekanan – sangat kompetitif, serba cepat, mendekati waktu nyata, dipenuhi dengan informasi, data didistribusikan ke seluruh perusahaan, dan dalam lingkup multinasional.

- Kombinasi kecepatan dan akses Internet yang memungkinkan, dan pematangan teknik kecerdasan buatan, telah menghasilkan bantuan canggih untuk mendukung pengambilan keputusan di bawah kondisi yang berisiko dan tidak pasti ini.

- Bantuan ini memiliki potensi untuk meningkatkan pengambilan keputusan dengan menyarankan solusi yang lebih baik daripada yang dibuat oleh manusia saja.

- Semakin tersedia berbagai bidang ilmu dan kepakaran mulai dari diagnosis medis hingga monitor dan kendali lalu lintas hingga aplikasi teknik.

<!-- halaman 3 -->

# Decision Support System

- Decision Support System (DSS) adalah sistem atau subsistem berbasis komputer interaktif yang dimaksudkan untuk membantu pengambil keputusan menggunakan teknologi komunikasi, data, dokumen, pengetahuan dan/atau model untuk mengidentifikasi dan memecahkan masalah, menyelesaikan tugas proses keputusan, dan membuat keputusan.

- Sistem Pendukung Keputusan adalah istilah umum untuk setiap aplikasi komputer yang meningkatkan kemampuan seseorang atau kelompok untuk membuat keputusan.

- Juga, Sistem Pendukung Keputusan mengacu pada bidang penelitian akademis yang melibatkan merancang dan mempelajari Sistem Pendukung Keputusan dalam konteks penggunaannya.

<!-- halaman 4 -->

# Tujuan

- Untuk mengenal dan terbiasa dengan tujuan dan berbagai bentuk pendukung keputusan,

- Mendapatkan pengetahuan tentang isu-isu praktis implementasi.

- Kuliah ini membahas sistem berdasarkan pendekatan statistik dan logis untuk pengambilan keputusan yang mencakup prediksi statistik, sistem berbasis aturan, penalaran berbasis kasus, jaringan saraf, logika fuzzy, dll.

- Memberikan gambaran tentang berbagai teknik pendukung keputusan terkomputerisasi bersama dengan penilaian rinci dari aplikasi yang berhasil dan tidak berhasil dikembangkan.

- Dampak aktual dan potensial dari teknologi bersama dengan tantangan yang terkait dengan aplikasi semacam ini akan diperiksa.

<!-- halaman 5 -->

Aturan untuk nilai akhir mhs : Nilai akan didasarkan pada:

- ujian akhir

- ulasan makalah

- Baca makalah dari literatur

- Menulis laporan di atas kertas

- Berikan presentasi lisan

- TugaS kelompok,

- Kelompok kecil

- Rancang dan implementasikan DSS untuk masalah pilihan Anda

- Laporan tertulis

- Presentasi lisan

<!-- halaman 6 -->

# BUKU RUJUKAN

- _Hand Book On Decision Support Systems_ , F. Burstein, Springer, 2008

- _Decision Support Systems and Intelligent Systems_ , Ephraim Turban and Jay Aronson, Prentice-Hall, 2001.

- _Making Hard Decisions Second Edition_ , Robert Clemen, Duxbury, 1996

- • _M. Seref, R. Ahuja, and W. Winston, Developing Spreadsheet-based Decision Support Systems, Dynamic Ideas (2007)._

   - Part I reviews Excel.

   - Part II supports the course.

   - Part III contains some advanced material and a set of case exercises.

<!-- halaman 7 -->

# Sistem pendukung keputusan berbasis spreadsheet

- DSS terdiri dari model, sumber data, dan antarmuka pengguna.

- Ketika model diimplementasikan di Excel, dimungkinkan untuk menggunakan Visual Basic for Applications (VBA) untuk membuat sistem lebih efisien dengan mengotomatiskan tugas-tugas interaktif yang seharusnya diulang secara rutin oleh pengguna.

- VBA juga dapat membuat sistem lebih kuat dengan memperluas fungsionalitas model spreadsheet dan dengan menyesuaikan penggunaannya.

<!-- halaman 8 -->

# Contoh Pengambilan Keputusan (HIPOTESIS)

- Negara dunia ketiga akan membangun sistem perkeretaapian untuk menghubungkan kawasan industri pedalaman yang potensial dan kawasan pertanian yang baik dengan pelabuhan.

- Sebuah badan pembangunan internasional merekomendasikan bahwa besi di daerah tersebut harus ditambang dan disuling secara lokal dan dilebur menggunakan industri yang harus didirikan.

- Besi olahan kemungkinan diekspor ke Jerman dan Jepang untuk industri mobil.

- Untuk keberhasilan proyek itu membutuhkan pasokan tenaga kerja terampil. Untuk mengatasi masalah ini pusat pelatihan harus didirikan untuk melatih pekerja pada saat pabrik siap.

- Badan Pembangunan juga merekomendasikan lahan subur di daerah tersebut harus disiapkan untuk pertanian intensif untuk menyediakan makanan bagi konsumsi masyarakat yang bekerja di industri.

- Kereta api harus menghubungkan kawasan industri, pertanian dan pelabuhan.

<!-- halaman 9 -->

# MASALAH YANG DITANGANI

- Apakah rutenya optimal? Apakah semua kemungkinan pengguna terhubung?

- Apa saja rute yang mungkin?

- Pertumbuhan lalu lintas: Sejauh mana perkembangan perkeretaapian bergantung pada pembangunan pelabuhan, kota baru, bandara, kawasan industri dan kawasan pertanian?

- Persaingan: Sampai sejauh mana pembangunan jalan yang lebih baik akan menghilangkan kebutuhan akan perkeretaapian?

- Masalah teknik: Berapa banyak listrik yang dibutuhkan untuk kereta listrik?

- Masalah pasokan: Dari mana pasokan peralatan dan bahan untuk konstruksi akan dicari?

- Masalah operasional: Dengan pasokan pekerja terampil lokal yang tidak memadai, dari mana tim operasi akan diperoleh? Apakah kontaktor operasi asing akan digunakan?

- Skala Waktu: Kapan memulai proyek dan kapan akan selesai?

- Biaya: Berapa total biaya proyek?

- Infrastruktur: Apakah layanan yang tersedia meliputi: telepon, pemadam kebakaran, air, komunikasi radio, rumah sakit, hotel, dan perumahan?

<!-- halaman 10 -->

# Langkah-langkah penting dalam proses pengambilan keputusan

Step 1 Concept of Project is Identified
Decision To Proceed Decision To Abandon
Project assessment. Taking
Step 2 account of all issues involved
Decision To Proceed Decision To Abandon
Project Goes to Detail
Step 3 Specification For Tender
Decision To Proceed Decision To Abandon
Tender Accepted. Construction
Step 4
Starts
Decision To Proceed Decision To Abandon
Step 5 Operation Starts
Decision To Proceed Decision To Abandon

<!-- halaman 11 -->

# TAHAP 1

- Kebutuhan konseptual untuk sebuah proyek muncul terutama sebagai akibat dari kebutuhan masa depan yang mendasar.

- Itu mungkin dibuat oleh tim ahli.

- Biasanya studi konseptual akan mengidentifikasi solusi teknis yang diperlukan, manfaat ekonomi, dan penerimaan proyek dalam hal sosial politik.

- Mungkin memerlukan diskusi dengan lembaga keuangan apakah mereka akan menyediakan dana yang diperlukan.

<!-- halaman 12 -->

# TAHAP 2

- Dengan asumsi keputusan telah dibuat untuk mengembangkan proyek lebih lanjut maka penilaian rinci harus dibuat dari semua faktor teknis, ekonomi dan sosial-politik.

- Rinciannya mungkin kuantitatif dan berdasarkan pengetahuan subjektif.

- Pengambilan keputusan utama adalah tentang kebaruan proyek.

- Sebuah proyek secara teknis mungkin baru (membuat pesawat baru).

   - Proyek ini dapat menggunakan teknologi yang sudah mapan di lingkungan baru (menggunakan kereta listrik di negara dunia ketiga).

   - Pada langkah ini tingkat ketidakpastian yang terkait dengan masing-masing faktor akan mulai muncul.

- Pemahaman tentang ketidakpastian yang terkait dengan proposal apa pun sangat penting untuk pengambilan keputusan yang layak.

<!-- halaman 13 -->

# TAHAP 3

- Jika hasil dari langkah 2 adalah melanjutkan proyek, maka spesifikasi tender harus disiapkan.

- Ini harus menentukan, pekerjaan apa yang harus dilakukan tender. Idealnya itu harus mendefinisikan setiap hal yang harus dilakukan.

- Besarnya ketidakpastian yang terkait dengan tahap ini adalah alasan untuk kemungkinan variasi dalam biaya dan durasi proyek.

- Sebelum spesifikasi tender dikeluarkan, adalah bijaksana untuk memastikan bahwa proyek tersebut dapat diterima oleh pihak berwenang dan bahwa keuangan yang memadai tersedia.

- Pembiayaan perlu diyakinkan bahwa proyek itu layak, bahwa pengusul itu sehat dan memiliki pengalaman dan kemampuan untuk membuat proyek itu sampai pada kesimpulan yang sukses.

<!-- halaman 14 -->

# TAHAP 4 ,5

## • TAHAP 4

   - Tindakan pertama adalah memutuskan apakah salah satu tender harus diterima.

   - Penawar harus memiliki pengalaman yang sesuai, kemampuan dan sumber daya keuangan yang memadai.

- TAHAP 5

   - Dengan asumsi semua langkah diselesaikan dengan memuaskan, keputusan harus diambil untuk memulai proyek.

   - Bahkan jika proyek dimulai, itu mungkin harus dihentikan jika lingkungan operasinya berubah.

<!-- halaman 15 -->

# KAREKTERISTIK PENGAMBILAN KEPUTUSAN

- Keputusan dibuat berdasarkan informasi yang tersedia.

- Pada setiap bagian penilaian, mungkin harus ada pengembangan berulang untuk memperhitungkan peningkatan data yang terjadi saat proyek berlangsung.

- Sebuah proyek tidak akan berjalan jika tidak ada pendanaan yang memadai.

<!-- halaman 16 -->

# Management

- **_Manajemen adalah pengambilan keputusan_**

- **_Manajer adalah pengambil keputusan_**

- **_Organisasi diisi dengan pengambil keputusan pada tingkat yang berbeda._**

- **_Manajemen dianggap sebagai seni: bakat yang diperoleh selama bertahun-tahun dengan coba-coba._**

- **_Namun pengambilan keputusan hari ini menjadi lebih rumit:_**

   - **_Teknologi / Informasi/Komputer : bertambah_** à **_Lebih banyak alternatif untuk dipilih_**

   - **_Kompleksitas Struktural / Persaingan : meningkat_** à **_biaya kesalahan yang lebih besar_**

   - **_Pasar internasional / Konsumerisme : meningkat_** à **_lebih banyak ketidakpastian tentang masa depan_**

   - **_Perubahan, Fluktuasi : meningkat_** à **_kebutuhan akan keputusan cepat_**

<!-- halaman 17 -->

# MASALAH Management

- Sebagian besar masalah manajemen yang keputusannya dicari dapat diwakili oleh tiga elemen standar - tujuan, variabel keputusan, dan kendala.

- **Tujuan**

   - Maksimalkan keuntungan

   - Berikan entri paling awal ke pasar

   - Meminimalkan ketidaknyamanan/pergantian karyawan

- **Variabel keputusan**

   - Tentukan harga yang akan digunakan

   - Tentukan lamanya waktu pengujian harus dijalankan pada produk/layanan baru

   - Tentukan tanggung jawab yang harus diberikan kepada setiap pekerja

- **Kendala**

   - Tidak dapat mengenakan biaya di bawah anggaran

   - Uji cukup untuk memenuhi peraturan keselamatan minimum

   - Pastikan tanggung jawab paling banyak dimiliki oleh dua pekerja

<!-- halaman 18 -->

# Tipe masalah

- Terstruktur: situasi di mana prosedur yang harus diikuti ketika keputusan diperlukan dapat ditentukan sebelumnya

   - Berulang-ulang

   - Metode solusi standar ada

   - Otomatisasi lengkap mungkin layak

- Tidak terstruktur: situasi keputusan di mana tidak mungkin untuk menentukan terlebih dahulu sebagian besar prosedur keputusan yang harus diikuti

- Satu kali

- Tidak ada solusi standar

- Mengandalkan penilaian

   - Otomatisasi biasanya tidak dapat dilakukan

- Semi-terstruktur: prosedur keputusan yang dapat ditentukan sebelumnya, tetapi tidak cukup untuk mengarah pada keputusan yang direkomendasikan secara pasti

   - Beberapa elemen dan/atau fase proses pengambilan keputusan memiliki elemen yang berulang

DSS paling berguna untuk aspek berulang dari masalah semi-terstruktur

<!-- halaman 19 -->

# DSS secara ringkas

- Sebuah SISTEM KOMPUTER TINGKAT MANAJEMEN Yang :

- • MENGGABUNGKAN DATA,

   - MODEL,

   - PENGGUNA - PERANGKAT LUNAK RAMAH

- UNTUK PENGAMBILAN KEPUTUSAN SEMISTRUKTUR & TIDAK TERSTRUKTUR.

   - Menggunakan data, menyediakan antarmuka yang mudah digunakan, dan memungkinkan wawasan pembuat keputusan sendiri.

<!-- halaman 20 -->

# Mengapa DSS?

- Meningkatnya kompleksitas keputusan • Teknologi

   - Informasi:

   - “Data, data di mana-mana, dan bukan waktunya untuk berpikir!”

   - • Jumlah dan kompleksitas opsi

   - Kecepatan perubahan

- Meningkatkan ketersediaan dukungan terkomputerisasi • Komputasi bertenaga tinggi yang murah

   - Perangkat lunak yang lebih baik

   - Proses pengembangan perangkat lunak yang lebih efisien

- Meningkatkan kegunaan komputer

<!-- halaman 21 (OCR) -->

Universitas Transformation
Kampus
Sumatera Utara Towards the Ultimate Merdeka
INDONESIA JAYA
Manfaat dari DSS

- **kualitas keputusan**

- **komunikasi yang ditingkatkan**

- **pengurangan biaya**

- **peningkatan produktivitas**

- **penghematan waktu**

- **meningkatkan kepuasan pelanggan dan karyawan**

# OX
