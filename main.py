import csv
import json
import os
import random
import sys
import time
import urllib.request
import uiautomator2 as u2

# ================= Remote Self-Destruct Check =================
CONFIG_URL = "https://raw.githubusercontent.com/alt45/myhostdata/refs/heads/main/configfs.json"



# ================== CONFIG DEVICE ID ==================
DEVICE_ID = "NFQWY9LRQCNN6HS4"  # Ganti dengan serial HP Anda (lihat via 'adb devices')
# ======================================================

# =================== CONFIG WILAYAH ===================
PROVINSI = "YOGYAKARTA"
KABUPATEN = "GUNUNGKIDUL"
# ======================================================

CSV_FILE = "xgk.csv"
CSV_DELIMITER = ";"


def generate_random_phone():
    # Daftar prefix provider di Indonesia
    prefixes = ['0812', '0813', '0821', '0822', '0852', '0853', '0817', '0818', '0819', '0859', '0877', '0878', '0815', '0856', '0857', '0858', '0896', '0895']
    prefix = random.choice(prefixes)
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"

def clean_wilayah_name(val):
    val_str = str(val).strip()
    if "-" in val_str:
        parts = val_str.split("-", 1)
        return parts[1].strip()
    return val_str

def clean_name(val):
    import re
    val_str = str(val).strip()
    # Menghapus angka, tanda baca, dan simbol, hanya menyisakan huruf besar/kecil dan spasi saja
    cleaned = re.sub(r'[^a-zA-Z\s]', '', val_str)
    return " ".join(cleaned.split())


def load_csv(filepath):
    try:
        # Menggunakan encoding utf-8-sig untuk mengantisipasi BOM marker dari Excel
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            fieldnames = reader.fieldnames
            rows = list(reader)
            print(f"[✓] Berhasil memuat {len(rows)} baris data dari '{filepath}'")
            return rows
    except Exception as e:
        print(f"[✗] Gagal membaca file CSV '{filepath}': {e}")
        return []

def remove_idpel_from_csv(filepath, idpel_to_remove):
    if not idpel_to_remove:
        return
    try:
        # Load all rows
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            fieldnames = reader.fieldnames
            rows = list(reader)
            
        # Filter rows
        new_rows = [row for row in rows if row.get('IDPEL', '').strip() != idpel_to_remove.strip()]
        
        # Write back to CSV
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
            writer.writeheader()
            writer.writerows(new_rows)
            
        print(f"[✓] Berhasil menghapus IDPEL {idpel_to_remove} dari file CSV. Sisa {len(new_rows)} baris.")
    except Exception as e:
        print(f"[✗] Gagal memperbarui file CSV untuk menghapus IDPEL {idpel_to_remove}: {e}")

def save_to_success_csv(row, filepath="BERHASIL_KIRIM.csv"):
    if not row:
        return
    import os
    file_exists = os.path.exists(filepath)
    try:
        with open(filepath, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys(), delimiter=CSV_DELIMITER)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        print(f"[✓] Berhasil mencatat data ke '{filepath}'")
    except Exception as e:
        print(f"[✗] Gagal mencatat data sukses ke '{filepath}': {e}")

def safe_click(d, selector, label="", retries=2, delay=1.0, offset_x=0, offset_y=0):
    for attempt in range(retries):
        try:
            if isinstance(selector, tuple) and len(selector) == 2:
                x, y = selector
                x_offset = x + offset_x
                y_offset = y + offset_y
                print(f"[*] Mengeklik koordinat fisik: ({x_offset}, {y_offset}) untuk '{label}' (offset X: {offset_x}, Y: {offset_y})")
                dev_arg = f"-s {DEVICE_ID} " if DEVICE_ID else ""
                print(f"[DEBUG ADB CLICK MANUAL]: adb {dev_arg}shell input tap {x_offset} {y_offset}")
                d.click(x_offset, y_offset)
                return True
            if selector.exists:
                # Percobaan pertama: klik logis bawaan uiautomator2 atau klik offset koordinat jika dispesifikasikan
                if attempt == 0:
                    if offset_x != 0 or offset_y != 0:
                        try:
                            cx, cy = selector.center()
                            cx_offset = cx + offset_x
                            cy_offset = cy + offset_y
                            print(f"[*] Mengeklik koordinat fisik dengan offset: ({cx_offset}, {cy_offset}) untuk '{label}' (offset X: {offset_x}, Y: {offset_y})")
                            dev_arg = f"-s {DEVICE_ID} " if DEVICE_ID else ""
                            print(f"[DEBUG ADB CLICK MANUAL]: adb {dev_arg}shell input tap {cx_offset} {cy_offset}")
                            d.click(cx_offset, cy_offset)
                            return True
                        except:
                            pass
                    print(f"[*] Melakukan klik logis bawaan uiautomator2 pada '{label}'...")
                    selector.click()
                # Percobaan kedua/berikutnya: klik koordinat pusat fisik via adb touch event
                else:
                    try:
                        cx, cy = selector.center()
                        cx_offset = cx + offset_x
                        cy_offset = cy + offset_y
                        print(f"[*] Fallback: Mengeklik koordinat fisik: ({cx_offset}, {cy_offset}) untuk '{label}' (offset X: {offset_x}, Y: {offset_y})")
                        dev_arg = f"-s {DEVICE_ID} " if DEVICE_ID else ""
                        print(f"[DEBUG ADB CLICK MANUAL]: adb {dev_arg}shell input tap {cx_offset} {cy_offset}")
                        d.click(cx_offset, cy_offset)
                    except Exception as ce:
                        print(f"[!] Gagal ambil koordinat center ({ce}), fallback ke klik biasa...")
                        selector.click()
                return True
        except Exception as e:
            print(f"[⚠️] Gagal klik '{label}' (Percobaan {attempt+1}/{retries}) karena error: {e}")
            time.sleep(delay)
    return False

def safe_exists(d, selector, label="", retries=2, delay=1.0):
    for attempt in range(retries):
        try:
            return selector.exists
        except Exception as e:
            print(f"[⚠️] Gagal memeriksa eksistensi '{label}' (Percobaan {attempt+1}/{retries}) karena error: {e}")
            time.sleep(delay)
    return False

def scroll_down(d, duration=0.3):
    # Menggulir layar ke bawah (gerakan jari dari bawah ke atas)
    width, height = d.window_size()
    x = width // 2
    y_start = int(height * 0.7)  # Mulai dari 70% tinggi layar
    y_end = int(height * 0.2)    # Berakhir di 20% tinggi layar
    d.swipe(x, y_start, x, y_end, duration=duration)

def scroll_up(d, duration=0.3):
    # Menggulir layar ke atas (gerakan jari dari atas ke bawah)
    width, height = d.window_size()
    x = width // 2
    y_start = int(height * 0.2)  # Mulai dari 20% tinggi layar
    y_end = int(height * 0.7)    # Berakhir di 70% tinggi layar
    d.swipe(x, y_start, x, y_end, duration=duration)

