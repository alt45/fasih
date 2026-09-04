import argparse
import csv
import os
import subprocess
import sys
import time

# Pastikan output utf-8 aman di terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uiautomator2 as u2

# ================== KONFIGURASI UTAMA ==================
DEVICE_ID = ""                    # Kosongkan untuk auto-detect perangkat aktif
CSV_INPUT = ""                    # Kosongkan untuk memilih file secara interaktif
CSV_DELIMITER = ";"               # Pemisah kolom CSV

OUT_SUKSES = "SUKSES_UPDATE_NIK.csv"
OUT_TIDAK_DITEMUKAN = "IDPEL_TIDAK_DITEMUKAN.csv"
OUT_NIK_TIDAK_DITEMUKAN = "NIK_TIDAK_DITEMUKAN.csv"
OUT_GAGAL = "NIK_GAGAL_UPDATE.csv"
# =======================================================


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


def load_input_data(filepath):
    """Membaca file CSV input dan mengembalikan list data (mendukung 2 kolom IDPEL/NIK atau 3 kolom IDPEL/Meter/NIK)."""
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
            col_nik = 1
            
            if header:
                h_lower = [str(col).strip().lower() for col in header]
                for i, col_name in enumerate(h_lower):
                    if "meter" in col_name:
                        col_meter = i
                    elif "nik" in col_name:
                        col_nik = i
                    elif "id" in col_name or "pelanggan" in col_name:
                        col_idpel = i
            
            if col_meter is not None and col_nik == 1 and col_meter == 1:
                col_nik = 2

            for line_no, r in enumerate(reader, start=2):
                if not r or len(r) < 2:
                    continue
                idpel = str(r[col_idpel]).strip() if col_idpel < len(r) else ""
                no_meter = str(r[col_meter]).strip() if (col_meter is not None and col_meter < len(r)) else ""
                nik_baru = str(r[col_nik]).strip() if col_nik < len(r) else ""
                
                if idpel and nik_baru:
                    item_dict = {
                        "id_pelanggan": idpel,
                        "NIK_Perbaikan": nik_baru
                    }
                    if no_meter:
                        item_dict["no_meter"] = no_meter
                    rows.append(item_dict)
        print(f"[OK] Berhasil memuat {len(rows)} data dari '{filepath}' (delimiter: '{delim}')")
        return rows
    except Exception as e:
        print(f"[X] Gagal membaca CSV '{filepath}': {e}")
        return []


def remove_idpel_from_input_csv(filepath, idpel_done):
    """Menghapus baris IDPEL yang sudah sukses dari file CSV input agar tidak diproses ulang."""
    if not os.path.exists(filepath) or not idpel_done:
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


def is_keyboard_shown(d):
    """Mendeteksi apakah virtual keyboard sedang aktif."""
    try:
        res, _ = d.shell("dumpsys input_method")
        return "mInputShown=true" in res or "mInputShown=True" in res
    except Exception:
        return False


def hide_keyboard(d):
    """Menutup virtual keyboard dengan aman jika sedang terbuka."""
    if is_keyboard_shown(d):
        d.press("back")
        time.sleep(0.6)


def scroll_up(d, duration=0.3):
    """Menggulir layar ke atas (gerakan jari dari atas ke bawah)."""
    try:
        width, height = d.window_size()
        x = width // 2
        y_start = int(height * 0.2)
        y_end = int(height * 0.7)
        d.swipe(x, y_start, x, y_end, duration=duration)
    except Exception as e:
        print(f"[!] Gagal scroll up: {e}")


def scroll_down(d, duration=0.3):
    """Menggulir layar ke bawah (gerakan jari dari bawah ke atas)."""
    try:
        width, height = d.window_size()
        x = width // 2
        y_start = int(height * 0.7)
        y_end = int(height * 0.2)
        d.swipe(x, y_start, x, y_end, duration=duration)
    except Exception as e:
        print(f"[!] Gagal scroll down: {e}")


def swipe_up_to_reveal(d, duration=0.4):
    """Menggeser tampilan ke atas (gerakan jari dari 75% ke 25% layar) agar konten bawah terlihat."""
    try:
        width, height = d.window_size()
        x = width // 2
        y_start = int(height * 0.75)
        y_end = int(height * 0.25)
        d.swipe(x, y_start, x, y_end, duration=duration)
    except Exception as e:
        print(f"[!] Gagal swipe up to reveal: {e}")


def scroll_down_small(d, duration=0.3):
    """Menggulir layar ke bawah sedikit (sekitar 15-20% layar) agar konten bawah terlihat."""
    try:
        width, height = d.window_size()
        x = width // 2
        y_start = int(height * 0.65)
        y_end = int(height * 0.45)
        d.swipe(x, y_start, x, y_end, duration=duration)
    except Exception as e:
        print(f"[!] Gagal scroll down small: {e}")


def is_nik_present_on_screen(d):
    """Mengecek apakah kata atau elemen NIK sudah muncul di layar (menandakan BLOK II aktif)."""
    try:
        # Cek tombol Cek NIK
        if d(text="Cek NIK").exists or d(textContains="Cek NIK").exists:
            return True
        # Cek resource ID r202 (field NIK)
        if d(resourceId="r202").exists:
            return True
        # Cek teks NIK saat Cek ID Pelanggan sudah tidak ada
        if not d(text="Cek ID Pelanggan").exists:
            if d(textContains="NIK").exists or d(text="BERIKUTNYA BLOK III").exists:
                return True
        # Cek hierarchy jika selector belum siap
        xml_dump = d.dump_hierarchy()
        if ("Cek NIK" in xml_dump or "r202" in xml_dump) and "Cek ID Pelanggan" not in xml_dump:
            return True
    except Exception:
        pass
    return False


