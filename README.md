# Otomasi Kuesioner & Perbaikan Data Fasih BPS (Android Automation)

Aplikasi otomasi berbasis Python untuk melakukan pengisian kuesioner tugas pencacahan serta **perbaikan/pembaruan data NIK** pada aplikasi **Fasih BPS** (`id.go.bpsfasih`) di perangkat Android secara otomatis menggunakan data dari file CSV.

---

## Fitur Utama

Aplikasi ini memiliki 2 mode operasi utama yang dapat dipilih melalui menu interaktif:

### 1. Penambahan Data Baru (`main.py`)
- **Alur Penuh Tambah Assignment:** Pengisian kuesioner dari awal untuk ID Pelanggan yang belum tercatat (pengambilan GPS, foto galeri acak, pengisian Blok II, Blok III, hingga Blok IV Jam Selesai & Kirim).
- **Pembersihan Nama Pintar:** Sanitasi karakter khusus dan tanda baca agar sesuai aturan validasi aplikasi.
- **Log Pelacakan:** Data sukses dicatat ke `BERHASIL_KIRIM.csv` dan otomatis dihapus dari file sumber (`HENGKI.csv`).

### 2. Perbaikan / Update Data NIK (Forward Mode: CSV -> Cari di HP)
- **Pencarian Assignment:** Menginput ID Pelanggan dari CSV di kolom *Search* pada tabel penugasan.
- **Penanganan IDPEL Tidak Ditemukan:** Otomatis dicatat ke `IDPEL_TIDAK_DITEMUKAN.csv` dan dilewati tanpa macet.
- **Validasi BLOK I & II:** Verifikasi ID Pelanggan, berpindah ke Blok II (1x klik adaptif dengan verifikasi kata NIK), mengetik NIK baru, dan memicu tombol fisik Cek NIK.
- **Pemadanan & Submit:** Memverifikasi status pemadanan server BPS (DITEMUKAN vs TIDAK DITEMUKAN), mengecek galat (harus `GALAT 0`), submit, cek antrean upload `SUCCESS`, dan kembali ke Daftar Assignment.

### 3. Pengeditan Data Terbalik (Reverse Mode: Pindai HP -> Cocokkan Master)
- **Sangat Cepat untuk Master CSV Besar:** Jika file master berisi ribuan data (misal 5.000 - 13.000 baris) sedangkan di HP hanya ada puluhan penugasan, mode ini memindai seluruh nomor meter/IDPEL di HP terlebih dahulu.
- **Show 100 entries Otomatis:** Membuka seluruh penugasan dalam 1 halaman utuh tanpa pagination.
- **Pencocokan Instan:** Mencocokkan data HP dengan file master (`mastermeter.csv` atau `master.csv`) di memori dalam hitungan milidetik.
- **Eksekusi Terarah:** Hanya mengeksekusi penugasan yang memang cocok dan memerlukan perbaikan NIK.

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
1. Pilih mode yang diinginkan:
   - Ketik **`1`** untuk Penambahan Data Baru.
   - Ketik **`2`** untuk Perbaikan Data NIK.
   - Ketik **`0`** untuk Keluar.
2. Setelah memilih mode, sistem akan menampilkan daftar seluruh file CSV yang ada di folder proyek lengkap dengan jumlah data:
   - Ketik **nomor urut** (misal: `1`, `2`, `3`) untuk memilih file langsung.
   - Atau ketik **nama file secara langsung** (misal: `data_saya.csv` atau `data_saya`).
   - Ketik **`0`** untuk batal dan kembali ke menu utama.

### Cara 2: Menjalankan Langsung Skrip Update NIK (Dukungan Multi-Device & Custom CSV)

- **Mode Interaktif Standar:**
  ```powershell
  python update_nik.py
  ```
  *(Script akan memunculkan menu interaktif untuk memilih file CSV dan memilih perangkat jika terhubung lebih dari 1 HP).*

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
