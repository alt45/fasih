"""
Modul Penyedia NIK Cadangan dan Parser Daya Listrik (Fasih BPS)
Digunakan untuk Fallback NIK otomatis dari berkas nik.json
"""
import json
import os
import random
import re


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
    Mengelola pengambilan NIK valid dari file nik.json secara acak atau berurutan.
    """
    def __init__(self, json_path="nik.json", state_file=".nik_fallback_state.json"):
        self.json_path = json_path
        self.state_file = state_file
        self.niks = []
        self.index = 0
        self.load()

    def load(self):
        """Memuat daftar NIK dari nik.json dan posisi indeks dari state_file."""
        if not os.path.exists(self.json_path):
            print(f"[!] Peringatan: Berkas '{self.json_path}' tidak ditemukan!")
            return
        
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.niks = [str(x).strip() for x in data if str(x).strip()]
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

    def get_random(self):
        """
        Mengambil satu NIK cadangan secara acak (random) dari daftar nik.json.
        """
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

        if self.index >= len(self.niks):
            print("[*] Catatan: Seluruh NIK di nik.json sudah digunakan sekali, merotasi kembali ke awal.")
            self.index = 0

        nik = self.niks[self.index]
        self.index += 1
        self.save_state()
        return nik

    def peek_next(self):
        """Melihat NIK berikutnya tanpa memajukan pointer indeks."""
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
        return len(self.niks)
