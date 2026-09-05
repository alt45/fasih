import csv
import os
import re
from .config import CSV_DELIMITER


def pilih_file_csv(judul_mode="Perbaikan Data NIK"):
    """
    Menampilkan daftar file CSV yang tersedia di folder proyek dan meminta
    pengguna memilih nomor urut file atau mengetik nama file secara manual.
    Mengembalikan path file CSV yang valid, atau None jika pengguna membatalkan.
    """
    ignore_files = {
        "berhasil_kirim.csv",
        "sukses_update_nik.csv",
        "idpel_tidak_ditemukan.csv",
        "nik_tidak_ditemukan.csv",
        "nik_gagal_update.csv",
        "idpeltmg_belum_tercatat.csv",
        "idpeltmg_sudah_tercatat.csv",
        "idpeltmg_tidak_ditemukan.csv",
        "idpeltmg_gagal_cek.csv",
    }
    
    all_files = [f for f in os.listdir(".") if f.lower().endswith(".csv") and os.path.isfile(f)]
    candidate_files = [f for f in all_files if f.lower() not in ignore_files]
    candidate_files.sort()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    mode_text = f"PILIH FILE CSV TARGET - {judul_mode}" if judul_mode else "PILIH FILE CSV TARGET"
    print(f"║  {mode_text:<56}║")
    print("╠══════════════════════════════════════════════════════════╣")

    if candidate_files:
        print("║  File CSV yang terdeteksi di folder:                     ║")
        for i, f_name in enumerate(candidate_files, start=1):
            count_str = ""
            try:
                with open(f_name, "r", encoding="utf-8-sig", errors="ignore") as f:
                    lines = sum(1 for line in f if line.strip())
                    data_count = max(0, lines - 1)
                    count_str = f"({data_count} data)"
            except Exception:
                pass
            item_str = f"[{i}] {f_name}"
            print(f"║   {item_str:<32} {count_str:>20} ║")
    else:
        print("║  (Tidak ada file CSV input terdeteksi di folder)        ║")

    print("║                                                          ║")
    print("║   [0] Batal / Keluar                                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    while True:
        prompt_text = f"   Pilih nomor [1-{len(candidate_files)}] atau ketik nama file: " if candidate_files else "   Ketik nama file CSV (atau 0 untuk batal): "
        pilihan = input(prompt_text).strip()

        if not pilihan or pilihan == "0" or pilihan.lower() in ["batal", "exit", "keluar"]:
            print("[*] Pemilihan file dibatalkan.")
            return None

        # Jika user memasukkan angka pilihan dari daftar
        if pilihan.isdigit() and candidate_files:
            idx = int(pilihan)
            if 1 <= idx <= len(candidate_files):
                selected = candidate_files[idx - 1]
                print(f"[✓] File dipilih: {selected}\n")
                return selected
            else:
                print(f"   [⚠️] Pilihan nomor {idx} di luar jangkauan (1-{len(candidate_files)}).")
                continue

        # Jika user mengetik nama file secara langsung
        custom_name = pilihan
        if not custom_name.lower().endswith(".csv") and not os.path.exists(custom_name):
            if os.path.exists(custom_name + ".csv"):
                custom_name = custom_name + ".csv"

        if os.path.exists(custom_name):
            print(f"[✓] File dipilih: {custom_name}\n")
            return custom_name
        else:
            print(f"   [⚠️] File '{custom_name}' tidak ditemukan di folder. Silakan coba lagi.")


def detect_delimiter(filepath):
    """Mendeteksi pemisah kolom CSV (; atau ,) secara otomatis berdasarkan isi file."""
    try:
        with open(filepath, mode="r", encoding="utf-8-sig", errors="ignore") as f:
            sample = f.read(4096)
            if ";" in sample and sample.count(";") >= sample.count(","):
                return ";"
            elif "," in sample:
                return ","
    except Exception:
        pass
    return CSV_DELIMITER


def append_to_log(filepath, data_dict):
    """Menyimpan catatan hasil ke file CSV log."""
    file_exists = os.path.exists(filepath)
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data_dict.keys()), delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_dict)
    except Exception as e:
        print(f"[!] Gagal mencatat ke log '{filepath}': {e}")


