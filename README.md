Otoklim
=======

Otoklim adalah aplikasi opensource yang berguna untuk mendukung otomasisai prediksi dan analisis musiman yang dihasilkan oleh Stasiun Klimatologi BMKG. Aplikasi ini dikembangkan dalam bentuk plugin di [QGIS](http://qgis.org). Untuk saat ini, plugin Otoklim yang dikembangkan masih terbatas penggunaanya untuk provinsi Jawa Timur.
Berikut ini adalah fungsi-fungsi dari Plugin Otoklim :
* Melakukan interpolasi data curah dan sifat hujan
* Membuat peta dari data hasil interpolasi dalam format .pdf
* Membuat data summary dalam format .csv untuk setiap wilayah administrasi

Persyaratan Sistem
-------------------

* PC standar (RAM minimal 4GB) dengan sistem Operasi Windows, Linux atau Mac OS X
* Perangkat lunak QGIS dengan versi di atas 2.0 atau versi yang lebih baru.

Cara Instalasi
-------------------

### 1. Instalasi secara manual:
* Unduh dan instal aplikasi QGIS (http://www.qgis.org/en/site/forusers/download.html)
* Unduh plugin Otoklim (https://github.com/geoenvo/otoklim.git)
* Ekstrak file otoklim-master.zip ke direktori berikut : `C:\Users\"username"\.qgis2\python\plugins`
* Ubah nama folder "otoklim-master" menjadi "Otoklim"
* Jalankan QGIS Desktop sebagai administrator (Klik kanan --> Run As Administrator)

### 2. Instalasi menggunakan GIT:
* Unduh dan Instal QGIS (http://www.qgis.org/en/site/forusers/download.html)
* Unduh dan Instal GIT (https://git-scm.com/downloads)
* Buka Git CMD, lakukan perintah berikut:
* `cd C:\Users\"username"\.qgis2\python\plugins`
* `git clone https://github.com/geoenvo/otoklim.git Otoklim`
* Jalankan QGIS Desktop sebagai administrator (Klik kanan --> Run As Administrator

### 3. Instalasi dari menu QGIS Plugins:

Petunjuk Penggunaan
-------------------
Mengacu pada halaman berikut: https://github.com/geoenvo/otoklim/wiki/User-Guide