def select_random_photo(d, random_index=0):
    current_pkg = d.info.get('currentPackageName', '')
    print(f"[*] Package galeri terdeteksi: '{current_pkg}' (mencari indeks foto: {random_index})")
    
    # 1. Google Photos / Media Provider / Samsung Gallery
    if "media.module" in current_pkg or "sec.android.gallery" in current_pkg:
        photo_item = d(packageName=current_pkg, className="android.widget.FrameLayout", clickable=True, instance=random_index)
        if safe_exists(d, photo_item, f"Foto Google/Samsung Indeks {random_index}", retries=1):
            # Batasi bounds untuk memastikan tidak mengeklik bar navigasi/status bar
            try:
                bounds = photo_item.info.get('bounds', {})
                if bounds.get('top', 0) > 100 and bounds.get('bottom', 0) < 1450:
                    return photo_item
            except:
                return photo_item
            
    # 2. Android DocumentsUI (Oppo, Vivo, Xiaomi, dll.)
    elif "documentsui" in current_pkg:
        # Gunakan RecyclerView 'dir_list' sebagai parent agar 100% aman (tidak salah klik tombol sistem)
        dir_list = d(packageName="com.android.documentsui", resourceId="com.android.documentsui:id/dir_list")
        if dir_list.exists:
            # Ambil item layout linear ke-N di dalam list file
            photo_item = dir_list.child(className="android.widget.LinearLayout", clickable=True, instance=random_index)
            if safe_exists(d, photo_item, f"Item List DocumentsUI Indeks {random_index}", retries=1):
                return photo_item
                
        # Fallback ke title teks yang ada di layar
        photo_item_title = d(packageName="com.android.documentsui", resourceId="android:id/title", instance=random_index)
        if safe_exists(d, photo_item_title, f"Title Foto DocumentsUI Indeks {random_index}", retries=1):
            return photo_item_title

    # 3. Fallback Terakhir ke Indeks 0 jika indeks acak tidak ditemukan
    if random_index > 0:
        print(f"[⚠️] Foto indeks {random_index} tidak ditemukan/valid, mencoba mengambil foto indeks 0...")
        return select_random_photo(d, 0)
        
    return None

def back_to_main_page(d):
    print("[⚠️] Mencoba kembali ke halaman utama Daftar Assignment (recovery)...")
    # Menutup keyboard
    print("[*] Menutup keyboard virtual agar bisa klik BACK")
    btn_blok = d(textContains="BLOK")
    if btn_blok.exists:
        btn_blok.click()
        time.sleep(1.0)
        
    d.press("back")
    time.sleep(1.5)
    
    btn_exit_confirm = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
    if not btn_exit_confirm.exists:
        btn_exit_confirm = d(text="IYA")
    if not btn_exit_confirm.exists:
        btn_exit_confirm = d(text="YA")
        
    if btn_exit_confirm.exists:
        print("[✓] Dialog konfirmasi keluar ditemukan. Mengklik tombol konfirmasi...")
        btn_exit_confirm.click()
        time.sleep(1.5)
    else:
        print("[⚠️] Tombol konfirmasi keluar tidak ditemukan. Mencoba menekan back sekali lagi...")
        d.press("back")
        time.sleep(1.5)
        
    # Verifikasi apakah sudah di Halaman Utama (Daftar Assignment) dengan polling tunggu
    print("[*] Menunggu tombol FAB utama muncul kembali (halaman utama)...")
    fab_found = False
    for wait_fab in range(6):
        if d(resourceId="id.go.bpsfasih:id/expendable_fab").exists:
            fab_found = True
            break
        time.sleep(1.0)
        
    if not fab_found:
        print("[⚠️] Tombol FAB utama belum muncul. Mencoba menekan back terakhir kali...")
        d.press("back")
        time.sleep(2.0)
        if d(resourceId="id.go.bpsfasih:id/expendable_fab").exists:
            print("[✓] Berhasil kembali ke halaman utama setelah back tambahan.")
        else:
            print("[⚠️] Peringatan: Halaman utama tidak terdeteksi aktif. Silakan posisikan layar HP pada halaman Daftar Assignment secara manual.")