def validate_and_fix_customer_data(idpel, no_meter, nik, line_no=None):
    """
    Memvalidasi dan otomatis membetulkan posisi jika IDPEL, No Meter, atau NIK tertukar.
    Karakteristik standar:
      - NIK      : Tepat 16 digit angka murni
      - IDPEL    : Tepat 12 digit angka murni
      - No. Meter: Biasanya 11 digit (token) atau 6-10 digit / '0' (pasca). Tidak pernah 16 digit.
    """
    clean_id = re.sub(r'\D', '', str(idpel).strip())
    clean_meter = re.sub(r'\D', '', str(no_meter).strip())
    clean_nik = re.sub(r'\D', '', str(nik).strip())

    swapped = False
    prefix = f"Baris {line_no}: " if line_no else ""

    # Kasus 1: No. Meter dan NIK tertukar (Meter 16 digit, NIK bukan 16 digit)
    if len(clean_meter) == 16 and len(clean_nik) != 16:
        print(f"[⚠️ AUTO-FIX] {prefix}No. Meter ('{no_meter}') dan NIK ('{nik}') terdeteksi TERTUKAR! Posisi otomatis dibenarkan.")
        clean_nik, clean_meter = clean_meter, clean_nik
        swapped = True

    # Kasus 2: IDPEL dan NIK tertukar (IDPEL 16 digit, NIK 12 digit)
    elif len(clean_id) == 16 and len(clean_nik) == 12:
        print(f"[⚠️ AUTO-FIX] {prefix}IDPEL ('{idpel}') dan NIK ('{nik}') terdeteksi TERTUKAR! Posisi otomatis dibenarkan.")
        clean_id, clean_nik = clean_nik, clean_id
        swapped = True

    # Kasus 3: IDPEL dan No. Meter tertukar (IDPEL 11 digit, Meter 12 digit)
    elif len(clean_id) == 11 and len(clean_meter) == 12:
        print(f"[⚠️ AUTO-FIX] {prefix}IDPEL ('{idpel}') dan No. Meter ('{no_meter}') terdeteksi TERTUKAR! Posisi otomatis dibenarkan.")
        clean_id, clean_meter = clean_meter, clean_id
        swapped = True

    final_id = clean_id if clean_id else str(idpel).strip()
    final_meter = clean_meter if clean_meter else str(no_meter).strip()
    final_nik = clean_nik if clean_nik else str(nik).strip()

    return final_id, final_meter, final_nik, swapped


def load_input_data(filepath):
    """Membaca file CSV input dan mengembalikan list data (mendukung 2 kolom IDPEL/NIK atau 3 kolom IDPEL/Meter/NIK dengan auto-fix data tertukar)."""
    if not os.path.exists(filepath):
        print(f"[X] File '{filepath}' tidak ditemukan!")
        return []
    
    rows = []
    delim = detect_delimiter(filepath)
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=delim)
            header = next(reader, None)
            
            col_idpel = 0
            col_meter = None
            col_daya = None
            col_nik = 1
            
            if header:
                h_lower = [str(col).strip().lower() for col in header]
                for i, col_name in enumerate(h_lower):
                    if "meter" in col_name:
                        col_meter = i
                    elif "daya" in col_name or "tarif" in col_name:
                        col_daya = i
                    elif "nik" in col_name:
                        col_nik = i
                    elif "id" in col_name or "pelanggan" in col_name:
                        col_idpel = i
            
            if col_meter is not None and col_nik == 1 and col_meter == 1:
                col_nik = 2

            auto_fix_count = 0
            for line_no, r in enumerate(reader, start=2):
                if not r or len(r) < 2:
                    continue
                idpel = str(r[col_idpel]).strip() if col_idpel < len(r) else ""
                no_meter = str(r[col_meter]).strip() if (col_meter is not None and col_meter < len(r)) else ""
                nik_baru = str(r[col_nik]).strip() if col_nik < len(r) else ""
                daya_val = str(r[col_daya]).strip() if (col_daya is not None and col_daya < len(r)) else ""
                
                # Validasi dan auto-fix jika ada kolom yang posisinya tertukar
                idpel, no_meter, nik_baru, was_swapped = validate_and_fix_customer_data(
                    idpel, no_meter, nik_baru, line_no=line_no
                )
                if was_swapped:
                    auto_fix_count += 1

                if idpel and nik_baru:
                    item_dict = {
                        "id_pelanggan": idpel,
                        "NIK_Perbaikan": nik_baru
                    }
                    if no_meter:
                        item_dict["no_meter"] = no_meter
                    if daya_val:
                        item_dict["daya"] = daya_val
                    rows.append(item_dict)

            if auto_fix_count > 0:
                print(f"[✓] Terdeteksi & dibetulkan otomatis {auto_fix_count} data yang posisinya tertukar!")
        print(f"[OK] Berhasil memuat {len(rows)} data dari '{filepath}' (delimiter: '{delim}')")
        return rows
    except Exception as e:
        print(f"[X] Gagal membaca CSV '{filepath}': {e}")
        return []


def remove_idpel_from_input_csv(filepath, idpel_done):
    """Menghapus baris IDPEL yang sudah sukses dari file CSV input agar tidak diproses ulang."""
    if not filepath or not os.path.exists(filepath) or not idpel_done:
        return
    delim = detect_delimiter(filepath)
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=delim)
            header = next(reader, None)
            all_rows = list(reader)
        
        col_idpel = 0
        if header:
            for i, h in enumerate(header):
                if "id" in h.lower() or "pelanggan" in h.lower():
                    col_idpel = i
                    break

        remaining = [r for r in all_rows if r and len(r) > col_idpel and r[col_idpel].strip() != idpel_done.strip()]
        
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=delim)
            if header:
                writer.writerow(header)
            writer.writerows(remaining)
        print(f"[*] IDPEL {idpel_done} dihapus dari '{filepath}' (Sisa: {len(remaining)} data)")
    except Exception as e:
        print(f"[!] Gagal memperbarui file input '{filepath}': {e}")
