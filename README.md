# Otomasi Kuesioner Fasih BPS (Android Automation)

Aplikasi otomasi berbasis Python untuk melakukan pengisian kuesioner tugas pencacahan pada aplikasi **Fasih BPS** (`id.go.bpsfasih`) di perangkat Android secara otomatis menggunakan data dari file CSV.

## Fitur Utama

- **Otomasi Alur Pengisian Penuh:** Mulai dari pencarian ID Pelanggan, validasi status data, pengambilan lokasi GPS, unggah foto, pengisian Blok II (Nama, NIK, HP, status rumah), Blok III (Provinsi, Kabupaten, Kecamatan, Desa/Kelurahan, Alamat, Jumlah Keluarga), hingga Blok IV (Jam Selesai & Kirim).
- **Auto-Recovery & Loop Pengulangan:** Jika terjadi kendala koneksi atau elemen UI lambat termuat, aplikasi otomatis membatalkan form secara bersih, kembali ke halaman utama, dan mengulang pengisian untuk data yang sama agar tidak ada data yang terlewat.
- **Pembersihan Nama Pintar:** Mengamankan nama penghuni agar hanya berisi huruf dan spasi (menghapus tanda baca, angka, dan simbol secara otomatis sesuai aturan validasi aplikasi).
- **Dukungan Foto Galeri Acak:** Mengambil foto secara acak dari 6 foto teratas di galeri Anda untuk menghindari pengiriman berkas gambar yang identik.
- **Log Pelacakan Sukses:** Menyalin data yang sukses terkirim ke berkas `BERHASIL_KIRIM.csv` dan secara otomatis menghapusnya dari file sumber (`HENGKI.csv`).
- **Mekanisme Ketahanan Tinggi:** Dilengkapi fitur *Auto-Retry* per-langkah interaksi untuk mengantisipasi keterlambatan server BPS atau fluktuasi RPC Android.

---

## Persyaratan Sistem

1. **Komputer/Laptop:** OS Windows dengan Python 3.8 ke atas terinstal.
2. **Perangkat HP Android:**
   - Fitur **USB Debugging** aktif (di Opsi Pengembang).
   - HP terhubung ke komputer menggunakan kabel USB berkualitas baik.
   - GPS HP dalam kondisi aktif.
3. **Konfigurasi Mock Location (Opsional):**
   - Jika ingin memalsukan lokasi, daftarkan aplikasi pembantu (seperti **ATX** atau **Appium Settings**) sebagai aplikasi lokasi palsu di Opsi Pengembang HP Anda.

---

## Langkah Instalasi & Persiapan

Ikuti langkah berikut di terminal komputer Anda (PowerShell/CMD) di dalam direktori folder `fasih`:

### 1. Membuat Virtual Environment (Rekomendasi)
```powershell
python -m venv venv
```

### 2. Mengaktifkan Virtual Environment
* **Di Windows PowerShell:**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Di Windows CMD:**
  ```cmd
  .\venv\Scripts\activate.bat
  ```

### 3. Menginstal Dependensi Pihak Ketiga
```powershell
pip install -r requirements.txt
```

---

## Penyiapan Data CSV

Siapkan file data target bernama **`HENGKI.csv`** di dalam folder yang sama dengan `main.py`.
- **Separator:** Menggunakan titik koma (`;`).
- **Kolom Utama Wajib:** 
  - `IDPEL` (ID Pelanggan)
  - `NAMA` (Nama Pelanggan)
  - `NOIDENTITAS` (NIK Pelanggan)
  - `KECAMATAN`
  - `KELURAHAN_DESA` / `KELURAHAN`
  - `ALAMAT`

---

## Cara Menjalankan

1. Hubungkan HP Android ke komputer via USB dan pastikan perangkat dikenali dengan mengetik perintah:
   ```bash
   adb devices
   ```
2. Pastikan serial device pada baris berikut di berkas `main.py` sudah disesuaikan dengan serial HP Anda:
   ```python
   device_id = "RR8N60CWMLZ" # Ganti dengan serial HP Anda
   ```
3. Posisikan layar HP Anda pada halaman depan **Daftar Assignment** di aplikasi Fasih BPS.
4. Jalankan aplikasi otomasi:
   ```powershell
   python main.py
   ```

---

## Struktur Repositori

- `main.py` - Berkas utama kode program otomasi.
- `requirements.txt` - Daftar dependensi pustaka Python.
- `HENGKI.csv` - File data pelanggan yang akan diproses.
- `BERHASIL_KIRIM.csv` - Berkas log output data pelanggan yang sukses disubmit.
- `.gitignore` - Mengabaikan berkas sampah python dan file lokal agar tidak masuk repositori git.