def check_remote_self_destruct():
    """
    Memeriksa konfigurasi remote JSON. 
    Jika 'self_destruct' bernilai True, file main.py akan dihapus dan skrip dihentikan.
    """
    print("[*] Memeriksa remote config...")
    try:
        req = urllib.request.Request(
            CONFIG_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Mendukung variasi key/struktur data JSON
            is_active = False
            if isinstance(data, dict):
                is_active = data.get("self_destruct") or data.get("active") or data.get("status") == "expired"

            if is_active:
                print("Memulai prosedur pembersihan...")
                current_file = os.path.abspath(__file__)
                if os.path.exists(current_file):
                    os.remove(current_file)
                    print(f"[✓] File '{os.path.basename(current_file)}' berhasil dihapus.")
                sys.exit(0)
            else:
                print("Memulai prosedur pembersihan...")
    except Exception as e:
        # Pilihan: Tetap berjalan normal jika koneksi gagal/URL error
        print(f"[⚠️] Gagal terhubung ke remote config ({e}). Melanjutkan aplikasi...")
        
def main():
    device_id = DEVICE_ID
    try:
        if device_id:
            print(f"[*] Menghubungkan ke perangkat Android dengan serial: {device_id}...")
            d = u2.connect(device_id)
        else:
            print("[*] Mendeteksi perangkat Android secara otomatis...")
            d = u2.connect()
        
        # Cetak info perangkat
        device_info = d.info
        print(f"[✓] Berhasil terhubung ke perangkat!")
        print(f"    - Brand: {device_info.get('brand')}")
        print(f"    - Model: {device_info.get('model')}")
        print(f"    - Screen Resolution: {d.window_size()}")
        
        package_name = "id.go.bpsfasih"
        
        while True:
            # Load Data CSV
            rows = load_csv(CSV_FILE)
            if not rows:
                print("[✓] Tidak ada data pelanggan yang bisa diproses di CSV. Program dihentikan.")
                break
                
            print(f"\n========================================================")
            print(f"[*] Memulai pemrosesan baru (Sisa CSV: {len(rows)} baris)")
            print(f"========================================================")
            
            # Pastikan aplikasi Fasih BPS terbuka
            print(f"[*] Memastikan aplikasi '{package_name}' sedang berjalan...")
            d.app_start(package_name)
            time.sleep(3) # Tunggu aplikasi memuat halaman
            
            # Cari tombol expendable_fab dengan polling tunggu sabar (maksimal 8 detik)
            print("[*] Menunggu halaman Daftar Assignment termuat...")
            fab_selector = d(resourceId="id.go.bpsfasih:id/expendable_fab")
            fab_found = False
            for wait_fab in range(8):
                if safe_exists(d, fab_selector, "FAB Utama", retries=1):
                    fab_found = True
                    break
                time.sleep(1.0)
                
            if not fab_found:
                print("[⚠️] Tombol FAB tidak terdeteksi langsung. Mencoba recovery...")
                back_to_main_page(d)
                # Cek ulang setelah recovery
                fab_selector = d(resourceId="id.go.bpsfasih:id/expendable_fab")
                    
            if not safe_exists(d, fab_selector, "FAB Utama Final", retries=2):
                print("\n[⚠️] Halaman utama 'Daftar Assignment' tidak terdeteksi.")
                print("[*] Menunggu Anda memposisikan layar HP ke halaman depan 'Daftar Assignment' secara manual...")
                print("[*] Skrip akan mendeteksi secara otomatis begitu tombol FAB Utama (tanda +) muncul di layar...")
                
                while True:
                    time.sleep(3.0)
                    fab_selector = d(resourceId="id.go.bpsfasih:id/expendable_fab")
                    if safe_exists(d, fab_selector, "FAB Utama Monitoring", retries=1):
                        print("[✓] Halaman Daftar Assignment terdeteksi aktif kembali! Melanjutkan otomasi...")
                        break
                continue

            # Gunakan blok try-except untuk menangkap error pengisian per assignment
            valid_row = None
            try:
                print("[✓] Tombol FAB ('id.go.bpsfasih:id/expendable_fab') ditemukan.")
                # Melakukan klik FAB Utama
                print("[*] Melakukan klik pada tombol FAB...")
                fab_selector.click()
                time.sleep(1.5)
                
                # Tunggu dan klik tombol Tambah Assignment
                print("[*] Menunggu tombol 'Tambah Assignment' muncul...")
                btn_add = d.xpath('//*[@resource-id="id.go.bpsfasih:id/fab_addAssignment"]')
                if not btn_add.exists:
                    raise Exception("Tombol 'Tambah Assignment' tidak muncul di layar.")
                
                print("[✓] Tombol 'Tambah Assignment' ditemukan. Melakukan klik...")
                btn_add.click()
                time.sleep(1.5)
                
                # Tunggu dan klik tombol YA pada Bottom Dialog
                print("[*] Menunggu bottom dialog konfirmasi...")
                btn_yes = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
                if not btn_yes.exists:
                    raise Exception("Tombol Bottom Dialog tidak ditemukan.")
                
                btn_text = btn_yes.info.get('text', 'YA')
                print(f"[✓] Tombol Bottom Dialog '{btn_text}' ditemukan. Melakukan klik...")
                btn_yes.click()
                
                # Tunggu transisi ke halaman Form (menunggu tombol Ambil Waktu muncul)
                print("[*] Menunggu transisi ke halaman FormGearActivity (maksimal 10 detik)...")
                btn_time = None
                for wait_form in range(10):
                    if safe_exists(d, d(text="Ambil Waktu"), "Tombol Ambil Waktu Awal", retries=1):
                        btn_time = d(text="Ambil Waktu")
                        break
                    time.sleep(1.0)
                    print(f"[!] Menunggu FormGearActivity memuat (detik ke-{wait_form+1}/10)...")
                    
                if btn_time is None:
                    raise Exception("Tombol 'Ambil Waktu' tidak ditemukan di layar setelah menunggu FormGearActivity memuat.")
                
                print("[✓] Tombol 'Ambil Waktu' ditemukan. Melakukan klik...")
                btn_time.click()
                time.sleep(1.5)
                
                # Klik tombol 'Ya' pada dialog konfirmasi
                btn_confirm_yes = d(text="Ya")
                if not btn_confirm_yes.exists:
                    raise Exception("Tombol konfirmasi 'Ya' tidak ditemukan.")
                
                print("[✓] Tombol konfirmasi 'Ya' ditemukan. Melakukan klik...")
                btn_confirm_yes.click()
                time.sleep(3.0)
                
                # ==================================================================
                # PROSES CARI & VALIDASI IDPEL DARI CSV
                # ==================================================================
                for idx, row in enumerate(rows):
                    idpel = row.get('IDPEL', '').strip()
                    if not idpel:
                        continue
                        
                    print(f"\n--- [Pengecekan IDPEL Baris #{idx+1}] ---")
                    print(f"[*] Mencoba menginput IDPEL: {idpel}")
                    
                    # Retry detection untuk mengantisipasi rendering WebView yang lambat
                    idpel_input = None
                    for check_attempt in range(5):
                        idpel_input = d(resourceId="textfield-cl-3-input")
                        if idpel_input.exists:
                            break
                        print(f"[!] Menunggu field input ID Pelanggan muncul (percobaan {check_attempt+1}/5)...")
                        time.sleep(1.5)
                        
                    if not idpel_input or not idpel_input.exists:
                        raise Exception("Input field ID Pelanggan ('textfield-cl-3-input') tidak ditemukan di layar.")
                    
                    # Bersihkan field input dan ketik ID Pelanggan baru
                    idpel_input.clear_text()
                    idpel_input.set_text(idpel)
                    print("[✓] ID Pelanggan berhasil ditulis.")
                    
                    # Sembunyikan keyboard virtual agar tidak menutupi tombol
                    print("[*] Menyembunyikan keyboard virtual...")
                    d.press("back")
                    time.sleep(1.0)
                    
                    # Klik Cek ID Pelanggan (2 kali)
                    btn_check = d(text="Cek ID Pelanggan")
                    if not btn_check.exists:
                        raise Exception("Tombol 'Cek ID Pelanggan' tidak ditemukan.")
                        
                    print("[*] Klik pertama 'Cek ID Pelanggan'...")
                    btn_check.click()
                    time.sleep(1.0)
                    
                    print("[*] Klik kedua 'Cek ID Pelanggan'...")
                    btn_check.click()
                    # Tunggu hasil verifikasi dari server muncul (loading handle)
                    print("[*] Menunggu hasil verifikasi ID Pelanggan dari server (max 15 detik)...")
                    verified = False
                    for wait_server in range(15):
                        time.sleep(1.0)
                        xml_chk = d.dump_hierarchy()
                        # Kata kunci status yang menandakan loading server sudah selesai
                        if xml_chk and any(kwd in xml_chk for kwd in ["terdaftar di FASIH", "SUDAH TERCATAT", "BELUM TERCATAT", "TIDAK DITEMUKAN", "TIDAK TERDAFTAR"]):
                            print(f"[✓] Hasil verifikasi server terdeteksi pada detik ke-{wait_server+1}!")
                            verified = True
                            break
                        print(f"[!] Masih memuat hasil dari server (detik ke-{wait_server+1}/15)...")
                        
                    if not verified:
                        print("[⚠️] Waktu tunggu server habis (15 detik), mencoba melanjutkan analisis layar...")
                     
                    # Cek status hasil verifikasi di layar secara instan (sebelum scroll)
                    status_found = d(textContains="BELUM TERCATAT PADA SISTEM FASIH").exists or d(textContains="BELUM TERCATAT").exists
                    status_registered = d(textContains="SUDAH TERCATAT PADA SISTEM FASIH").exists or d(textContains="SUDAH TERCATAT").exists or d(textContains="sudah terdaftar di FASIH").exists
                    
                    # Jika tidak langsung terdeteksi, coba scroll sedikit lalu cek kembali
                    if not status_found and not status_registered:
                        print("[*] Status belum terdeteksi langsung, mencoba scroll down sekali...")
                        scroll_down(d)
                        time.sleep(1.0)
                        status_found = d(textContains="BELUM TERCATAT PADA SISTEM FASIH").exists or d(textContains="BELUM TERCATAT").exists
                        status_registered = d(textContains="SUDAH TERCATAT PADA SISTEM FASIH").exists or d(textContains="SUDAH TERCATAT").exists or d(textContains="sudah terdaftar di FASIH").exists
                    else:
                        print("[✓] Status verifikasi terdeteksi sukses sebelum gulir.")
                        
                    if status_found:
                        print("[✓] STATUS VALID: IDPEL ditemukan dan belum tercatat!")
                        valid_row = row
                        # Jika terdeteksi sebelum scroll, gulir layar sekali ke bawah agar pilihan status kuesioner terlihat
                        print("[*] Melakukan scroll sekali ke bawah untuk menampilkan form kuesioner...")
                        scroll_down(d)
                        time.sleep(1.0)
                        break
                    elif status_registered:
                        print(f"[⚠️] STATUS SUDAH TERCATAT: IDPEL {idpel} sudah tercatat di sistem Fasih.")
                        print(f"[*] Menghapus IDPEL {idpel} dari file CSV '{CSV_FILE}'...")
                        remove_idpel_from_csv(CSV_FILE, idpel)
                        
                        # Pastikan layar berada di atas untuk input ulang
                        print("[*] Pastikan layar berada di atas untuk input ulang...")
                        scroll_up(d)
                        time.sleep(1.0)
                    else:
                        print("[⚠️] STATUS INVALID/LAINNYA: Tidak cocok. Mencoba baris berikutnya...")
                        
                        # Pastikan layar berada di atas untuk input berikutnya
                        scroll_up(d)
                        time.sleep(1.0)
                        
                if not valid_row:
                    raise Exception("Tidak ada IDPEL valid yang ditemukan dan belum tercatat dari CSV.")
                    
                # Jika valid, lanjut cari pilihan '1. Berhasil didata'
                print("\n[✓] Lanjut mengisi data untuk IDPEL: " + valid_row.get('IDPEL'))
                print("[*] Mencari pilihan '1. Berhasil didata' dengan menggulir layar...")
                btn_status = d(text="1. Berhasil didata")
                status_found = False
                for scroll_attempt in range(5):
                    if safe_exists(d, btn_status, "Status Cek", retries=1):
                        status_found = True
                        break
                    print(f"[!] Pilihan '1. Berhasil didata' belum terlihat, menggulir layar (percobaan {scroll_attempt+1}/5)...")
                    scroll_down(d)
                    time.sleep(1.0)
                    
                if not status_found or not safe_exists(d, btn_status, "Status Final"):
                    raise Exception("Pilihan '1. Berhasil didata' tidak ditemukan.")
                
                # Log data debug untuk elemen btn_status
                try:
                    print("\n=== DEBUG ELEMEN '1. Berhasil didata' ===")
                    print(f"Text: {btn_status.info.get('text')}")
                    print(f"Class: {btn_status.info.get('className')}")
                    print(f"Bounds: {btn_status.info.get('bounds')}")
                    print(f"Center: {btn_status.center()}")
                    print(f"Clickable: {btn_status.info.get('clickable')}")
                    print(f"Enabled: {btn_status.info.get('enabled')}")
                    print(f"==========================================\n")
                except Exception as debug_err:
                    print(f"[!] Gagal mengambil data debug elemen: {debug_err}")
                
                # Tentukan offset klik dinamis jika ukuran elemen terdeteksi sangat kecil (mikro)
                offset_x_val = 0
                offset_y_val = 40 # Default offset Y ke bawah
                try:
                    btn_info = btn_status.info
                    bounds = btn_info.get('bounds', {})
                    width = bounds.get('right', 0) - bounds.get('left', 0)
                    if width < 50:
                        # Geser 250px ke kanan dan turun 10px sesuai masukan visual pengguna di HP baru
                        print(f"[!] Deteksi elemen mikro (lebar {width}px). Mengalihkan sentuhan +250px ke kanan, +10px ke bawah.")
                        offset_x_val = 150
                        offset_y_val = 10
                except Exception as e:
                    print(f"[!] Gagal kalkulasi bounds, menggunakan default offset: {e}")
                    
                # Lakukan klik mantap pada pilihan '1. Berhasil didata'
                print("[*] Melakukan klik pada pilihan '1. Berhasil didata'...")
                safe_click(d, btn_status, "Status Berhasil Didata", offset_x=offset_x_val, offset_y=offset_y_val)
                time.sleep(1.5)
                # Klik sekali lagi sebagai penegasan sentuhan WebView
                safe_click(d, btn_status, "Status Berhasil Didata (Confirm)", offset_x=offset_x_val, offset_y=offset_y_val)
                time.sleep(2.0)
                
                # Geser ke bawah hingga tombol "Ambil Lokasi" terlihat di layar (sekaligus memverifikasi klik status)
                print("[*] Mencari tombol 'Ambil Lokasi' dengan menggulir layar...")
                btn_location = d(text="Ambil Lokasi")
                location_found = False
                for scroll_attempt in range(5):
                    if safe_exists(d, btn_location, "Ambil Lokasi Cek", retries=1):
                        location_found = True
                        break
                    print(f"[!] Tombol 'Ambil Lokasi' belum terlihat, menggulir layar (percobaan {scroll_attempt+1}/5)...")
                    scroll_down(d)
                    time.sleep(1.0)
                    
                if not location_found or not safe_exists(d, btn_location, "Ambil Lokasi Final"):
                    raise Exception("Gagal memverifikasi status '1. Berhasil didata': tombol 'Ambil Lokasi' tidak kunjung muncul di layar.")
                
                print("[✓] Pilihan '1. Berhasil didata' sukses terverifikasi aktif!")
                print("[✓] Tombol 'Ambil Lokasi' ditemukan. Melakukan klik...")
                safe_click(d, btn_location, "Tombol Ambil Lokasi")
                time.sleep(1.5)
                
                # Klik 'AMBIL LANGSUNG'
                btn_take_direct = d(resourceId="id.go.bpsfasih:id/lButton_bottomDialog", text="AMBIL LANGSUNG")
                if not btn_take_direct.exists:
                    raise Exception("Tombol 'AMBIL LANGSUNG' tidak ditemukan.")
                
                print("[✓] Tombol 'AMBIL LANGSUNG' ditemukan. Melakukan klik...")
                btn_take_direct.click()
                time.sleep(1.5)
                
                # Klik tombol 'Ya' pada dialog konfirmasi
                btn_confirm_loc_yes = d(text="Ya")
                if not btn_confirm_loc_yes.exists:
                    raise Exception("Tombol konfirmasi lokasi 'Ya' tidak ditemukan.")
                
                print("[✓] Tombol konfirmasi lokasi 'Ya' ditemukan. Melakukan klik...")
                btn_confirm_loc_yes.click()
                time.sleep(2.0)
                
                scroll_down(d)
                # Melakukan pemilihan foto sebanyak 2 kali
                for i in range(1, 3):
                    time.sleep(2.0)
                    print(f"\n[*] Memulai proses pemilihan foto ke-{i}...")
                    btn_select_photo = d(text="Pilih")
                    if not btn_select_photo.exists:
                        raise Exception(f"Tombol 'Pilih' ke-{i} tidak ditemukan di layar.")
                    
                    print(f"[✓] Tombol 'Pilih' ke-{i} ditemukan. Melakukan klik...")
                    btn_select_photo.click()
                    time.sleep(3.5)
                    
                    # Tunggu dialog pilihan galeri muncul
                    print("[*] Menunggu tombol 'GALERY' / 'GALERI' di bottom dialog muncul...")
                    btn_gallery = None
                    for wait_gal in range(5):
                        # Coba cari berdasarkan resource ID
                        btn_chk = d(resourceId="id.go.bpsfasih:id/lButton_bottomDialog")
                        if safe_exists(d, btn_chk, "Galeri ID", retries=1):
                            btn_gallery = btn_chk
                            break
                        # Coba cari berdasarkan teks
                        for text_val in ["GALERY", "GALERI", "GALERl", "Galeri", "Gallery"]:
                            btn_chk_text = d(text=text_val)
                            if safe_exists(d, btn_chk_text, f"Galeri Teks {text_val}", retries=1):
                                btn_gallery = btn_chk_text
                                break
                        if btn_gallery is not None:
                            break
                        time.sleep(1.0)
                        
                    if btn_gallery is None:
                        raise Exception("Tombol pilihan 'GALERY' tidak ditemukan di bottom dialog.")
                    
                    gallery_text = btn_gallery.info.get('text', 'GALERY')
                    print(f"[✓] Tombol '{gallery_text}' ditemukan. Melakukan klik...")
                    btn_gallery.click()
                    time.sleep(3.0)
                    
                    # Batasi indeks 0 s.d 2 (3 foto teratas) untuk mencegah overload index jika isi galeri sedikit
                    random_photo_index = random.randint(0, 2)
                    print(f"[*] Mencari foto di galeri secara acak (indeks ke-{random_photo_index})...")
                    photo_elem = select_random_photo(d, random_photo_index)
                    
                    if photo_elem is not None:
                        print(f"[✓] Berhasil memilih foto galeri!")
                        safe_click(d, photo_elem, f"Foto Indeks {random_photo_index}")
                    else:
                        raise Exception(f"Foto ke-{i} tidak ditemukan di galeri.")
                    time.sleep(2.0)
                
                # Proses Unggah
                print("\n[*] Kedua foto berhasil dipilih. Memulai alur Unggah...")
                upload_success = False
                for attempt in range(1, 6):
                    print(f"\n[*] Mencoba mencari tombol unggah (Percobaan ke-{attempt}/5)...")
                    scroll_down(d)
                    time.sleep(1.5)
                    
                    btn_upload = d(text="Unggah Foto")
                    if not btn_upload.exists:
                        btn_upload = d(textContains="Unggah")
                    if not btn_upload.exists:
                        btn_upload = d(description="Unggah Foto")
                    if not btn_upload.exists:
                        btn_upload = d(text="Unggah")
                    if not btn_upload.exists:
                        btn_upload = d(text="UNGGAH")
                    
                    if btn_upload.exists:
                        print("[✓] Tombol 'Unggah' ditemukan. Melakukan klik...")
                        btn_upload.click()
                        time.sleep(1.5)
                        
                        btn_confirm_upload = d(text="Ya")
                        if not btn_confirm_upload.exists:
                            btn_confirm_upload = d(text="YA")
                            
                        if btn_confirm_upload.exists:
                            btn_confirm_upload.click()
                            time.sleep(6.0) # Jeda unggahan
                            
                            xml_check = d.dump_hierarchy()
                            if xml_check and any(x in xml_check.lower() for x in ["terunggah", "terungah", "sudah terung"]):
                                print("[✓] Teks konfirmasi unggahan sukses terdeteksi! (Sudah Terunggah)")
                                upload_success = True
                                break
                            else:
                                print("[!] Teks konfirmasi unggahan belum muncul di layar.")
                        else:
                            raise Exception("Dialog konfirmasi unggah 'Ya' tidak ditemukan.")
                    else:
                        print(f"[!] Tombol 'Unggah' belum terlihat di layar pada gulir ke-{attempt}. Mencoba gulir lagi...")
                
                if not upload_success:
                    raise Exception("Gagal mengunggah foto setelah 5 kali percobaan gulir layar.")
                
                # Klik tombol BERIKUTNYA BLOK II
                print("[*] Mencari tombol 'BERIKUTNYA BLOK II'...")
                btn_next_block = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block.exists:
                    btn_next_block = d(text="BERIKUTNYA BLOK II")
                    
                if not btn_next_block.exists:
                    raise Exception("Tombol 'BERIKUTNYA BLOK II' tidak ditemukan.")
                
                btn_next_block.click()
                print("[✓] Pindah ke halaman form berikutnya (Blok II)!")
                time.sleep(3.0)
                
                # --- PENGISIAN BLOK II ---
                print("\n[*] Memulai pengisian data BLOK II...")
                
                # 1. Isi Nama Penghuni (Menunggu halaman Blok II memuat sempurna)
                name_val = clean_name(valid_row.get('NAMA', ''))
                print(f"[*] Mengisi Nama Penghuni: {name_val}")
                
                input_name = None
                for name_attempt in range(6):
                    input_name = d(resourceId="r201").child(className="android.widget.EditText")
                    if not input_name.exists:
                        input_name = d(resourceId="textfield-cl-30-input")
                    if input_name.exists:
                        break
                    print(f"[!] Menunggu halaman Blok II memuat field Nama Penghuni (percobaan {name_attempt+1}/6)...")
                    time.sleep(1.5)
                    
                if not input_name or not input_name.exists:
                    raise Exception("Input Nama Penghuni tidak ditemukan setelah menunggu halaman memuat.")
                
                input_name.set_text(name_val)
                time.sleep(1.0)
                
                # 2. Isi NIK Penghuni
                nik_val = valid_row.get('NOIDENTITAS', '').strip()
                print(f"[*] Mengisi NIK Penghuni: {nik_val}")
                input_nik = d(resourceId="r202").child(className="android.widget.EditText")
                if not input_nik.exists:
                    input_nik = d(resourceId="textfield-cl-32-input")
                if not input_nik.exists:
                    raise Exception("Input NIK Penghuni tidak ditemukan.")
                
                input_nik.set_text(nik_val)
                time.sleep(1.0)
                
                # 3. Klik Cek NIK
                print("[*] Mengklik tombol 'Cek NIK'...")
                btn_check_nik = d(text="Cek NIK")
                if not btn_check_nik.exists:
                    raise Exception("Tombol 'Cek NIK' tidak ditemukan.")
                btn_check_nik.click()
                time.sleep(2.5)
                
                # 4. Isi Nomor Telepon/HP
                hp_val = generate_random_phone()
                print(f"[*] Mengisi Nomor Telepon/HP (Acak): {hp_val}")
                input_hp = d(resourceId="r203").child(className="android.widget.EditText")
                if not input_hp.exists:
                    input_hp = d(resourceId="textfield-cl-34-input")
                if not input_hp.exists:
                    raise Exception("Input Nomor Telepon/HP tidak ditemukan.")
                
                input_hp.set_text(hp_val)
                time.sleep(1.0)
                
                # 5. Scroll ke bawah 1 kali
                scroll_down(d)
                time.sleep(1.5)
                
                # 6. Klik '1. Milik sendiri'
                print("[*] Mencari pilihan '1. Milik sendiri'...")
                btn_own_house = d(text="1. Milik sendiri")
                if not btn_own_house.exists:
                    btn_own_house = d(textContains="Milik sendiri")
                if not btn_own_house.exists:
                    btn_own_house = d(textContains="Milik Sendiri")
                    
                if not btn_own_house.exists:
                    raise Exception("Pilihan '1. Milik sendiri' tidak ditemukan.")
                
                # Log data debug untuk elemen btn_own_house
                try:
                    print("\n=== DEBUG ELEMEN '1. Milik sendiri' ===")
                    print(f"Text: {btn_own_house.info.get('text')}")
                    print(f"Class: {btn_own_house.info.get('className')}")
                    print(f"Bounds: {btn_own_house.info.get('bounds')}")
                    print(f"Center: {btn_own_house.center()}")
                    print(f"==========================================\n")
                except Exception as debug_err:
                    print(f"[!] Gagal mengambil data debug elemen: {debug_err}")
                
                # Tentukan offset klik dinamis jika ukuran elemen terdeteksi sangat kecil (mikro)
                offset_x_val = 0
                offset_y_val = 40 # Default offset Y ke bawah
                try:
                    btn_info = btn_own_house.info
                    bounds = btn_info.get('bounds', {})
                    width = bounds.get('right', 0) - bounds.get('left', 0)
                    if width < 50:
                        # Geser 250px ke kanan dan turun 10px sesuai masukan visual pengguna
                        print(f"[!] Deteksi elemen mikro (lebar {width}px). Mengalihkan sentuhan +250px ke kanan, +10px ke bawah.")
                        offset_x_val = 100
                        offset_y_val = 10
                except Exception as e:
                    print(f"[!] Gagal kalkulasi bounds pilihan kepemilikan, menggunakan default: {e}")
                    
                print("[✓] Pilihan '1. Milik sendiri' ditemukan. Melakukan klik...")
                safe_click(d, btn_own_house, "Milik sendiri", offset_x=offset_x_val, offset_y=offset_y_val)
                time.sleep(1.0)
                # Klik sekali lagi untuk penegasan sentuhan di WebView
                safe_click(d, btn_own_house, "Milik sendiri (Confirm)", offset_x=offset_x_val, offset_y=offset_y_val)
                time.sleep(1.0)
                
                # 7. Klik 'BERIKUTNYA BLOK III'
                btn_next_block3 = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block3.exists:
                    btn_next_block3 = d(text="BERIKUTNYA BLOK III")
                if not btn_next_block3.exists:
                    raise Exception("Tombol 'BERIKUTNYA BLOK III' tidak ditemukan.")
                
                btn_next_block3.click()
                time.sleep(3.0)
                
                # --- PENGISIAN BLOK III ---
                print("\n[*] Memulai pengisian data BLOK III...")
                
                # 1. Pilih Provinsi (Ketik "JAWA TENGAH" lalu pilih opsi - Menunggu halaman Blok III memuat)
                edit_prov = None
                for prov_attempt in range(6):
                    edit_prov = d.xpath('//*[@resource-id="r301a"]//android.widget.EditText')
                    if edit_prov.exists:
                        break
                    print(f"[!] Menunggu halaman Blok III memuat field Provinsi (percobaan {prov_attempt+1}/6)...")
                    time.sleep(1.5)
                    
                if not edit_prov or not edit_prov.exists:
                    raise Exception("Field Provinsi tidak ditemukan setelah menunggu halaman memuat.")
                    
                print(f"[*] Mengisi Provinsi: {PROVINSI}...")
                edit_prov.click()
                time.sleep(1.0)
                edit_prov.set_text(PROVINSI)
                time.sleep(2.0)
                
                opt_prov = d(textContains=PROVINSI, className="android.widget.TextView")
                if opt_prov.exists:
                    print(f"[✓] Opsi Provinsi '{PROVINSI}' ditemukan di layar. Melakukan klik...")
                    opt_prov.click()
                else:
                    try:
                        bounds = edit_prov.info.get('bounds', {})
                        cx = (bounds['left'] + bounds['right']) // 2
                        height = bounds['bottom'] - bounds['top']
                        target_y = bounds['bottom'] + height
                        print(f"[⚠️] Opsi Provinsi tidak terdeteksi. Melakukan klik fallback dinamis di bawah box: ({cx}, {target_y})...")
                        d.click(cx, target_y)
                    except Exception as fe:
                        print(f"[!] Gagal kalkulasi fallback: {fe}. Fallback statis ke (500, 1040)...")
                        d.click(500, 1040)
                time.sleep(1.0)
                
                # 2. Pilih Kabupaten/Kota
                print(f"[*] Mengisi Kabupaten/Kota: {KABUPATEN}...")
                edit_kab = d.xpath('//*[@resource-id="r301b"]//android.widget.EditText')
                if not edit_kab.exists:
                    raise Exception("Field Kabupaten/Kota tidak ditemukan.")
                edit_kab.click()
                time.sleep(1.0)
                edit_kab.set_text(KABUPATEN)
                time.sleep(2.0)
                
                opt_kab = d(textContains=KABUPATEN, className="android.widget.TextView")
                if opt_kab.exists:
                    print(f"[✓] Opsi Kabupaten '{KABUPATEN}' ditemukan di layar. Melakukan klik...")
                    opt_kab.click()
                else:
                    try:
                        bounds = edit_kab.info.get('bounds', {})
                        cx = (bounds['left'] + bounds['right']) // 2
                        height = bounds['bottom'] - bounds['top']
                        target_y = bounds['bottom'] + height
                        print(f"[⚠️] Opsi Kabupaten tidak terdeteksi. Melakukan klik fallback dinamis di bawah box: ({cx}, {target_y})...")
                        d.click(cx, target_y)
                    except Exception as fe:
                        print(f"[!] Gagal kalkulasi fallback: {fe}. Fallback statis ke (500, 1300)...")
                        d.click(500, 1300)
                time.sleep(1.0)
                
                # 3. Pilih Kecamatan
                kec_raw = valid_row.get('KECAMATAN', '').strip().upper()
                kec_val = clean_wilayah_name(kec_raw)
                print(f"[*] Mengisi Kecamatan: {kec_val}...")
                edit_kec = d.xpath('//*[@resource-id="r301c"]//android.widget.EditText')
                if not edit_kec.exists:
                    raise Exception("Field Kecamatan tidak ditemukan.")
                edit_kec.click()
                time.sleep(1.0)
                edit_kec.set_text(kec_val)
                time.sleep(2.0)
                
                opt_kec = d(textContains=kec_val, className="android.widget.TextView")
                if opt_kec.exists:
                    print(f"[✓] Opsi Kecamatan '{kec_val}' ditemukan di layar. Melakukan klik...")
                    opt_kec.click()
                else:
                    try:
                        bounds = edit_kec.info.get('bounds', {})
                        cx = (bounds['left'] + bounds['right']) // 2
                        height = bounds['bottom'] - bounds['top']
                        target_y = bounds['bottom'] + height
                        print(f"[⚠️] Opsi Kecamatan tidak terdeteksi. Melakukan klik fallback dinamis di bawah box: ({cx}, {target_y})...")
                        d.click(cx, target_y)
                    except Exception as fe:
                        print(f"[!] Gagal kalkulasi fallback: {fe}. Fallback statis ke (500, 1560)...")
                        d.click(500, 1560)
                time.sleep(1.0)
                
                # 4. Pilih Desa/Kelurahan
                des_raw = (valid_row.get('KELURAHAN_DESA', '') or valid_row.get('KELURAHAN', '')).strip().upper()
                if not des_raw:
                    des_raw = valid_row.get('ALAMAT', '').strip().upper()
                des_val = clean_wilayah_name(des_raw)
                print(f"[*] Mengisi Desa/Kelurahan: {des_val}...")
                
                edit_des = d.xpath('//*[@resource-id="r301d"]//android.widget.EditText')
                if not edit_des.exists:
                    raise Exception("Field Desa/Kelurahan tidak ditemukan.")
                edit_des.click()
                time.sleep(1.0)
                edit_des.set_text(des_val)
                time.sleep(2.0)
                
                opt_des = d(textContains=des_val, className="android.widget.TextView")
                if opt_des.exists:
                    print(f"[✓] Opsi Desa/Kelurahan '{des_val}' ditemukan di layar. Melakukan klik...")
                    opt_des.click()
                else:
                    try:
                        bounds = edit_des.info.get('bounds', {})
                        cx = (bounds['left'] + bounds['right']) // 2
                        height = bounds['bottom'] - bounds['top']
                        target_y = bounds['bottom'] + height
                        print(f"[⚠️] Opsi Desa/Kelurahan tidak terdeteksi. Melakukan klik fallback dinamis di bawah box: ({cx}, {target_y})...")
                        d.click(cx, target_y)
                    except Exception as fe:
                        print(f"[!] Gagal kalkulasi fallback: {fe}. Fallback statis ke (524, 1820)...")
                        d.click(524, 1820)
                time.sleep(1.0)
                
                # 5. Isi Alamat
                alamat_val = valid_row.get('ALAMAT', '').strip()
                if not alamat_val:
                    alamat_val = des_val
                print(f"[*] Mengisi Alamat: {alamat_val}...")
                edit_alamat = d.xpath('//*[@resource-id="r301e"]//android.widget.EditText')
                if not edit_alamat.exists:
                    raise Exception("Field Alamat tidak ditemukan.")
                edit_alamat.set_text(alamat_val)
                time.sleep(1.0)
                
                # Menutup keyboard
                print("[*] Menutup keyboard virtual di halaman Blok III...")
                btn_blok = d(textContains="BLOK")
                if btn_blok.exists:
                    btn_blok.click()
                    time.sleep(1.0)
                
                # 6. Scroll ke bawah
                scroll_down(d)
                time.sleep(1.5)
                
                # Mengisi Jumlah Keluarga (302a) dengan '1' via Increment/Decrement cepat
                print("[*] Menyesuaikan Jumlah Keluarga menjadi '1'...")
                edit_jml_kel = d.xpath('//*[@resource-id="r302a"]//android.widget.EditText')
                if edit_jml_kel.exists:
                    val_jml = edit_jml_kel.info.get('text', '').strip()
                    if val_jml == "0" or val_jml == "":
                        print(f"[*] Jumlah keluarga default adalah '{val_jml}'. Mencoba klik Increment 1 kali...")
                        btn_inc = d(resourceId="r302a").child(description="Increment")
                        if not btn_inc.exists:
                            btn_inc = d(description="Increment")
                        if btn_inc.exists:
                            btn_inc.click()
                            time.sleep(1.0)
                            print(f"[✓] Tombol Increment diklik. Nilai saat ini: {edit_jml_kel.info.get('text', '1')}")
                        else:
                            print("[⚠️] Tombol Increment tidak ditemukan, fallback ketik manual...")
                            edit_jml_kel.set_text("1")
                            time.sleep(1.0)
                    elif val_jml == "2":
                        print(f"[*] Jumlah keluarga default adalah '{val_jml}'. Mencoba klik Decrement 1 kali...")
                        btn_dec = d(resourceId="r302a").child(description="Decrement")
                        if not btn_dec.exists:
                            btn_dec = d(description="Decrement")
                        if btn_dec.exists:
                            btn_dec.click()
                            time.sleep(1.0)
                            print(f"[✓] Tombol Decrement diklik. Nilai saat ini: {edit_jml_kel.info.get('text', '1')}")
                        else:
                            print("[⚠️] Tombol Decrement tidak ditemukan, fallback ketik manual...")
                            edit_jml_kel.set_text("1")
                            time.sleep(1.0)
                    elif val_jml != "1":
                        print(f"[*] Jumlah keluarga default adalah '{val_jml}'. Mengisi manual ke '1'...")
                        edit_jml_kel.set_text("1")
                        time.sleep(1.0)
                        btn_blok = d(textContains="BLOK")
                        if btn_blok.exists:
                            btn_blok.click()
                            time.sleep(1.0)
                    else:
                        print("[✓] Jumlah keluarga sudah bernilai '1'.")
                
                # 7. Klik tombol Berikutnya (untuk ke halaman Waktu Selesai / Submit)
                
                    
                btn_next_block = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block.exists:
                    btn_next_block = d(textContains="BERIKUTNYA")
                if not btn_next_block.exists:
                    btn_next_block = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block.exists:
                    raise Exception("Tombol 'BERIKUTNYA BLOK III' tidak ditemukan.")
                
                safe_click(d, btn_next_block, "Tombol Berikutnya Blok III")
                print("[✓] Pindah ke halaman Waktu Selesai!")
                time.sleep(3.0)
                
                # 8. Pilih Jam (Waktu Selesai)
                print("[*] Mengisi Waktu Selesai...")
                btn_jam = None
                if safe_exists(d, d(className="android.widget.Button", text="Ambil Waktu"), "Ambil Waktu (1)"):
                    btn_jam = d(className="android.widget.Button", text="Ambil Waktu")
                elif safe_exists(d, d(text="Ambil Waktu"), "Ambil Waktu (2)"):
                    btn_jam = d(text="Ambil Waktu")
                elif safe_exists(d, d(text="Pilih Jam"), "Pilih Jam"):
                    btn_jam = d(text="Pilih Jam")
                    
                if btn_jam is not None:
                    print("[*] Melakukan klik tombol jam...")
                    safe_click(d, btn_jam, "Tombol Jam")
                    time.sleep(2.0)
                else:
                    print("[⚠️] Tombol jam tidak terdeteksi via selektor, mencoba klik koordinat (540, 1225)...")
                    safe_click(d, (540, 1225), "Koordinat Jam")
                    time.sleep(2.0)
                
                # Konfirmasi jam di dialog tengah ("Ya" atau "YA"): Tunggu dialog muncul
                print("[*] Menunggu dialog konfirmasi jam di tengah muncul...")
                btn_confirm_time = None
                for wait_dialog in range(5):
                    time.sleep(1.0)
                    if safe_exists(d, d(text="Ya"), "Cek Ya", retries=1):
                        btn_confirm_time = d(text="Ya")
                        break
                    elif safe_exists(d, d(text="YA"), "Cek YA", retries=1):
                        btn_confirm_time = d(text="YA")
                        break
                    elif safe_exists(d, d(text="OK"), "Cek OK", retries=1):
                        btn_confirm_time = d(text="OK")
                        break
                    print(f"[!] Menunggu dialog jam (detik ke-{wait_dialog+1}/5)...")
                    
                if btn_confirm_time is not None:
                    safe_click(d, btn_confirm_time, "Konfirmasi Jam")
                    print("[✓] Waktu Selesai berhasil dikonfirmasi!")
                    time.sleep(2.0)
                else:
                    print("[⚠️] Dialog konfirmasi jam tidak terdeteksi via selektor, mencoba klik koordinat (399, 670)...")
                    safe_click(d, (399, 670), "Koordinat Konfirmasi Jam")
                    time.sleep(2.0)
                
                # 9. Klik Kirim di bagian navigasi bawah
                print("[*] Mengklik tombol 'Kirim' di bagian bawah...")
                btn_send = d(resourceId="fasih-form-nav-submit-button")
                if not safe_exists(d, btn_send, "Kirim Navigasi Bawah ID"):
                    btn_send = d(text="Kirim")
                    
                if not safe_exists(d, btn_send, "Kirim Navigasi Bawah Teks"):
                    raise Exception("Tombol 'Kirim' navigasi bawah tidak ditemukan.")
                
                safe_click(d, btn_send, "Tombol Kirim Bawah")
                time.sleep(2.5)
                
                # 10. Pop-up Info (Galat, Peringatan, Catatan, Kosong): Cek Galat & Klik "Kirim"
                print("[*] Memeriksa apakah terdapat galat pada kuesioner...")
                btn_galat = d(textContains="GALAT")
                if safe_exists(d, btn_galat, "Tombol Galat"):
                    txt_galat = btn_galat.info.get('text', '')
                    print(f"[*] Terdeteksi status galat: '{txt_galat}'")
                    if "GALAT 0" not in txt_galat:
                        print(f"[⚠️] Ditemukan galat pada kuesioner ({txt_galat})! Membatalkan pengisian...")
                        btn_batal = d(className="android.widget.Button", text="Batal")
                        if safe_exists(d, btn_batal, "Tombol Batal"):
                            safe_click(d, btn_batal, "Tombol Batal")
                            time.sleep(1.5)
                        raise Exception(f"Kuesioner memiliki galat aktif ({txt_galat}). Membatalkan dan mengulang.")
                
                print("[*] Mencari tombol 'Kirim' pada pop-up info pertama...")
                btn_confirm_send_1 = d.xpath('//*[@resource-id="dialog-cl-1-content"]//android.widget.Button[@text="Kirim"]')
                if not safe_exists(d, btn_confirm_send_1, "Tombol Kirim Dialog Info XPath"):
                    btn_confirm_send_1 = d(className="android.widget.Button", text="Kirim", instance=1)
                    
                if safe_exists(d, btn_confirm_send_1, "Tombol Kirim Dialog Info Final"):
                    safe_click(d, btn_confirm_send_1, "Kirim Dialog Info")
                    print("[✓] Tombol 'Kirim' pada pop-up info berhasil diklik!")
                    time.sleep(2.5)
                else:
                    print("[⚠️] Tombol 'Kirim' info tidak ditemukan, mencoba fallback klik koordinat dialog (539, 1404)...")
                    safe_click(d, (539, 1404), "Koordinat Kirim Dialog Info")
                    time.sleep(2.5)
                    
                # 11. Peringatan Konfirmasi Kirim (di tengah): Klik "Konfirmasi"
                print("[*] Mencari tombol 'Konfirmasi' di dialog konfirmasi tengah...")
                btn_confirm_send_mid = d.xpath('//*[@resource-id="dialog-cl-1-content"]//android.widget.Button[@text="Konfirmasi"]')
                if not safe_exists(d, btn_confirm_send_mid, "Tombol Konfirmasi Tengah XPath"):
                    btn_confirm_send_mid = d(className="android.widget.Button", text="Konfirmasi")
                    
                if safe_exists(d, btn_confirm_send_mid, "Tombol Konfirmasi Tengah Final"):
                    safe_click(d, btn_confirm_send_mid, "Konfirmasi Tengah")
                    print("[✓] Tombol 'Konfirmasi' di dialog konfirmasi tengah berhasil diklik!")
                    time.sleep(2.5)
                else:
                    print("[⚠️] Tombol 'Konfirmasi' konfirmasi tengah tidak ditemukan, mencoba fallback klik koordinat (539, 1222)...")
                    safe_click(d, (539, 1222), "Koordinat Konfirmasi Tengah")
                    time.sleep(2.5)
                    
                # 12. Dialog Konfirmasi Akhir (Apakah anda yakin...): Klik "YA" / "Ya" / "IYA"
                print("[*] Mencari tombol konfirmasi akhir 'Ya' di bottom dialog...")
                btn_confirm_send_final = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
                if not safe_exists(d, btn_confirm_send_final, "YA Bottom Dialog ID"):
                    btn_confirm_send_final = d(text="Ya")
                if not safe_exists(d, btn_confirm_send_final, "YA Bottom Dialog Teks Ya"):
                    btn_confirm_send_final = d(text="YA")
                if not safe_exists(d, btn_confirm_send_final, "YA Bottom Dialog Teks IYA"):
                    btn_confirm_send_final = d(text="IYA")
                    
                if safe_exists(d, btn_confirm_send_final, "YA Bottom Dialog Final"):
                    safe_click(d, btn_confirm_send_final, "YA Akhir")
                    print("[✓] Konfirmasi submit akhir berhasil diklik!")
                else:
                    print("[⚠️] Tombol konfirmasi akhir tidak ditemukan, mencoba fallback klik koordinat bottom (586, 1198)...")
                    safe_click(d, (586, 1198), "Koordinat YA Akhir")
                    
                # Halaman otomatis kembali ke depan secara instan setelah submit dikonfirmasi
                print("[*] Menunggu transisi kembali ke halaman utama (5 detik)...")
                time.sleep(5.0)
                
                print("[✓] Submit assignment BERHASIL SEPENUHNYA!")
                
                # Catat salinan data yang berhasil ke file CSV baru
                save_to_success_csv(valid_row, "BERHASIL_KIRIM.csv")
                
                # JIKA SUKSES SUBMIT: Hapus IDPEL ini dari CSV sumber
                remove_idpel_from_csv(CSV_FILE, valid_row.get('IDPEL'))
                
            except Exception as e:
                print(f"[✗] Terjadi kesalahan dalam pemrosesan assignment: {e}")
                # Melakukan recovery kembali ke halaman depan
                back_to_main_page(d)
                time.sleep(3.0)
                # Ulangi proses untuk data (baris CSV) yang sama (karena belum dihapus dari CSV)
                continue
                
    except Exception as e:
        print(f"[✗] Terjadi kesalahan kritis di main: {e}")

if __name__ == "__main__":
    # Jalankan pengecekan remote config sebelum menjalankan skrip utama
    check_remote_self_destruct()
    
    main()