def back_to_assignment_list(d):
    """Mengembalikan layar ke halaman depan 'Daftar Assignment' secara aman jika terjadi kendala."""
    print("[*] Melakukan recovery kembali ke halaman Daftar Assignment...")
    hide_keyboard(d)
    
    # Cek apakah ada tombol Batal pada dialog aktif
    btn_batal = d(text="Batal")
    if btn_batal.exists:
        btn_batal.click()
        time.sleep(1.0)

    # Cek tombol keluar form
    for _ in range(5):
        # Jika ada loading progress, tunggu sebentar
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            time.sleep(2.0)
            continue

        # Jika sudah di halaman Daftar Assignment
        if d(text="Daftar Assignment").exists or d(text="Search:").exists:
            print("[OK] Sudah berada di halaman Daftar Assignment.")
            return True
        
        # Jika berada di Halaman Upload, klik tombol back_button
        if d(text="Halaman Upload").exists or d(resourceId="id.go.bpsfasih:id/back_button").exists:
            btn_back = d(resourceId="id.go.bpsfasih:id/back_button")
            if btn_back.exists:
                btn_back.click()
            else:
                d.press("back")
            time.sleep(2.0)
            continue

        d.press("back")
        time.sleep(1.0)
        
        # Jika muncul konfirmasi keluar (IYA/YA)
        btn_confirm = d(text="IYA")
        if not btn_confirm.exists:
            btn_confirm = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
        if not btn_confirm.exists:
            btn_confirm = d(text="YA")
        if btn_confirm.exists:
            btn_confirm.click()
            time.sleep(1.5)
            # Tunggu card_progress selesai jika ada
            for _ in range(10):
                if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                    time.sleep(1.0)
                else:
                    break
            
    return d(text="Daftar Assignment").exists or d(text="Search:").exists


def clear_search_box(d):
    """Membersihkan isi kotak pencarian Search di Daftar Assignment."""
    try:
        search_input = d(className="android.widget.EditText")
        if search_input.exists:
            search_input.set_text("")
            hide_keyboard(d)
            time.sleep(1.0)
    except Exception:
        pass


