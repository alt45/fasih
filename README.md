# Otomasi Kuesioner & Perbaikan Data Fasih BPS (Android Automation)

Aplikasi otomasi berbasis Python untuk melakukan pengisian kuesioner tugas pencacahan serta **perbaikan/pembaruan data NIK** pada aplikasi **Fasih BPS** (`id.go.bpsfasih`) di perangkat Android secara otomatis menggunakan data dari file CSV.

---

## Fitur Utama

Aplikasi ini memiliki 2 mode operasi utama yang dapat dipilih melalui menu interaktif:

### 1. Penambahan Data Baru (`main.py`)
- **Alur Penuh Tambah Assignment:** Pengisian kuesioner dari awal untuk ID Pelanggan yang belum tercatat (pengambilan GPS, foto galeri acak, pengisian Blok II, Blok III, hingga Blok IV Jam Selesai & Kirim).
- **Pembersihan Nama Pintar:** Sanitasi karakter khusus dan tanda baca agar sesuai aturan validasi aplikasi.
- **Log Pelacakan:** Data sukses dicatat ke `BERHASIL_KIRIM.csv` dan otomatis dihapus dari file sumber (`HENGKI.csv`).

### 2. Perbaikan / Update Data NIK (`update_nik.py`)
- **Pencarian Assignment Cepat:** Menginput ID Pelanggan di kolom *Search* pada tabel penugasan.
- **Penanganan IDPEL Tidak Ditemukan:** Jika ID Pelanggan tidak ada di penugasan, otomatis dicatat ke `IDPEL_TIDAK_DITEMUKAN.csv`, dihapus dari daftar CSV input, kolom pencarian dibersihkan, dan langsung beralih ke ID berikutnya tanpa macet.
- **Validasi BLOK I:** Menggulir layar, klik **Cek ID Pelanggan**, lalu navigasi ke BLOK II.
- **Pembaruan NIK Cepat & Presisi di BLOK II:** Menghapus NIK lama, mengetik NIK perbaikan secara instan, dan memicu penekanan tombol fisik **Cek NIK**.
- **Pengecekan Pemadanan Server:**
  - Jika hasil pemadanan NIK **`TIDAK DITEMUKAN`**: otomatis dicatat ke `NIK_TIDAK_DITEMUKAN.csv`, dihapus dari CSV input, form dibatalkan secara bersih (menekan tombol kembali & konfirmasi `IYA`), dan lanjut ke baris berikutnya.
  - Jika hasil pemadanan **`SESUAI / DITEMUKAN`**: melanjutkan proses penyimpanan.
- **Pengecekan Galat Otomatis:** Memeriksa status galat aktif (harus `GALAT 0`) sebelum konfirmasi pengiriman.
- **Deteksi Layar Akhir Adaptif:**
  - **Jika Masuk ke `Halaman Upload`:** Otomatis mendeteksi status `PENDING SUBMIT`, mengklik **`Cek Status`**, menunggu hingga status antrian berubah menjadi **`SUCCESS SUBMIT`**, lalu menekan tombol **Kembali (Back)** menuju Daftar Assignment.
  - **Jika Langsung Kembali ke `Daftar Assignment`:** Otomatis mendeteksi halaman depan tanpa waktu tunggu yang sia-sia, membersihkan kotak pencarian, mencatat hasil ke `SUKSES_UPDATE_NIK.csv`, dan melanjutkan ke baris berikutnya.

---

## Persyaratan Sistem

1. **Komputer/Laptop:** OS Windows dengan Python 3.8 ke atas terinstal.
2. **Perangkat HP Android:**
   - Fitur **USB Debugging** aktif (di Opsi Pengembang).
   - HP terhubung ke komputer via kabel data USB.
   - Layar HP menyala dan aplikasi Fasih BPS terinstal.

---

## Langkah Instalasi & Persiapan

Jalankan perintah berikut di terminal (PowerShell atau CMD) di folder proyek:

### 1. Mengaktifkan Virtual Environment
* **Windows PowerShell:**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Windows CMD:**
  ```cmd
  .\venv\Scripts\activate.bat
  ```

### 2. Menginstal Dependensi
```powershell
pip install -r requirements.txt
```

---

## Format Data CSV

### A. Untuk Mode Tambah Baru (`HENGKI.csv`)
- **Separator:** Titik koma (`;`)
- **Kolom Utama:** `IDPEL`, `NAMA`, `NOIDENTITAS`, `KECAMATAN`, `KELURAHAN_DESA`, `ALAMAT`

### B. Untuk Mode Update NIK (`ahzacahyo.csv`)
- **Separator:** Titik koma (`;`)
- **Format Header:**
  ```csv
  id_pelanggan;NIK Perbaikan
  521550683355;3308180507950006
  521551931787;3308201010770006
  ```

---

## Cara Menjalankan

### Cara 1: Melalui Menu Interaktif Utama
Posisikan layar HP pada halaman depan **Daftar Assignment** di aplikasi Fasih BPS, lalu jalankan:
```powershell
python main.py
```
Pilih mode yang diinginkan:
- Ketik **`1`** untuk Penambahan Data Baru.
- Ketik **`2`** untuk Perbaikan Data NIK.

### Cara 2: Menjalankan Langsung Skrip Update NIK (Dukungan Multi-Device & Custom CSV)

- **Mode Standar (Auto-detect):**
  ```powershell
  python update_nik.py
  ```
  *(Jika terhubung lebih dari 1 HP, script akan memunculkan menu interaktif untuk memilih perangkat).*

- **Mode Multi-Device / Custom File CSV:**
  Gunakan parameter `--device` (atau `-d`) dan `--csv` (atau `-c`):
  ```powershell
  python update_nik.py --device <SERIAL_HP> --csv <NAMA_FILE.csv>
  ```
  *Contoh menjalankan 2 HP secara bersamaan di 2 terminal terpisah:*
  - **Terminal 1:**
    ```powershell
    python update_nik.py --device 068703713T108144 --csv data_hp1.csv
    ```
  - **Terminal 2:**
    ```powershell
    python update_nik.py --device RR8N60CWMLZ --csv data_hp2.csv
    ```

---

## File Log & Output Otomatis

| Nama File | Keterangan |
| :--- | :--- |
| `SUKSES_UPDATE_NIK.csv` | Catatan ID Pelanggan dan NIK yang berhasil diperbarui dan disubmit. |
| `IDPEL_TIDAK_DITEMUKAN.csv` | Catatan ID Pelanggan yang tidak ada dalam daftar penugasan. |
| `NIK_TIDAK_DITEMUKAN.csv` | Catatan NIK yang gagal dipadankan di server BPS (status *TIDAK DITEMUKAN*). |
| `NIK_GAGAL_UPDATE.csv` | Catatan error teknis / form galat selama proses perbaikan. |
| `BERHASIL_KIRIM.csv` | Catatan data yang sukses disubmit pada mode penambahan kuesioner baru. |

---

## Struktur Repositori

```text
├── main.py                    # Berkas utama peluncur & menu otomasi
├── update_nik.py              # Modul otomasi perbaikan / update NIK
├── analisa_ui.py              # Utilitas inspeksi & dump UI Android
├── requirements.txt           # Daftar dependensi library Python
├── README.md                  # Dokumentasi panduan penggunaan
└── .gitignore                 # Konfigurasi pengabaian file sampah & log
```
