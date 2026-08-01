import csv
import os
import time
import uiautomator2 as u2

# ================== KONFIGURASI UTAMA ==================
DEVICE_ID = "RR8N60CWMLZ"  # Serial HP/Emulator Anda
CSV_INPUT = "IDPELTMG.csv"         # File data utama
CSV_DELIMITER = ";"              # Delimiter CSV

# Nama file output hasil pemilahan
OUT_BELUM_TERCATAT = "IDPELTMG_BELUM_TERCATAT.csv"
OUT_SUDAH_TERCATAT = "IDPELTMG_SUDAH_TERCATAT.csv"
OUT_TIDAK_DITEMUKAN = "IDPELTMG_TIDAK_DITEMUKAN.csv"
OUT_GAGAL_CEK = "IDPELTMG_GAGAL_CEK.csv"
# =======================================================

def scroll_down(d, duration=0.3):
    width, height = d.window_size()
    x = width // 2
    y_start = int(height * 0.7)
    y_end = int(height * 0.2)
    d.swipe(x, y_start, x, y_end, duration=duration)

def scroll_up(d, duration=0.3):
    width, height = d.window_size()
    x = width // 2
    y_start = int(height * 0.2)
    y_end = int(height * 0.7)
    d.swipe(x, y_start, x, y_end, duration=duration)

def append_to_csv(filepath, row, fieldnames):
    file_exists = os.path.exists(filepath)
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_input_csv(filepath):
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            return reader.fieldnames, list(reader)
    except Exception as e:
        print(f"[✗] Gagal membaca file CSV '{filepath}': {e}")
        return None, []

def main():
    print("==========================================================")
    print("      SKRIP PEMILAHAN IDPEL FASIH BPS (REAL-TIME)        ")
    print("==========================================================")

    # 1. Load Data Input
    fieldnames, rows = load_input_csv(CSV_INPUT)
    if not rows:
        print("[✗] Data input kosong atau tidak ditemukan. Program dihentikan.")
        return

    print(f"[✓] Berhasil memuat {len(rows)} baris data dari '{CSV_INPUT}'")
    
    # 2. Hubungkan ke Device
    print(f"[*] Menghubungkan ke perangkat Android: {DEVICE_ID}...")
    try:
        d = u2.connect(DEVICE_ID)
        device_info = d.info
        print(f"[✓] Terhubung ke {device_info.get('brand')} {device_info.get('model')} ({d.window_size()})")
    except Exception as e:
        print(f"[✗] Gagal terhubung ke device: {e}")
        return

    print("\n[⚠️] PETUNJUK: Posisikan layar HP/Emulator pada Form Input ID Pelanggan sebelum memulai.")
    print("[*] Skrip akan mencari field 'textfield-cl-3-input' secara otomatis...")
    
    # Deteksi field awal
    idpel_input = d(resourceId="textfield-cl-3-input")
    if not idpel_input.exists:
        print("[!] Field input ID Pelanggan tidak terdeteksi langsung.")
        print("[*] Menunggu Anda memposisikan layar secara manual...")
        while not idpel_input.exists:
            time.sleep(2.0)
            idpel_input = d(resourceId="textfield-cl-3-input")
        print("[✓] Field input ID Pelanggan ditemukan! Memulai pemrosesan...")

    # Looping baris data
    total = len(rows)
    for idx, row in enumerate(rows, start=1):
        idpel = row.get('IDPEL', '').strip()
        if not idpel:
            print(f"[{idx}/{total}] Kolom IDPEL kosong di baris ini. Dilewati.")
            continue

        print(f"\n[{idx}/{total}] Memeriksa IDPEL: {idpel} ...")
        
        # 1. Bersihkan dan Isi Field Input
        try:
            idpel_input.clear_text()
            idpel_input.set_text(idpel)
            
            # Sembunyikan keyboard virtual agar tidak menutupi tombol
            d.press("back")
            time.sleep(0.5)
        except Exception as e:
            print(f"    [✗] Gagal berinteraksi dengan field input: {e}")
            append_to_csv(OUT_GAGAL_CEK, row, fieldnames)
            continue

        # 2. Klik Cek ID Pelanggan (2 kali)
        btn_check = d(text="Cek ID Pelanggan")
        if not btn_check.exists:
            print("    [✗] Tombol 'Cek ID Pelanggan' tidak ditemukan di layar.")
            append_to_csv(OUT_GAGAL_CEK, row, fieldnames)
            continue

        btn_check.click()
        time.sleep(0.5)
        btn_check.click()

        # 3. Tunggu respon server (max 15 detik)
        print("    [*] Menunggu respon dari server...")
        verified = False
        status_kategori = None

        for wait in range(15):
            time.sleep(1.0)
            xml_chk = d.dump_hierarchy()
            
            # Cek status langsung tanpa scroll
            if "DITEMUKAN DAN BELUM TERCATAT" in xml_chk:
                status_kategori = "BELUM_TERCATAT"
                verified = True
                break
            elif "DITEMUKAN DAN SUDAH TERCATAT" in xml_chk or "sudah terdaftar di FASIH" in xml_chk:
                status_kategori = "SUDAH_TERCATAT"
                verified = True
                break
            elif "TIDAK DITEMUKAN" in xml_chk or "TIDAK TERDAFTAR" in xml_chk:
                status_kategori = "TIDAK_DITEMUKAN"
                verified = True
                break

        if not verified:
            print("    [⚠️] Waktu tunggu server habis (Timeout 15s). Dimasukkan ke daftar Gagal Cek.")
            append_to_csv(OUT_GAGAL_CEK, row, fieldnames)
            continue

        # 4. Catat ke File CSV yang Sesuai
        if status_kategori == "BELUM_TERCATAT":
            print(f"    [✓] HASIL: BELUM TERCATAT (Disimpan ke '{OUT_BELUM_TERCATAT}')")
            append_to_csv(OUT_BELUM_TERCATAT, row, fieldnames)
        elif status_kategori == "SUDAH_TERCATAT":
            print(f"    [✓] HASIL: SUDAH TERCATAT (Disimpan ke '{OUT_SUDAH_TERCATAT}')")
            append_to_csv(OUT_SUDAH_TERCATAT, row, fieldnames)
        elif status_kategori == "TIDAK_DITEMUKAN":
            print(f"    [✓] HASIL: TIDAK DITEMUKAN (Disimpan ke '{OUT_TIDAK_DITEMUKAN}')")
            append_to_csv(OUT_TIDAK_DITEMUKAN, row, fieldnames)
        else:
            print(f"    [⚠️] HASIL: TIDAK DIKENAL/ERROR (Disimpan ke '{OUT_GAGAL_CEK}')")
            append_to_csv(OUT_GAGAL_CEK, row, fieldnames)

        time.sleep(1.0)  # Jeda kecil antar pengecekan

    print("\n==========================================================")
    print("           PENGOLAHAN DATA SELESAI DENGAN SUKSES!         ")
    print("==========================================================")
    print(f" - Belum Tercatat: Check file '{OUT_BELUM_TERCATAT}'")
    print(f" - Sudah Tercatat: Check file '{OUT_SUDAH_TERCATAT}'")
    print(f" - Tidak Ditemukan: Check file '{OUT_TIDAK_DITEMUKAN}'")
    print(f" - Gagal/Timeout: Check file '{OUT_GAGAL_CEK}'")
    print("==========================================================")

if __name__ == "__main__":
    main()