def get_connected_devices():
    """Mengambil daftar perangkat Android yang terhubung via ADB beserta model/nama perangkat."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        devices = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model = ""
                product = ""
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split("model:", 1)[1].replace("_", " ")
                    elif p.startswith("product:"):
                        product = p.split("product:", 1)[1].replace("_", " ")
                dev_name = model or product or "Perangkat Android"
                devices.append({"serial": serial, "name": dev_name})
        return devices
    except Exception as e:
        print(f"[!] Gagal mengecek adb devices: {e}")
        return []


def pilih_perangkat():
    """
    Menampilkan menu interaktif pemilihan perangkat Android jika terdeteksi lebih dari 1 perangkat.
    Mengembalikan serial perangkat yang dipilih, atau None jika dibatalkan/kosong.
    """
    devices = get_connected_devices()
    if not devices:
        print("[!] Tidak ada perangkat yang terdeteksi di 'adb devices'.")
        print("    Pastikan kabel USB terpasang baik dan HP dalam mode USB Debugging aktif.")
        return None
    elif len(devices) == 1:
        chosen = devices[0]
        print(f"[✓] Menggunakan perangkat: {chosen['name']} (Serial: {chosen['serial']})")
        return chosen["serial"]

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║             PILIH PERANGKAT ANDROID TARGET               ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Terdeteksi {len(devices)} perangkat Android aktif:                  ║")
    for i, dev in enumerate(devices, start=1):
        dev_label = f"[{i}] {dev['name']} ({dev['serial']})"
        print(f"║   {dev_label:<54} ║")
    print("║                                                          ║")
    print("║   [0] Batal / Keluar                                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    while True:
        pilihan = input(f"   Pilih perangkat [1-{len(devices)}] atau 0 untuk batal: ").strip()
        if not pilihan or pilihan == "0" or pilihan.lower() in ["batal", "exit", "keluar"]:
            print("[*] Pemilihan perangkat dibatalkan.")
            return None
        if pilihan.isdigit() and 1 <= int(pilihan) <= len(devices):
            chosen = devices[int(pilihan) - 1]
            print(f"[✓] Perangkat dipilih: {chosen['name']} (Serial: {chosen['serial']})\n")
            return chosen["serial"]
        print("   [⚠️] Pilihan tidak valid, silakan coba lagi.")


def connect_device(target_device=None):
    """
    Menghubungkan ke perangkat Android via uiautomator2.
    """
    try:
        chosen_serial = target_device.strip() if target_device else None

        if not chosen_serial:
            chosen_serial = pilih_perangkat()
            if not chosen_serial:
                return None
        else:
            print(f"[*] Menghubungkan ke perangkat target: {chosen_serial}...")

        d = u2.connect(chosen_serial)
        info = d.info
        print(f"[OK] Berhasil terhubung ke: {info.get('brand', '')} {info.get('model', '')} (Serial: {d.serial})")
        print(f"     Resolusi Layar: {d.window_size()}")
        
        global DEVICE_ID
        DEVICE_ID = d.serial
        return d
    except Exception as e:
        print(f"[X] Gagal terhubung ke Android: {e}")
        print("    Tips penanganan:")
        print("    1. Pastikan kabel USB terpasang baik dan HP dalam mode USB Debugging aktif.")
        print("    2. Ketik 'adb devices' di terminal untuk memastikan serial HP terdaftar.")
        return None


def process_update_nik(d, row_data, csv_input_path=CSV_INPUT):
    """
    Memproses satu baris data IDPEL:
    Cari IDPEL -> Buka -> BLOK I Cek IDPEL -> BLOK II Ganti NIK & Cek NIK -> Kirim
    """
    idpel = row_data["id_pelanggan"]
    nik_baru = row_data["NIK_Perbaikan"]
    
    print(f"\n========================================================")
    print(f"[*] MEMPROSES IDPEL : {idpel}")
    print(f"    NIK BARU TARGET : {nik_baru}")
    print(f"========================================================")

    # 1. Pastikan di Halaman Daftar Assignment
    if not (d(text="Daftar Assignment").exists or d(text="Search:").exists):
        if not back_to_assignment_list(d):
            raise Exception("Gagal memposisikan layar ke 'Daftar Assignment'.")

    # 2. Input IDPEL ke kotak Search
    print("[*] Menginput IDPEL ke kotak pencarian...")
    search_input = d(className="android.widget.EditText")
    if not search_input.exists:
        raise Exception("Field input pencarian (Search:) tidak ditemukan.")
    
    search_input.click()
    time.sleep(0.3)
    search_input.set_text("")
    time.sleep(0.3)
    search_input.set_text(idpel)
    time.sleep(0.5)
    hide_keyboard(d)
    
    # Tunggu tabel memfilter hasil (1-2 detik)
    time.sleep(2.0)

    # 3. Cek apakah data ditemukan di tabel
    xml_table = d.dump_hierarchy()
    if idpel not in xml_table or "Showing 0 to 0 of 0 entries" in xml_table or "No matching records" in xml_table:
        print(f"[!] IDPEL {idpel} TIDAK DITEMUKAN di tabel assignment! Melewati...")
        append_to_log(OUT_TIDAK_DITEMUKAN, {
            "id_pelanggan": idpel,
            "NIK_Perbaikan": nik_baru,
            "keterangan": "Tidak ditemukan di tabel assignment"
        })
        remove_idpel_from_input_csv(csv_input_path, idpel)
        clear_search_box(d)
        return "IDPEL_NOT_FOUND"

    print(f"[OK] Data IDPEL {idpel} ditemukan di tabel!")

    # 4. Klik tanda '+' untuk expand detail baris (ikon '+' berada di sisi kiri sel kolom pertama)
    print("[*] Meng-expand baris tabel (klik '+')...")
    expanded = False
    for attempt in range(4):
        btn_plus = d(textContains="+")
        if btn_plus.exists:
            try:
                b = btn_plus.bounds()
                x_plus = b[0] + 25  # Sentuh sisi kiri sel tepat di ikon '+'
                y_plus = (b[1] + b[3]) // 2
                d.click(x_plus, y_plus)
            except Exception:
                btn_plus.click()
        else:
            d.click(57, 886)

        # Tunggu sampai tombol Aksi muncul
        for _ in range(6):
            time.sleep(0.5)
            if d(className="android.widget.Button", text="Aksi").exists or d(text="Aksi").exists:
                expanded = True
                break
        if expanded:
            print("[OK] Baris tabel berhasil diexpand! Tombol 'Aksi' tersedia.")
            break
        print(f"[*] Tombol Aksi belum tampak (percobaan {attempt+1}), mencoba klik '+' lagi...")

    # 5. Klik tombol 'Aksi'
    print("[*] Mengklik tombol 'Aksi'...")
    btn_aksi = d(className="android.widget.Button", text="Aksi")
    if not btn_aksi.exists:
        btn_aksi = d(text="Aksi")
    if btn_aksi.exists:
        btn_aksi.click()
    else:
        # Fallback koordinat center tombol Aksi yang terverifikasi
        d.click(258, 1325)

    # 6. Tunggu dan klik 'BUKA' pada dialog
    print("[*] Menunggu menu dialog 'BUKA'...")
    btn_buka = None
    for _ in range(8):
        time.sleep(0.5)
        if d(resourceId="id.go.bpsfasih:id/openAssignment_b").exists:
            btn_buka = d(resourceId="id.go.bpsfasih:id/openAssignment_b")
            break
        elif d(text="BUKA").exists:
            btn_buka = d(text="BUKA")
            break

    if not btn_buka or not btn_buka.exists:
        # Percobaan ulang klik Aksi jika dialog belum terbuka
        btn_aksi = d(className="android.widget.Button", text="Aksi")
        if btn_aksi.exists:
            btn_aksi.click()
            time.sleep(1.5)
            if d(resourceId="id.go.bpsfasih:id/openAssignment_b").exists:
                btn_buka = d(resourceId="id.go.bpsfasih:id/openAssignment_b")
            elif d(text="BUKA").exists:
                btn_buka = d(text="BUKA")

    if not btn_buka or not btn_buka.exists:
        raise Exception("Tombol 'BUKA' tidak ditemukan di menu dialog Aksi.")
    
    print("[OK] Tombol 'BUKA' ditemukan! Mengklik 'BUKA'...")
    btn_buka.click()
    time.sleep(1.5)

    # 7. Klik 'YA' pada konfirmasi buka assignment
    btn_ya_buka = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
    if not btn_ya_buka.exists:
        btn_ya_buka = d(text="YA")
    if not btn_ya_buka.exists:
        d.click(519, 1385)  # Fallback koordinat center YA
    else:
        btn_ya_buka.click()
    
    print("[*] Menunggu loading kuesioner selesai (card_progress)...")
    for _ in range(30):
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            time.sleep(0.3)
        else:
            break
    time.sleep(0.5)

    # 8. BLOK I: Verifikasi halaman terbuka, Geser layar cepat, & Klik 'Cek ID Pelanggan'
    print("[*] Menunggu halaman BLOK I termuat...")
    for _ in range(20):
        if d(text="Cek ID Pelanggan").exists or d(text="BERIKUTNYA BLOK II").exists or d(textContains="ID pelanggan").exists or d(textContains="BLOK I").exists:
            break
        time.sleep(0.3)

    # Scroll kecil bertahap sampai tombol 'Cek ID Pelanggan' terlihat
    btn_cek_idpel = d(text="Cek ID Pelanggan")
    for attempt in range(1, 6):
        if btn_cek_idpel.exists:
            break
        print(f"[*] BLOK I: Menggeser layar sedikit (percobaan {attempt}/5)...")
        scroll_down_small(d, duration=0.35)
        time.sleep(0.5)
        btn_cek_idpel = d(text="Cek ID Pelanggan")

    if not btn_cek_idpel or not btn_cek_idpel.exists:
        raise Exception("Gagal masuk ke BLOK I / Tombol 'Cek ID Pelanggan' tidak ditemukan.")

    print("[*] BLOK I: Mengklik 'Cek ID Pelanggan'...")
    btn_cek_idpel.click()
    
    # Tunggu respon verifikasi ID Pelanggan dari server (card_progress)
    print("[*] Menunggu respon Cek ID Pelanggan...")
    for _ in range(25):
        time.sleep(0.3)
        if not d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            break
    hide_keyboard(d)
    time.sleep(0.4)

    # 9. Klik 'BERIKUTNYA BLOK II' (Hanya klik 1x -> Cek kata NIK di layar -> Jika belum ada, klik lagi)
    print("[*] Berpindah ke BLOK II...")
    in_blok2 = False
    
    for attempt in range(1, 8):
        # 1. Cek terlebih dahulu apakah kata NIK sudah muncul di layar
        if is_nik_present_on_screen(d):
            print(f"[OK] Kata/elemen NIK sudah terdeteksi di layar (Percobaan {attempt})! Masuk ke BLOK II.")
            in_blok2 = True
            break

        print(f"[*] Percobaan {attempt}/7: Mengklik tombol 'BERIKUTNYA BLOK II' (1 KALI)...")
        hide_keyboard(d)

        # Cari tombol BERIKUTNYA BLOK II
        btn_next_b2 = d(resourceId="fasih-form-nav-next-button")
        if not btn_next_b2.exists:
            btn_next_b2 = d(text="BERIKUTNYA BLOK II")
        if not btn_next_b2.exists:
            btn_next_b2 = d(textContains="BERIKUTNYA")

        # Jika tombol navigasi belum terlihat di layar, scroll sedikit ke bawah
        if not btn_next_b2.exists:
            print("[*] Tombol belum tampak, mencoba scroll ke bawah...")
            scroll_down_small(d)
            time.sleep(0.8)
            btn_next_b2 = d(resourceId="fasih-form-nav-next-button")
            if not btn_next_b2.exists:
                btn_next_b2 = d(text="BERIKUTNYA BLOK II")

        # KLIK HANYA 1 KALI (TIDAK DOUBLE CLICK)
        if btn_next_b2.exists:
            try:
                cx, cy = btn_next_b2.center()
                print(f"[*] Klik 1x sentuhan fisik tombol di ({cx}, {cy})...")
                d.click(cx, cy)
            except Exception:
                print(f"[*] Klik 1x logis tombol BERIKUTNYA...")
                btn_next_b2.click()
        else:
            # Fallback koordinat adaptif persentase layar (sudut kanan-bawah area navigasi)
            w, h = d.window_size()
            fb_x = int(w * 0.75)
            fb_y = int(h * 0.94)
            print(f"[*] Fallback: Klik 1x di area navigasi ({fb_x}, {fb_y})...")
            d.click(fb_x, fb_y)

        # 2. Tunggu respon dan cek apakah kata/field 'NIK' sudah muncul di layar
        print("[*] Memeriksa apakah kata 'NIK' sudah muncul di layar...")
        for wait_t in range(4):
            time.sleep(1.0)
            if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                continue
            if is_nik_present_on_screen(d):
                print(f"[OK] Kata 'NIK' terdeteksi di layar pada detik ke-{wait_t+1}! Berhasil masuk ke BLOK II.")
                in_blok2 = True
                break

        if in_blok2:
            break
        else:
            print("[!] Kata 'NIK' belum muncul di layar. Bersiap klik tombol Berikutnya lagi...")

    if not in_blok2:
        if is_nik_present_on_screen(d):
            print("[OK] Kata 'NIK' terkonfirmasi aktif di layar.")
            in_blok2 = True
        else:
            raise Exception("Gagal berpindah ke BLOK II: kata 'NIK' tidak ditemukan setelah mencoba klik tombol Berikutnya.")

    # 10. BLOK II: Input NIK Baru & Klik 'Cek NIK'
    print("[*] BLOK II: Mencari field input NIK penghuni...")
    input_nik = None
    
    # Tunggu dan cari elemen input NIK dengan polling adaptif
    for poll in range(8):
        # 1. Coba resourceId r202 child EditText
        cand = d(resourceId="r202").child(className="android.widget.EditText")
        if cand.exists:
            input_nik = cand
            break
            
        # 2. Coba XPath di dalam r202
        cand_xp = d.xpath('//*[@resource-id="r202"]//android.widget.EditText')
        if cand_xp.exists:
            input_nik = cand_xp
            break

        # 3. Coba ID dinamis FormGear
        for dyn_id in ["textfield-cl-29-input", "textfield-cl-30-input", "textfield-cl-32-input", "textfield-cl-28-input"]:
            cand_dyn = d(resourceId=dyn_id)
            if cand_dyn.exists:
                input_nik = cand_dyn
                break
        if input_nik:
            break

        # 4. Coba ambil dari seluruh EditText di layar Blok II
        all_edits = d(className="android.widget.EditText")
        if all_edits.count >= 2:
            # Di BLOK II: index 0 biasanya Nama Penghuni (r201), index 1 adalah NIK (r202)
            input_nik = all_edits[1]
            break
        elif all_edits.count == 1:
            # Jika r201 di-collapse atau tidak tampak, bisa jadi input pertama adalah NIK
            res_n = all_edits[0].info.get("resourceName", "")
            if "r202" in res_n or "nik" in res_n.lower():
                input_nik = all_edits[0]
                break

        # Jika di percobaan ke-2 belum tampak, scroll down sedikit untuk memunculkan NIK ke viewport
        if poll in [2, 4]:
            print("[*] NIK belum tampak di viewport, mencoba scroll down sedikit...")
            scroll_down_small(d)

        time.sleep(1.0)

    if not input_nik or not input_nik.exists:
        raise Exception("Field input NIK di BLOK II tidak ditemukan.")

    print(f"[*] Membersihkan NIK lama dan mengetik NIK Baru (Instan): {nik_baru}...")
    input_nik.click()
    time.sleep(0.3)
    input_nik.clear_text()
    time.sleep(0.2)
    input_nik.set_text(nik_baru)
    time.sleep(0.5)

    # Tutup keyboard dan tunggu animasi keyboard selesai sepenuhnya
    hide_keyboard(d)
    time.sleep(1.0)

    # Klik tombol 'Cek NIK' secara fisik (sentuhan koordinat langsung)
    btn_cek_nik = d(text="Cek NIK")
    if not btn_cek_nik.exists:
        btn_cek_nik = d(resourceId="cek_nik").child(className="android.widget.Button")
    
    # Jika belum tampak, coba scroll down sedikit agar tombol Cek NIK terlihat
    if not btn_cek_nik.exists:
        scroll_down_small(d)
        time.sleep(1.0)
        btn_cek_nik = d(text="Cek NIK")
        if not btn_cek_nik.exists:
            btn_cek_nik = d(resourceId="cek_nik").child(className="android.widget.Button")

    if btn_cek_nik.exists:
        cx, cy = btn_cek_nik.center()
        print(f"[*] Mengklik sentuhan fisik pada tombol 'Cek NIK' di ({cx}, {cy})...")
        d.click(cx, cy)
        time.sleep(0.6)
        # Penegasan sentuhan kedua untuk memastikan event onclick WebView terpicu
        d.click(cx, cy)
    else:
        print("[*] Fallback koordinat fisik tombol 'Cek NIK' (99, 935)...")
        d.click(99, 935)
        time.sleep(0.6)
        d.click(99, 935)

    print("[*] Menunggu pemadanan NIK dari server (max 12 detik)...")
    nik_match_result = "UNKNOWN"
    for wait_sec in range(12):
        time.sleep(1.0)
        xml_chk = d.dump_hierarchy()
        if d(textContains="TIDAK DITEMUKAN").exists or "TIDAK DITEMUKAN" in xml_chk:
            nik_match_result = "TIDAK DITEMUKAN"
            print(f"[!] Respon pemadanan terdeteksi pada detik ke-{wait_sec+1}: NIK TIDAK DITEMUKAN!")
            break
        elif d(textContains="SESUAI").exists or "SESUAI" in xml_chk or "DITEMUKAN" in xml_chk:
            nik_match_result = "DITEMUKAN"
            print(f"[OK] Respon pemadanan terdeteksi pada detik ke-{wait_sec+1}: NIK DITEMUKAN / SESUAI!")
            break

    # Jika NIK TIDAK DITEMUKAN saat pemadanan:
    if nik_match_result == "TIDAK DITEMUKAN":
        print(f"[!] Pemadanan Gagal: NIK {nik_baru} untuk IDPEL {idpel} TIDAK DITEMUKAN.")
        print(f"[*] Mencatat ke '{OUT_NIK_TIDAK_DITEMUKAN}' dan menghapus dari '{csv_input_path}'...")
        append_to_log(OUT_NIK_TIDAK_DITEMUKAN, {
            "id_pelanggan": idpel,
            "NIK_Perbaikan": nik_baru,
            "keterangan": "NIK Tidak Ditemukan saat pemadanan",
            "waktu": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        remove_idpel_from_input_csv(csv_input_path, idpel)
        print("[*] Membatalkan pengisian form dan kembali ke halaman Daftar Assignment...")
        back_to_assignment_list(d)
        clear_search_box(d)
        return "NIK_NOT_FOUND"

    # 11. Klik 'Kirim' di Toolbar Kanan Atas
    print("[*] Menyimpan perubahan: Mengklik tombol 'Kirim' di toolbar...")
    btn_kirim_top = d(className="android.widget.Button", text="Kirim")
    if not btn_kirim_top.exists:
        d.click(596, 124)  # Fallback koordinat tombol Kirim kanan atas
    else:
        btn_kirim_top.click()
    time.sleep(3.0)

    # 12. Pop-up Cek Galat
    btn_galat = d(textContains="GALAT")
    if btn_galat.exists:
        txt_galat = btn_galat.info.get("text", "")
        print(f"[*] Status Galat terdeteksi: '{txt_galat}'")
        if "GALAT 0" not in txt_galat:
            print(f"[!] Terdapat galat aktif ({txt_galat})! Membatalkan pengiriman...")
            btn_batal = d(className="android.widget.Button", text="Batal")
            if btn_batal.exists:
                btn_batal.click()
            raise Exception(f"Form memiliki galat aktif: {txt_galat}")

    # Klik 'Kirim' di Pop-up Dialog Info
    print("[*] Mengonfirmasi Kirim di dialog info...")
    btn_kirim_dialog = d(className="android.widget.Button", text="Kirim")
    if btn_kirim_dialog.exists:
        btn_kirim_dialog.click()
    else:
        d.click(360, 1015)
    time.sleep(2.5)

    # Klik 'Konfirmasi'
    print("[*] Mengklik 'Konfirmasi'...")
    btn_konfirm = d(className="android.widget.Button", text="Konfirmasi")
    if btn_konfirm.exists:
        btn_konfirm.click()
    else:
        d.click(360, 850)
    time.sleep(2.5)

    # Dialog Akhir 'YA'
    print("[*] Mengonfirmasi final: Mengklik 'YA'...")
    btn_ya_final = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
    if not btn_ya_final.exists:
        btn_ya_final = d(text="YA")
    if not btn_ya_final.exists:
        btn_ya_final = d(text="IYA")
    if btn_ya_final.exists:
        btn_ya_final.click()
    else:
        d.click(519, 1385)

    print("[*] Menunggu proses upload & submit ke server selesai (muncul tombol OK)...")
    btn_ok_final = d(resourceId="id.go.bpsfasih:id/btn_submit_progress_close")
    for wait_ok in range(30):
        if btn_ok_final.exists or d(text="OK").exists:
            print(f"[OK] Submit server selesai (detik ke-{wait_ok+1})!")
            break
        time.sleep(1.0)

    # Klik tombol OK
    if btn_ok_final.exists:
        btn_ok_final.click()
    elif d(text="OK").exists:
        d(text="OK").click()
    else:
        print("[*] Fallback: Mengklik koordinat tombol OK (351, 1318)...")
        d.click(351, 1318)
    time.sleep(2.5)

    # 13. Deteksi Layar Tujuan Setelah Submit Selesai (Halaman Upload vs Daftar Assignment)
    print("[*] Memeriksa layar tujuan setelah submit (Halaman Upload atau Daftar Assignment)...")
    detected_screen = None
    for wait_scr in range(15):
        time.sleep(1.0)
        # Jika ada loading progress, tunggu proses render selesai
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            continue

        # Cek apakah masuk ke 'Halaman Upload'
        if d(text="Halaman Upload").exists or d(resourceId="id.go.bpsfasih:id/btn_check_status").exists or d(resourceId="id.go.bpsfasih:id/btn_check_status_bulk").exists:
            detected_screen = "HALAMAN_UPLOAD"
            print(f"[OK] Terdeteksi masuk ke 'Halaman Upload' (detik ke-{wait_scr+1})!")
            break

        # Cek apakah langsung masuk ke 'Daftar Assignment'
        if d(text="Daftar Assignment").exists or d(text="Search:").exists:
            detected_screen = "DAFTAR_ASSIGNMENT"
            print(f"[OK] Terdeteksi langsung kembali ke 'Daftar Assignment' (detik ke-{wait_scr+1})!")
            break

    # JIKA MASUK KE HALAMAN UPLOAD:
    if detected_screen == "HALAMAN_UPLOAD":
        print("[*] Memproses Halaman Upload: Mengklik 'Cek Status'...")
        time.sleep(1.5)
        btn_cek_status = d(resourceId="id.go.bpsfasih:id/btn_check_status")
        if not btn_cek_status.exists:
            btn_cek_status = d(text="Cek Status")
        if not btn_cek_status.exists:
            btn_cek_status = d(resourceId="id.go.bpsfasih:id/btn_check_status_bulk")
        
        if btn_cek_status.exists:
            btn_cek_status.click()
            print("[*] Tombol 'Cek Status' diklik. Menunggu status antrian berubah menjadi SUCCESS...")
        else:
            print("[*] Fallback: Mengklik koordinat tombol Cek Status (570, 665)...")
            d.click(570, 665)

        # Tunggu sampai status berubah menjadi SUCCESS
        for wait_s in range(15):
            time.sleep(1.0)
            xml_upload = d.dump_hierarchy()
            if "SUCCESS" in xml_upload:
                print(f"[OK] Status antrian upload berubah menjadi SUCCESS (detik ke-{wait_s+1})!")
                break

        time.sleep(1.5)
        # Klik tombol Kembali (Back) untuk kembali ke Daftar Assignment
        print("[*] Mengklik tombol kembali (Back) menuju Daftar Assignment...")
        btn_back = d(resourceId="id.go.bpsfasih:id/back_button")
        if btn_back.exists:
            btn_back.click()
        else:
            d.press("back")

        # Tunggu kembali ke halaman 'Daftar Assignment'
        print("[*] Memastikan kembali ke halaman Daftar Assignment...")
        for _ in range(15):
            time.sleep(1.0)
            if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                continue
            if d(text="Daftar Assignment").exists or d(text="Search:").exists:
                print("[OK] Berhasil kembali ke halaman Daftar Assignment.")
                break
            if d(text="Halaman Upload").exists or d(resourceId="id.go.bpsfasih:id/back_button").exists:
                btn_back = d(resourceId="id.go.bpsfasih:id/back_button")
                if btn_back.exists:
                    btn_back.click()
                else:
                    d.press("back")

    elif detected_screen == "DAFTAR_ASSIGNMENT":
        print("[OK] Aplikasi langsung berada di halaman 'Daftar Assignment'. Melewati proses Halaman Upload.")

    else:
        # Fallback jika belum terdeteksi jelas, panggil recovery
        print("[!] Layar belum teridentifikasi jelas, memastikan posisi kembali ke 'Daftar Assignment'...")
        back_to_assignment_list(d)

    # 15. Catat Sukses
    print(f"[OK] SUKSES! NIK untuk IDPEL {idpel} berhasil diperbarui menjadi {nik_baru}!")
    append_to_log(OUT_SUKSES, {
        "id_pelanggan": idpel,
        "NIK_Perbaikan": nik_baru,
        "waktu_selesai": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Hapus dari CSV input
    remove_idpel_from_input_csv(csv_input_path, idpel)
    clear_search_box(d)
    return "SUKSES"


def scroll_table_up(d, swipes=15):
    """Menggulir tabel ke baris paling awal."""
    for _ in range(swipes):
        d.swipe(360, 850, 360, 1450, duration=0.12)
        time.sleep(0.05)


def scroll_table_down(d):
    """Menggulir tabel ke bawah sedikit."""
    d.swipe(360, 1350, 360, 850, duration=0.25)
    time.sleep(0.3)


def scan_all_meters_from_hp(d):
    """
    Memindai seluruh nomor meter yang ada di tabel assignment HP.
    1. Memastikan opsi 'Show 100 entries' aktif agar seluruh data tampil tanpa pagination.
    2. Menggulir ke baris 1 paling atas.
    3. Menggulir bertahap ke bawah dan mengekstrak nomor meter (11 digit).
    4. Berhenti ketika tidak ada nomor meter baru setelah 3 kali scroll berturut-turut.
    5. Mengembalikan daftar nomor meter unik.
    """
    import re
    print("[*] Menyiapkan pemindaian nomor meter di aplikasi Fasih...")
    if not (d(text="Daftar Assignment").exists or d(text="Search:").exists):
        if not back_to_assignment_list(d):
            raise Exception("Gagal memposisikan layar ke 'Daftar Assignment'.")

    clear_search_box(d)

    # 1. Pastikan tampilan 'Show 100 entries' aktif jika ada opsi dropdown
    scroll_table_up(d, swipes=10)
    dd_50 = d(text="50")
    if dd_50.exists:
        print("[*] Mengubah konfigurasi tabel menjadi '100 entries' per halaman...")
        dd_50.click()
        time.sleep(1.0)
        opt_100 = d(text="100")
        if opt_100.exists:
            opt_100.click()
            time.sleep(1.5)
            print("[✓] Tampilan berhasil diubah menjadi 100 entries.")

    # 2. Gulir ke baris paling awal
    print("[*] Menggulir tabel ke posisi paling awal...")
    scroll_table_up(d, swipes=15)

    collected_meters = []
    print("[*] Memulai pemindaian dari baris 1 sampai tuntas...")

    consecutive_no_new = 0
    for step in range(35):
        xml = d.dump_hierarchy()
        found = re.findall(r'\b\d{11}\b', xml)
        new_in_step = 0
        for m in found:
            if m not in collected_meters:
                collected_meters.append(m)
                new_in_step += 1

        m_footer = re.search(r'Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries', xml)
        footer_text = m_footer.group(0) if m_footer else "-"

        print(f"    [Pindai Step {step+1:2d}] +{new_in_step:2d} meter baru (Total: {len(collected_meters):2d}) | {footer_text}")

        if new_in_step == 0:
            consecutive_no_new += 1
            if consecutive_no_new >= 3:
                print(f"[✓] Mencapai akhir tabel. Selesai memindai!")
                break
        else:
            consecutive_no_new = 0

        scroll_table_down(d)

    # 3. Kembalikan ke paling atas untuk persiapan eksekusi
    print("[*] Mengembalikan posisi tabel ke baris paling atas...")
    scroll_table_up(d, swipes=15)

    print(f"[✓] Berhasil mengumpulkan {len(collected_meters)} nomor meter unik dari HP.")
    return collected_meters


def run_reverse_mode(target_device=None, custom_csv=None):
    """
    Mode 3: PENGEDITAN DATA TERBALIK (REVERSE)
    1. Memindai seluruh nomor meter dari HP.
    2. Mencocokkan nomor meter dengan file master (mastermeter.csv atau master.csv).
    3. Mengeksekusi pembaruan NIK hanya untuk data yang cocok.
    """
    target_csv = custom_csv or ""
    if not target_csv:
        if os.path.exists("mastermeter.csv"):
            print("[*] File 'mastermeter.csv' terdeteksi otomatis sebagai file master.")
            target_csv = "mastermeter.csv"
        elif os.path.exists("master.csv"):
            print("[*] File 'master.csv' terdeteksi otomatis sebagai file master.")
            target_csv = "master.csv"
        else:
            target_csv = pilih_file_csv(judul_mode="Pengeditan NIK Terbalik (Master CSV)")
            if not target_csv:
                return

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   OTOMASI PENGEDITAN NIK TERBALIK (REVERSE MODE)         ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  File Master : {target_csv:<41} ║")
    if target_device:
        print(f"║  Device ID   : {target_device:<41} ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 1. Muat master data ke dict
    raw_data = load_input_data(target_csv)
    if not raw_data:
        print(f"[X] Gagal membaca data dari '{target_csv}'. Program berhenti.")
        return

    # Buat mapping berdasarkan no_meter jika tersedia, atau id_pelanggan
    has_meter_col = any("no_meter" in r for r in raw_data)
    master_by_meter = {}
    master_by_idpel = {}
    for r in raw_data:
        idp = r["id_pelanggan"]
        nik = r["NIK_Perbaikan"]
        master_by_idpel[idp] = r
        if "no_meter" in r and r["no_meter"]:
            master_by_meter[r["no_meter"]] = r

    print(f"[OK] Berhasil memuat {len(raw_data)} data master.")
    if has_meter_col:
        print(f"     Terdeteksi {len(master_by_meter)} data nomor meter unik.")

    # 2. Hubungkan ke Perangkat Android
    d = connect_device(target_device)
    if not d:
        return

    package_name = "id.go.bpsfasih"
    print(f"[*] Memastikan aplikasi '{package_name}' aktif di layar...")
    d.app_start(package_name)
    time.sleep(2.0)

    # 3. Pindai seluruh data dari HP
    hp_meters = scan_all_meters_from_hp(d)
    if not hp_meters:
        print("[!] Tidak ada nomor meter yang berhasil discan dari HP. Program berhenti.")
        return

    # 4. Cocokkan data HP dengan file master
    antrean_eksekusi = []
    dilewati = []

    for m in hp_meters:
        if m in master_by_meter:
            antrean_eksekusi.append(master_by_meter[m])
        else:
            dilewati.append(m)

    total_hp = len(hp_meters)
    total_cocok = len(antrean_eksekusi)
    total_lewat = len(dilewati)

    print("\n" + "═" * 65)
    print("           REKAPITULASI PENCOCOKAN DATA HP vs MASTER")
    print("═" * 65)
    print(f"  • Total Penugasan di HP        : {total_hp} data")
    print(f"  • Cocok di Master (Eksekusi)   : {total_cocok} data")
    print(f"  • Tidak Ada di Master (Lewati) : {total_lewat} data")
    print("═" * 65 + "\n")

    if total_cocok == 0:
        print("[✓] Semua penugasan di HP saat ini tidak memerlukan perbaikan NIK.")
        return

    print(f"[*] Memulai pemrosesan {total_cocok} data penugasan yang cocok...\n")

    # 5. Eksekusi pembaruan NIK untuk data yang cocok
    sukses_count = 0
    idpel_tidak_ada_count = 0
    nik_tidak_ditemukan_count = 0
    gagal_count = 0

    for idx, item in enumerate(antrean_eksekusi, start=1):
        idpel = item["id_pelanggan"]
        nik = item["NIK_Perbaikan"]
        meter = item.get("no_meter", "")
        meter_info = f" (No. Meter: {meter})" if meter else ""
        print(f"\n>>> Progress Reverse: [{idx}/{total_cocok}] IDPEL: {idpel}{meter_info} <<<")

        try:
            status_hasil = process_update_nik(d, item, target_csv)
            if status_hasil == "SUKSES":
                sukses_count += 1
            elif status_hasil == "IDPEL_NOT_FOUND":
                idpel_tidak_ada_count += 1
            elif status_hasil == "NIK_NOT_FOUND":
                nik_tidak_ditemukan_count += 1
            else:
                idpel_tidak_ada_count += 1
        except Exception as e:
            print(f"[X] Gagal memproses IDPEL {idpel}: {e}")
            gagal_count += 1
            append_to_log(OUT_GAGAL, {
                "id_pelanggan": idpel,
                "NIK_Perbaikan": nik,
                "error": str(e),
                "waktu": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            back_to_assignment_list(d)
            clear_search_box(d)
            time.sleep(2.0)

    print("\n" + "=" * 65)
    print("             PEMROSESAN REVERSE SELESAI!")
    print("=" * 65)
    print(f"  - Total Data Cocok      : {total_cocok}")
    print(f"  - Berhasil Diupdate     : {sukses_count} (Cek: '{OUT_SUKSES}')")
    print(f"  - IDPEL Tidak Ditemukan : {idpel_tidak_ada_count} (Cek: '{OUT_TIDAK_DITEMUKAN}')")
    print(f"  - NIK Tidak Ditemukan   : {nik_tidak_ditemukan_count} (Cek: '{OUT_NIK_TIDAK_DITEMUKAN}')")
    print(f"  - Gagal / Galat         : {gagal_count} (Cek: '{OUT_GAGAL}')")
    print("=" * 65)


def main(custom_device=None, custom_csv=None, mode="forward"):
    # Parsing CLI arguments jika dipanggil dari terminal
    parser = argparse.ArgumentParser(
        description="Otomasi Perbaikan Data NIK - Fasih BPS",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--device", "-d", type=str, default="", help="Serial ID perangkat Android (lihat via 'adb devices')")
    parser.add_argument("--csv", "-c", type=str, default="", help="Nama/path file CSV data perbaikan NIK")
    parser.add_argument("--mode", "-m", type=str, default="forward", help="Pilih mode: 'forward' (atau '2') / 'reverse' (atau '3')")
    
    args, _ = parser.parse_known_args()
    target_device = custom_device or args.device or DEVICE_ID
    target_csv = custom_csv or args.csv or ""
    selected_mode = mode or args.mode or "forward"

    if selected_mode.lower() in ["reverse", "3", "terbalik", "rev"]:
        run_reverse_mode(target_device=target_device, custom_csv=target_csv)
        return

    # Jika file CSV belum ditentukan, minta pengguna memilih secara interaktif
    if not target_csv:
        target_csv = pilih_file_csv(judul_mode="Perbaikan Data NIK")
        if not target_csv:
            return

    print("╔══════════════════════════════════════════════════════════╗")
    print("║      OTOMASI PERBAIKAN DATA NIK - FASIH BPS             ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  File Target : {target_csv:<41} ║")
    if target_device:
        print(f"║  Device ID   : {target_device:<41} ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 1. Load Data CSV
    if not os.path.exists(target_csv):
        print(f"[X] File CSV '{target_csv}' TIDAK DITEMUKAN!")
        print(f"    Pastikan file '{target_csv}' sudah berada di folder proyek.")
        return

    data_list = load_input_data(target_csv)
    if not data_list:
        print(f"[!] Tidak ada data untuk diproses di '{target_csv}'. Program selesai.")
        return

    # 2. Hubungkan ke Perangkat Android
    d = connect_device(target_device)
    if not d:
        return

    # Pastikan aplikasi Fasih aktif
    package_name = "id.go.bpsfasih"
    print(f"[*] Memastikan aplikasi '{package_name}' aktif di layar...")
    d.app_start(package_name)
    time.sleep(2.0)

    total_data = len(data_list)
    print(f"\n[*] Memulai pemrosesan {total_data} data NIK perbaikan...\n")

    sukses_count = 0
    idpel_tidak_ada_count = 0
    nik_tidak_ditemukan_count = 0
    gagal_count = 0

    for idx, item in enumerate(data_list, start=1):
        idpel = item["id_pelanggan"]
        nik = item["NIK_Perbaikan"]
        print(f"\n>>> Progress: [{idx}/{total_data}] IDPEL: {idpel} <<<")

        try:
            status_hasil = process_update_nik(d, item, target_csv)
            if status_hasil == "SUKSES":
                sukses_count += 1
            elif status_hasil == "IDPEL_NOT_FOUND":
                idpel_tidak_ada_count += 1
            elif status_hasil == "NIK_NOT_FOUND":
                nik_tidak_ditemukan_count += 1
            else:
                idpel_tidak_ada_count += 1
        except Exception as e:
            print(f"[X] Gagal memproses IDPEL {idpel}: {e}")
            gagal_count += 1
            append_to_log(OUT_GAGAL, {
                "id_pelanggan": idpel,
                "NIK_Perbaikan": nik,
                "error": str(e),
                "waktu": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            back_to_assignment_list(d)
            clear_search_box(d)
            time.sleep(2.0)

    print("\n" + "=" * 60)
    print("              PEMROSESAN SELESAI!")
    print("=" * 60)
    print(f"  - Total Data            : {total_data}")
    print(f"  - Berhasil Diupdate     : {sukses_count} (Cek: '{OUT_SUKSES}')")
    print(f"  - IDPEL Tidak Ditemukan : {idpel_tidak_ada_count} (Cek: '{OUT_TIDAK_DITEMUKAN}')")
    print(f"  - NIK Tidak Ditemukan   : {nik_tidak_ditemukan_count} (Cek: '{OUT_NIK_TIDAK_DITEMUKAN}')")
    print(f"  - Gagal / Galat         : {gagal_count} (Cek: '{OUT_GAGAL}')")
    print("=" * 60)


if __name__ == "__main__":
    main()
