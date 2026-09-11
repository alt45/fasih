# Otomasi Kuesioner & Perbaikan Data Fasih BPS (Android Automation)

Aplikasi otomasi cerdas berbasis Python dan `uiautomator2` untuk melakukan pengisian kuesioner tugas pencacahan baru serta **perbaikan/pembaruan massal data NIK pelanggan** pada aplikasi **Fasih BPS** (`id.go.bpsfasih`) di perangkat Android secara otomatis, aman, dan efisien.

---

## Daftar Isi
- [Fitur Utama & 7 Mode Operasi](#fitur-utama--7-mode-operasi)
- [Fitur Keamanan & Keandalan Terbaru](#fitur-keamanan--keandalan-terbaru)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Instalasi & Persiapan](#instalasi--persiapan)
- [Format Data Masukan (CSV & JSON)](#format-data-masukan-csv--json)
- [Panduan Menjalankan Aplikasi](#panduan-menjalankan-aplikasi)
- [Manajemen Stok NIK & Logging](#manajemen-stok-nik--logging)
- [Struktur Repositori](#struktur-repositori)

---

## Fitur Utama & 7 Mode Operasi

Aplikasi menyediakan struktur menu bertingkat (Submenu) yang rapi dan mudah dikembangkan:

### ⚡ Kelompok Prabayar (Wajib Cek IDPEL di BLOK I)
| No | Nama Mode | Deskripsi Singkat | Shortcut CLI |
| :---: | :--- | :--- | :--- |
| **[1]** | **Penambahan Data Baru** | Pengisian kuesioner baru dari awal (GPS, foto galeri acak, Blok II, Blok III, Blok IV Jam Selesai & Kirim). | `-m 1` / `-m pra1` / `-m tambah` |
| **[2]** | **Pengeditan Data (Forward)** | Mengambil ID Pelanggan satu per satu dari CSV, mencari di kolom Search HP, lalu mengganti NIK. | `-m 2` / `-m pra2` / `-m edit` |
| **[3]** | **Reverse Mode (Prabayar)** | Pindai seluruh penugasan/meter di HP terlebih dahulu, lalu mencocokkan instan dengan master CSV di memori. | `-m 3` / `-m pra3` / `-m reverse` |
| **[4]** | **Direct Random Prabayar** | Scan penugasan HP -> Cek IDPEL di Blok I -> Isi NIK acak dari file stok JSON tanpa CSV. Coba hingga 5x. | `-m 4` / `-m pra4` / `-m direct_pra` / `-m 7` |

### 🏢 Kelompok Pasca Bayar (Bypass BLOK I -> Langsung BLOK II)
| No | Nama Mode | Deskripsi Singkat | Shortcut CLI |
| :---: | :--- | :--- | :--- |
| **[1]** | **Reverse Pasca Bayar** | Pindai penugasan di HP -> lewati Cek IDPEL Blok I -> cocokkan dengan `masterpasca.csv`. | `-m pasca1` / `-m pasca` / `-m 4` |
| **[2]** | **Pasca Bayar + Daya & Fallback** | Lewati Blok I. Jika NIK utama gagal & bukan 450 VA (900 VA+), otomatis ambil NIK cadangan dari JSON. | `-m pasca2` / `-m pascadaya` / `-m 5` |
| **[3]** | **Direct Random Pasca Bayar** | Scan seluruh IDPEL di HP -> lewati Blok I -> isi NIK acak dari file JSON tanpa CSV. Coba hingga 5x. | `-m pasca3` / `-m direct` / `-m 6` |

---

## Fitur Keamanan & Keandalan Terbaru

### 1. Smart Caching Wilayah (`cache/cache_scan_<wilayah1>.json`)
- **Penyimpanan Terorganisir di Subfolder:** Seluruh berkas cache hasil pemindaian penugasan HP disimpan di dalam subfolder `cache/` (misalnya `cache/cache_scan_525215052151DABMYTB.json`).
- **Dinamis Berbasis Identitas Wilayah:** File cache dinamai berdasarkan `resource-id="wilayah1"` pada layar aplikasi. Jika suatu wilayah sedang diproses, HP lain dapat langsung melanjutkan antrean tanpa perlu memindai ulang.
- **Proteksi Antrean Cache:** Item ID **TIDAK AKAN DIHAPUS** dari cache jika terjadi gangguan koneksi, timeout server, atau terkena Limit API, sehingga data tetap aman dan dapat diproses kembali setelah koneksi stabil atau setelah berganti akun.

### 2. Deteksi & Auto-Skip Kuesioner Belum Tersurvei
- Pada kuesioner yang belum pernah disurvei di lapangan, halaman BLOK I menampilkan tombol *"Ambil Waktu"* dan langsung tombol *"Kirim"*, tanpa adanya tombol *"BERIKUTNYA BLOK II"*.
- Sistem mendeteksi kondisi ini secara otomatis, membatalkan form, mencatat ke `BELUM_TERSURVEI_SKIP.csv`, dan membersihkan item dari antrean cache agar tidak menghambat penugasan lainnya.

### 3. Logika Cek NIK Cerdas & Retry 2x
- **Jika `DITEMUKAN` (Hijau):** Pemadanan sukses, langsung lanjut ke konfirmasi simpan dan kirim.
- **Jika `TIDAK DITEMUKAN`:** Server Dukcapil merespon secara valid bahwa NIK tidak terdaftar. Sistem **tidak mengulang** tombol Cek NIK pada NIK yang sama, melainkan langsung mencoba NIK cadangan lain (fallback acak) jika mode fallback aktif.
- **Jika Kendala Koneksi / Timeout / *"Kesalahan Mengambil Data"*:** Sistem mengulangi penekanan tombol **Cek NIK sekali lagi (Retry ke-2)**. Jika masih gagal karena koneksi, IDPEL di-skip tanpa kirim dan cache scan dipertahankan.
- **Proteksi Mutlak Anti-Kirim:** Tombol *"Kirim"* **MUTLAK DIBLOKIR** jika NIK belum berstatus `DITEMUKAN` (Hijau), mencegah risiko pengiriman data dengan NIK merah/invalid.

### 4. Manajemen Stok NIK JSON Fleksibel (Root & Folder `nik/`)
- Menu pemilihan file JSON stok NIK (`pilih_file_json`) otomatis membaca file `.json` yang ada di **main utama (root)** maupun di dalam subfolder **`nik/`**.
- Menampilkan nomor urut, path file, label lokasi (`[Main]` vs `[Folder nik]`), serta jumlah stok NIK yang tersedia.
- Mendukung pemilihan via nomor urut, tombol **Enter** untuk default (`nik.json` di root atau `nik/nik.json`), atau pengetikan nama file langsung.
- NIK sukses otomatis dicatat ke `nik_valid.json`, sedangkan NIK tidak ditemukan dipindahkan ke `nik_invalid.json`.

### 5. Deteksi Dini Batas Kuota (API Limit)
- Sistem memantau kemunculan banner limit API server BPS secara real-time.
- Begitu limit terdeteksi, sistem segera menampilkan informasi cooldown dan menghentikan proses dengan aman (`ApiLimitError`) agar pengguna dapat logout dan login menggunakan akun pencacah lain.

### 6. Dukungan Multi-Device (Paralel Multi-HP)
- Parameter `--device` / `-d` memungkinkan eksekusi beberapa HP Android sekaligus pada komputer yang sama via USB debugging secara paralel tanpa bentrok antrean cache.

---

## Persyaratan Sistem

1. **Komputer/Laptop:** OS Windows 10/11 dengan Python 3.8 - 3.11 terinstal.
2. **Perangkat HP Android:**
   - Opsi Pengembang (*Developer Options*) aktif.
   - **USB Debugging** diaktifkan.
   - Layar menyala dan aplikasi **Fasih BPS** (`id.go.bpsfasih`) sudah terinstal dan login.
3. **Kabel Data USB:** Koneksi stabil antara HP dan komputer.

---

## Instalasi & Persiapan

1. Buka terminal (PowerShell / CMD) di direktori proyek.
2. Aktifkan virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Pasang library yang diperlukan:
   ```powershell
   pip install -r requirements.txt
   ```
4. Pastikan perangkat Android terdeteksi oleh ADB:
   ```powershell
   adb devices
   ```

---

## Format Data Masukan (CSV & JSON)

### A. Format CSV untuk Mode Tambah Baru (`HENGKI.csv`)
- **Separator:** Titik koma (`;`)
- **Kolom Utama:** `IDPEL`, `NAMA`, `NOIDENTITAS`, `KECAMATAN`, `KELURAHAN_DESA`, `ALAMAT`

### B. Format Master CSV untuk Update NIK (Mode 2, 3, 4, 5)
- **Separator:** Titik koma (`;`)
- **Contoh Header:**
  ```csv
  id_pelanggan;NIK Perbaikan;daya
  521550683355;3308180507950006;900
  521551931787;3308201010770006;450
  ```

### C. Format Stok JSON untuk Mode Direct / Fallback (Mode 5, 6, 7)
File dapat diletakkan di root proyek atau di dalam subfolder `nik/` (misal: `nik/BANDONGAN.json` atau `nik.json`):
```json
[
  "3308113103850004",
  "3308110502900001",
  "3308112208930002"
]
```
*(Mendukung daftar string NIK langsung maupun daftar objek JSON dengan atribut `"nik"`).*

---

## Panduan Menjalankan Aplikasi

### Cara 1: Menu Interaktif Utama (`main.py`)
Posisikan aplikasi Fasih di HP pada halaman **Daftar Assignment**, lalu jalankan:
```powershell
python main.py
```
Pilih angka mode yang diinginkan `[1 - 7]` sesuai kebutuhan.

---

### Cara 2: Menjalankan Langsung via Command Line (`update_nik.py`)

Gunakan argumen baris perintah untuk eksekusi spesifik atau multi-device:

#### Menjalankan Mode 6 (Pasca Bayar Direct HP):
```powershell
python update_nik.py --mode 6 --device <SERIAL_HP> --json nik/MERTOYUDAN.json
```

#### Menjalankan Mode 7 (Prabayar Direct HP):
```powershell
python update_nik.py --mode 7 --device <SERIAL_HP> --json nik.json
```

#### Menjalankan Mode 4 (Pasca Bayar Reverse CSV):
```powershell
python update_nik.py --mode 4 --device <SERIAL_HP> --csv masterpasca.csv
```

#### Menjalankan Multi-Device Bersamaan (2 HP di 2 Terminal Terpisah):
- **Terminal 1 (HP 1):**
  ```powershell
  python update_nik.py --mode 6 --device 068703713T108144 --json nik/BANDONGAN.json
  ```
- **Terminal 2 (HP 2):**
  ```powershell
  python update_nik.py --mode 6 --device RR8N60CWMLZ --json nik/MERTOYUDAN.json
  ```

---

## Manajemen Stok NIK & Logging

### File Log Output Otomatis (CSV)
| File Log | Keterangan |
| :--- | :--- |
| `SUKSES_UPDATE_NIK.csv` | Data IDPEL & NIK yang berhasil diperbarui dan berstatus terkirim. |
| `BELUM_TERSURVEI_SKIP.csv` | Data yang dilewati otomatis karena kuesioner belum disurvei. |
| `IDPEL_TIDAK_DITEMUKAN.csv` | Data IDPEL yang tidak ditemukan di tabel penugasan aplikasi. |
| `NIK_TIDAK_DITEMUKAN.csv` | NIK yang berstatus *TIDAK DITEMUKAN* saat pemadanan Dukcapil. |
| `NIK_GAGAL_UPDATE.csv` | Catatan galat form atau kendala koneksi server selama proses. |
| `BERHASIL_KIRIM.csv` | Data berhasil kirim untuk mode penambahan kuesioner baru. |

### Pemilahan Stok NIK JSON Real-Time
| File JSON | Keterangan |
| :--- | :--- |
| `<nama_file>.json` | File stok aktif (NIK yang sudah terpakai atau invalid otomatis dihapus). |
| `nik_valid.json` | Arsip NIK yang terbukti **SESUAI/DITEMUKAN** dan telah berhasil dikirim ke server (disimpan lengkap dengan IDPEL & waktu). |
| `nik_invalid.json` | Arsip NIK yang dinyatakan **TIDAK DITEMUKAN** oleh Dukcapil agar tidak dicoba kembali. |

---

## Struktur Repositori

```text
├── core/                           # Paket inti otomasi modular
│   ├── __init__.py                 # Ekspor fungsi-fungsi utama
│   ├── config.py                   # Konfigurasi konstanta & nama file
│   ├── csv_utils.py                # Utilitas pembacaan & penulisan CSV log
│   ├── exceptions.py               # Custom Exception (ApiLimitError, dll)
│   ├── form_processor.py           # Logika pemadanan BLOK I/II & tombol Kirim
│   ├── logger.py                   # Sistem pencatatan logging
│   ├── nik_provider.py             # Manajemen stok NIK JSON, fallback & menu pilih
│   ├── scanner.py                  # Pemindaian tabel HP & smart caching wilayah
│   └── ui_helpers.py               # Operasi UI Android (klik, input, scroll)
├── cache/                          # Subfolder penyimpanan file cache antrean HP
│   └── cache_scan_<wilayah1>.json  # File cache penugasan per wilayah
├── nik/                            # Subfolder koleksi file stok NIK JSON
│   └── *.json                      # File stok NIK per kecamatan/wilayah
├── main.py                         # Peluncur utama dengan menu 7 mode operasi
├── update_nik.py                   # Skrip eksekutor perbaikan data NIK
├── analisa_ui.py                   # Alat bantu inspeksi hierarchy XML Android
├── requirements.txt                # Dependensi modul Python
└── README.md                       # Dokumentasi panduan lengkap
```
