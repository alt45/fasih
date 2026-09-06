"""
Modul Penyedia NIK Cadangan dan Parser Daya Listrik (Fasih BPS)
Digunakan untuk Fallback NIK otomatis dari berkas nik.json
Mendukung penghapusan real-time NIK invalid ke nik_invalid.json
dan pencatatan NIK sukses terpakai ke nik_valid.json.
"""
import datetime
import json
import os
import random
import re
import threading


def is_daya_450(daya_str):
    """
    Mendeteksi apakah daya listrik merupakan daya 450 (subsidi murni yang tidak boleh difallback).
    Mengembalikan True jika daya 450 (misal '450', 'R1/450', '450 VA', '450.0').
    Mengembalikan False untuk daya lainnya seperti 900, 1300, 2200, dst. (diperbolehkan fallback).
    """
    if not daya_str:
        return False
    match = re.search(r'(?<!\d)450(?!\d)', str(daya_str))
    return bool(match)


class FallbackNIKProvider:
    """
    Mengelola pengambilan NIK valid dari file nik.json secara acak atau berurutan,
    sekaligus mengelola pemilahan data:
    - NIK TIDAK DITEMUKAN -> Dihapus dari file aktif dan disimpan ke nik_invalid.json
    - NIK SESUAI & TERPAKAI -> Dihapus dari file aktif dan dicatat ke nik_valid.json
    """
    def __init__(self, json_path="nik.json", state_file=".nik_fallback_state.json",
                 invalid_file="nik_invalid.json", valid_file="nik_valid.json"):
        self.json_path = json_path
        self.state_file = state_file
        self.invalid_file = invalid_file
        self.valid_file = valid_file
        self.niks = []
        self.index = 0
        self.lock = threading.Lock()
        self.load()

    def _save_json(self, file_path, data):
        """Menyimpan data ke file JSON secara aman (atomic write)."""
        temp_file = f"{file_path}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if os.path.exists(file_path):
                os.replace(temp_file, file_path)
            else:
                os.rename(temp_file, file_path)
        except Exception as e:
            print(f"[X] Gagal menyimpan file JSON '{file_path}': {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def load(self):
        """Memuat daftar NIK dari json_path dan posisi indeks dari state_file."""
        if not os.path.exists(self.json_path):
            print(f"[!] Peringatan: Berkas '{self.json_path}' tidak ditemukan!")
            return
        
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Mendukung list of string maupun list of dict
                    self.niks = [
                        str(x["nik"] if isinstance(x, dict) and "nik" in x else x).strip()
                        for x in data
                        if str(x).strip()
                    ]
                else:
                    self.niks = []
            print(f"[OK] Berhasil memuat {len(self.niks)} NIK cadangan dari '{self.json_path}'")
        except Exception as e:
            print(f"[X] Gagal membaca berkas '{self.json_path}': {e}")
            self.niks = []

        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.index = int(state.get("last_index", 0))
                    if self.index >= len(self.niks):
                        self.index = 0
            except Exception:
                self.index = 0
        else:
            self.index = 0

    def record_invalid(self, nik, reason="TIDAK DITEMUKAN"):
        """
        Menghapus NIK yang tidak valid dari daftar aktif (memori & file json),
        lalu mencatatnya ke file arsip nik_invalid.json agar tidak hilang.
        """
        nik_clean = str(nik).strip()
        if not nik_clean:
            return

        with self.lock:
            # 1. Hapus dari memori & perbarui file aktif
            if nik_clean in self.niks:
                self.niks.remove(nik_clean)
                self._save_json(self.json_path, self.niks)

            # 2. Tambahkan ke file arsip invalid
            try:
                existing = []
                if os.path.exists(self.invalid_file):
                    try:
                        with open(self.invalid_file, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                            if not isinstance(existing, list):
                                existing = []
                    except Exception:
                        existing = []

                existing_niks = {
                    str(x.get("nik") if isinstance(x, dict) else x).strip()
                    for x in existing
                }
                if nik_clean not in existing_niks:
                    existing.append({
                        "nik": nik_clean,
                        "alasan": reason,
                        "waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    self._save_json(self.invalid_file, existing)

                print(f"[*] NIK {nik_clean} {reason}: Dihapus dari '{self.json_path}' & disimpan ke '{self.invalid_file}' (Sisa stok: {len(self.niks)})")
            except Exception as e:
                print(f"[!] Gagal mengarsipkan NIK invalid {nik_clean}: {e}")

    def record_valid(self, nik, idpel=None):
        """
        Menghapus NIK yang sukses terpakai dari daftar aktif (memori & file json),
        lalu mencatatnya ke file arsip nik_valid.json (lengkap dengan pasangan IDPEL & waktu).
        """
        nik_clean = str(nik).strip()
        if not nik_clean:
            return

        with self.lock:
            # 1. Hapus dari memori & perbarui file aktif
            if nik_clean in self.niks:
                self.niks.remove(nik_clean)
                self._save_json(self.json_path, self.niks)

            # 2. Tambahkan ke file arsip valid
            try:
                existing = []
                if os.path.exists(self.valid_file):
                    try:
                        with open(self.valid_file, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                            if not isinstance(existing, list):
                                existing = []
                    except Exception:
                        existing = []

                entry = {
                    "nik": nik_clean,
                    "idpel": str(idpel).strip() if idpel else "-",
                    "waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                existing.append(entry)
                self._save_json(self.valid_file, existing)

                print(f"[OK] NIK {nik_clean} SESUAI & TERPAKAI (IDPEL: {idpel}): Dihapus dari '{self.json_path}' & dicatat ke '{self.valid_file}' (Sisa stok: {len(self.niks)})")
            except Exception as e:
                print(f"[!] Gagal mencatat NIK valid {nik_clean}: {e}")

    def get_random(self):
        """
        Mengambil satu NIK cadangan secara acak (random) dari daftar aktif.
        """
        with self.lock:
            if not self.niks:
                return None
            return random.choice(self.niks)

    def get_next(self, random_pick=True):
        """
        Mengambil satu NIK cadangan. Default mengambil secara acak (random_pick=True).
        Jika random_pick=False, mengambil secara berurutan (*sequential*).
        """
        if not self.niks:
            return None
        
        if random_pick:
            return self.get_random()

        with self.lock:
            if self.index >= len(self.niks):
                print(f"[*] Catatan: Seluruh NIK di {self.json_path} sudah digunakan sekali, merotasi kembali ke awal.")
                self.index = 0

            nik = self.niks[self.index]
            self.index += 1
            self.save_state()
            return nik

    def peek_next(self):
        """Melihat NIK berikutnya tanpa memajukan pointer indeks."""
        with self.lock:
            if not self.niks:
                return None
            idx = self.index if self.index < len(self.niks) else 0
            return self.niks[idx]

    def save_state(self):
        """Menyimpan indeks pointer saat ini ke file state lokal."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({"last_index": self.index}, f)
        except Exception:
            pass

    def __len__(self):
        with self.lock:
            return len(self.niks)


def pilih_file_json(judul_mode="Perbaikan Data NIK (Direct Mode 6)"):
    """
    Menampilkan daftar file JSON yang tersedia di folder proyek dan meminta
    pengguna memilih nomor urut file atau mengetik nama file secara manual.
    Jika user langsung menekan Enter atau memilih default, gunakan 'nik.json'.
    """
    ignore_files = {
        ".nik_fallback_state.json",
        "nik_invalid.json",
        "nik_valid.json",
        "configfs.json",
    }
    
    all_files = [f for f in os.listdir(".") if f.lower().endswith(".json") and os.path.isfile(f)]
    candidate_files = [f for f in all_files if f.lower() not in ignore_files and not f.startswith(".")]
    candidate_files.sort()

    if "nik.json" in candidate_files:
        candidate_files.remove("nik.json")
        candidate_files.insert(0, "nik.json")

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    mode_text = f"PILIH FILE JSON NIK - {judul_mode}" if judul_mode else "PILIH FILE JSON NIK"
    print(f"║  {mode_text:<56}║")
    print("╠══════════════════════════════════════════════════════════╣")

    if candidate_files:
        print("║  File JSON yang terdeteksi di folder:                    ║")
        for i, f_name in enumerate(candidate_files, start=1):
            count_str = ""
            try:
                with open(f_name, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        count_str = f"({len(data)} NIK)"
            except Exception:
                pass
            item_str = f"[{i}] {f_name}"
            print(f"║   {item_str:<32} {count_str:>20} ║")
    else:
        print("║  (Tidak ada file JSON selain default terdeteksi)        ║")

    print("║                                                          ║")
    print("║   [Enter] Gunakan default: 'nik.json'                    ║")
    print("║   [0] Batal / Keluar                                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    while True:
        prompt_text = f"   Pilih nomor [1-{len(candidate_files)}] atau tekan Enter [nik.json]: " if candidate_files else "   Ketik nama file JSON (atau tekan Enter untuk nik.json): "
        pilihan = input(prompt_text).strip()

        if not pilihan:
            default_file = "nik.json"
            print(f"[OK] Menggunakan file default: {default_file}\n")
            return default_file

        if pilihan == "0" or pilihan.lower() in ["batal", "exit", "keluar"]:
            print("[*] Pemilihan file JSON dibatalkan.")
            return None

        # Jika user memasukkan angka pilihan dari daftar
        if pilihan.isdigit() and candidate_files:
            idx = int(pilihan)
            if 1 <= idx <= len(candidate_files):
                selected = candidate_files[idx - 1]
                print(f"[OK] File JSON dipilih: {selected}\n")
                return selected
            else:
                print(f"   [!] Pilihan nomor {idx} di luar jangkauan (1-{len(candidate_files)}).")
                continue

        # Jika user mengetik nama file secara langsung
        custom_name = pilihan
        if not custom_name.lower().endswith(".json") and not os.path.exists(custom_name):
            if os.path.exists(custom_name + ".json"):
                custom_name = custom_name + ".json"

        if os.path.exists(custom_name):
            print(f"[OK] File JSON dipilih: {custom_name}\n")
            return custom_name
        else:
            print(f"   [!] File '{custom_name}' tidak ditemukan di folder. Silakan coba lagi.")
