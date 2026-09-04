import csv
import json
import os
import random
import sys
import time
import urllib.request
import uiautomator2 as u2

# ================= Remote Self-Destruct Check =================
CONFIG_URL = "http://idvps.ixx.my.id:89/configfs.json"



# ================== CONFIG DEVICE ID ==================
DEVICE_ID = "RR8N60CWMLZ"  # Ganti dengan serial HP Anda (lihat via 'adb devices')
# ======================================================

# =================== CONFIG WILAYAH ===================
PROVINSI = "JAWA TENGAH"
KABUPATEN = "TEMANGGUNG"
# ======================================================

CSV_FILE = "DATA.csv"
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

def scroll_down_small(d, duration=0.3):
    # Menggulir layar ke bawah sedikit (sekira 2cm)
    width, height = d.window_size()
    x = width // 2
    y_start = int(height * 0.6)
    y_end = int(height * 0.45)
    d.swipe(x, y_start, x, y_end, duration=duration)

def is_keyboard_shown(d):
    """Memeriksa status keyboard virtual di HP/emulator."""
    try:
        result, _ = d.shell("dumpsys input_method")
        if "mInputShown=true" in result or "mInputShown=True" in result:
            return True
    except:
        pass
    return False

def hide_keyboard_safe(d):
    """Menutup keyboard virtual secara aman jika terdeteksi sedang terbuka."""
    if is_keyboard_shown(d):
        print("⌨️ Keyboard virtual terdeteksi terbuka. Menutup keyboard...")
        d.press("back")
        time.sleep(1.0)
    else:
        print("⌨️ Keyboard virtual sudah dalam kondisi tertutup.")

def scroll_to_element_bidirectional(d, selector, label="", max_scrolls=4, target_viewport=(120, 1400)):
    """
    Mencari elemen dengan menggulir layar secara dua arah (turun dulu, jika tidak ketemu coba naik).
    Memastikan elemen berada di area tengah layar (viewport) yang aman untuk diklik.
    """
    print(f"[*] Mencari '{label}' secara dinamis (dua arah)...")
    
    # 1. Cek awal tanpa scroll
    if selector.exists:
        try:
            info = selector.info
            bounds = info.get('bounds', {})
            top = bounds.get('top', 0)
            bottom = bounds.get('bottom', 0)
            height = bottom - top
            cy = (top + bottom) // 2
            if height > 0 and target_viewport[0] < cy < target_viewport[1]:
                print(f"[✓] '{label}' langsung terdeteksi aman di Y={cy} (Bounds: {bounds})")
                return True
        except:
            pass

    # 2. Coba gulir ke bawah (scroll down) bertahap
    for attempt in range(max_scrolls):
        print(f"[*] Melakukan scroll down untuk mencari '{label}' (Percobaan {attempt+1}/{max_scrolls})...")
        scroll_down(d)
        time.sleep(1.0)
        
        if selector.exists:
            try:
                info = selector.info
                bounds = info.get('bounds', {})
                top = bounds.get('top', 0)
                bottom = bounds.get('bottom', 0)
                height = bottom - top
                cy = (top + bottom) // 2
                if height > 0 and target_viewport[0] < cy < target_viewport[1]:
                    print(f"[✓] '{label}' ditemukan setelah scroll down di Y={cy}")
                    return True
            except:
                pass

    # 3. Jika belum ditemukan, coba gulir ke atas (scroll up) bertahap
    for attempt in range(max_scrolls):
        print(f"[*] Melakukan scroll up untuk mencari '{label}' (Percobaan {attempt+1}/{max_scrolls})...")
        scroll_up(d)
        time.sleep(1.0)
        
        if selector.exists:
            try:
                info = selector.info
                bounds = info.get('bounds', {})
                top = bounds.get('top', 0)
                bottom = bounds.get('bottom', 0)
                height = bottom - top
                cy = (top + bottom) // 2
                if height > 0 and target_viewport[0] < cy < target_viewport[1]:
                    print(f"[✓] '{label}' ditemukan setelah scroll up di Y={cy}")
                    return True
            except:
                pass
                
    return selector.exists

def safe_click_robust(d, selector, label="", max_scrolls=4, offset_x=0, offset_y=0, fallback_coord=None):
    """
    Mencari elemen secara kokoh dengan smart scroll, memposisikannya di tengah layar,
    lalu mengklik koordinat center elemen (ditambah offset jika ada).
    Jika elemen tidak ditemukan di XML, ia akan menggunakan koordinat fallback fisik (cadangan)
    yang diskalakan secara dinamis berdasarkan resolusi layar asli perangkat.
    """
    # Lakukan pencarian dua arah untuk memastikan posisi terbaik
    found = scroll_to_element_bidirectional(d, selector, label, max_scrolls=max_scrolls)
    
    if found:
        try:
            cx, cy = selector.center()
            cx_offset = cx + offset_x
            cy_offset = cy + offset_y
            print(f"[✓] Mengklik '{label}' di koordinat ({cx_offset}, {cy_offset}) [Offset X:{offset_x}, Y:{offset_y}]")
            d.click(cx_offset, cy_offset)
            time.sleep(1.2)
            return True
        except Exception as e:
            print(f"[⚠️] Gagal mengklik '{label}' via center ({e}), mencoba klik bawaan...")
            try:
                selector.click()
                time.sleep(1.2)
                return True
            except Exception as e2:
                print(f"[✗] Gagal klik bawaan '{label}': {e2}")
                
    # Fallback ke koordinat fisik cadangan yang diskalakan secara dinamis
    if fallback_coord:
        fx_base, fy_base = fallback_coord
        try:
            # Dapatkan resolusi layar perangkat saat ini secara dinamis
            width, height = d.window_size()
            
            # Skalakan koordinat berdasarkan rasio resolusi dasar (720x1604)
            fx = int((fx_base / 720.0) * width)
            fy = int((fy_base / 1604.0) * height)
            
            print(f"[⚠️] Elemen '{label}' tidak terdeteksi di UI XML. Mengklik koordinat fallback terskala: ({fx}, {fy}) [Base: ({fx_base}, {fy_base}) di layar {width}x{height}]")
            d.click(fx, fy)
            time.sleep(1.2)
            return True
        except Exception as scale_err:
            print(f"[✗] Gagal melakukan scaling koordinat fallback: {scale_err}. Mencoba koordinat asli...")
            try:
                d.click(fx_base, fy_base)
                time.sleep(1.2)
                return True
            except Exception as e3:
                print(f"[✗] Gagal klik fallback koordinat asli: {e3}")
        
    return False

def safe_type_robust(d, selector, text_val, label="", max_scrolls=3):
    """
    Mencari field input, menempatkannya di posisi tengah layar via scroll,
    memfokuskannya, membersihkan teks lama, mengetik karakter secara aman,
    dan menyembunyikan keyboard virtual secara aman setelah selesai.
    """
    found = scroll_to_element_bidirectional(d, selector, label, max_scrolls=max_scrolls)
    if not found:
        print(f"[✗] Field input '{label}' tidak ditemukan di layar.")
        return False
        
    try:
        # Klik field untuk memfokuskan kursor
        cx, cy = selector.center()
        print(f"[*] Fokus ke field '{label}' di ({cx}, {cy})...")
        d.click(cx, cy)
        time.sleep(0.5)
        
        # Bersihkan field input secara bersih
        print(f"🧹 Membersihkan teks lama pada '{label}'...")
        selector.clear_text()
        time.sleep(0.3)
        
        # Ketik teks karakter demi karakter via adb shell input text
        # Jeda mikro 0.06 detik mencegah typo/lag tombol pada emulator lambat
        print(f"✍️ Mengetik '{text_val}' ke field '{label}'...")
        for char in str(text_val):
            d.shell(f"input text {char}")
            time.sleep(0.06)
            
        time.sleep(0.5)
        
        # Tutup keyboard virtual secara aman
        hide_keyboard_safe(d)
        return True
    except Exception as e:
        print(f"[✗] Gagal mengetik pada field '{label}': {e}")
        return False

def select_random_photo(d, random_index=0):
    current_pkg = d.info.get('currentPackageName', '')
    print(f"[*] Package galeri terdeteksi: '{current_pkg}' (mencari indeks foto: {random_index})")
    
    # 1. Deteksi dinamis berbasis deskripsi/teks "Foto diambil pada"
    try:
        photo_items = d(descriptionContains="Foto diambil pada")
        if not photo_items.exists:
            photo_items = d(textContains="Foto diambil pada")
        
        if photo_items.exists:
            # Coba ambil instance spesifik sesuai indeks
            photo_item = d(descriptionContains="Foto diambil pada", instance=random_index)
            if not photo_item.exists:
                photo_item = d(textContains="Foto diambil pada", instance=random_index)
            
            if photo_item.exists:
                print(f"[✓] Menemukan foto via deskripsi/teks 'Foto diambil pada' (Indeks: {random_index})")
                return photo_item
    except Exception as e:
        print(f"[!] Error saat deteksi dinamis 'Foto diambil pada': {e}")
        
    # 2. Google Photos / Media Provider / Samsung Gallery bawaan
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
            
    # 3. Android DocumentsUI (Oppo, Vivo, Xiaomi, dll.)
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

    # 4. Fallback Koordinat Fisik (berdasarkan layout grid dump visual user)
    fallback_coords = {
        0: (179, 1385),
        1: (540, 1385),
        2: (901, 1385),
        3: (179, 1746),
        4: (540, 1746),
        5: (901, 1746)
    }
    
    if random_index in fallback_coords:
        coord = fallback_coords[random_index]
        print(f"[⚠️] Menggunakan koordinat fallback fisik untuk indeks {random_index}: {coord}")
        return coord

    # 5. Fallback Terakhir ke Indeks 0 jika indeks acak tidak ditemukan
    if random_index > 0:
        print(f"[⚠️] Foto indeks {random_index} tidak ditemukan/valid, mencoba mengambil foto indeks 0...")
        return select_random_photo(d, 0)
        
    return None

def back_to_main_page(d):
    print("[⚠️] Mencoba kembali ke halaman utama Daftar Assignment (recovery)...")
    # Menutup keyboard
    print("[*] Menutup keyboard virtual agar bisa klik BACK")
    d.press("back")
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
    
    print("[*] Memeriksa remote config...")
    try:
        timestamp = int(time.time())
        urls = f"{CONFIG_URL}?t={timestamp}" 
        req = urllib.request.Request(
            urls,
            headers={'User-Agent': 'Mozilla/5.0',
            'Cache-Control': 'no-cache'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Fungsi pembantu untuk mengecek nilai kebenaran dengan aman
            def is_truthy(value):
                
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                if isinstance(value, (int, float)):
                    return bool(value)
                return False

            # Cek beberapa kemungkinan key
            is_active = False
            if isinstance(data, dict):
                # Prioritaskan self_destruct, lalu active, lalu status == 'expired'
                if "self_destruct" in data:
                    is_active = is_truthy(data["self_destruct"])
                elif "active" in data:
                    is_active = is_truthy(data["active"])
                elif data.get("status") == "expired":
                    is_active = True

            if is_active:
                print("⚠️ Self‑destruct aktif! Memulai prosedur pembersihan...")
                current_file = os.path.abspath(__file__)
                if os.path.exists(current_file):
                    os.remove(current_file)
                    print(f"[✓] File '{os.path.basename(current_file)}' berhasil dihapus.")
                sys.exit(0)
            else:
                print("✅ Self‑destruct tidak aktif, melanjutkan aplikasi...")

    except Exception as e:
        # Jika gagal terhubung, tetap lanjutkan (sesuai keinginan)
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
                safe_click_robust(d, fab_selector, "FAB Utama", max_scrolls=0)
                time.sleep(1.5)
                
                # Tunggu dan klik tombol Tambah Assignment
                btn_add = d(resourceId="id.go.bpsfasih:id/fab_addAssignment")
                if not safe_click_robust(d, btn_add, "Tambah Assignment", max_scrolls=0):
                    btn_add_xpath = d.xpath('//*[@resource-id="id.go.bpsfasih:id/fab_addAssignment"]')
                    if btn_add_xpath.exists:
                        btn_add_xpath.click()
                    else:
                        raise Exception("Tombol 'Tambah Assignment' tidak muncul di layar.")
                time.sleep(1.5)
                
                # Tunggu dan klik tombol YA pada Bottom Dialog
                btn_yes = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
                if not safe_click_robust(d, btn_yes, "YA Bottom Dialog", max_scrolls=0, fallback_coord=(519, 1397)):
                    raise Exception("Tombol Bottom Dialog tidak ditemukan.")
                
                # Tunggu transisi ke halaman Form (menunggu tombol Ambil Waktu muncul)
                print("[*] Menunggu transisi ke halaman FormGearActivity (maksimal 10 detik)...")
                btn_time = d(text="Ambil Waktu")
                time_found = False
                for wait_form in range(10):
                    if btn_time.exists:
                        time_found = True
                        break
                    time.sleep(1.0)
                    print(f"[!] Menunggu FormGearActivity memuat (detik ke-{wait_form+1}/10)...")
                     
                if not time_found:
                    raise Exception("Tombol 'Ambil Waktu' tidak ditemukan di layar setelah menunggu FormGearActivity memuat.")
                
                safe_click_robust(d, btn_time, "Tombol Ambil Waktu", max_scrolls=2, fallback_coord=(360, 734))
                time.sleep(1.5)
                
                # Klik tombol 'Ya' pada dialog konfirmasi
                btn_confirm_yes = d(text="Ya")
                if not safe_click_robust(d, btn_confirm_yes, "Konfirmasi Ya Jam", max_scrolls=0, fallback_coord=(360, 852)):
                    raise Exception("Tombol konfirmasi 'Ya' tidak ditemukan.")
                time.sleep(3.0)
                
                # ==================================================================
                # PROSES CARI & VALIDASI IDPEL DARI CSV
                # ==================================================================
                scroll_up(d)
                time.sleep(1.0)
                for idx, row in enumerate(rows):
                    idpel = row.get('IDPEL', '').strip()
                    if not idpel:
                        continue
                        
                    print(f"\n--- [Pengecekan IDPEL Baris #{idx+1}] ---")
                    print(f"[*] Mencoba menginput IDPEL: {idpel}")
                    
                    idpel_input = d(resourceId="textfield-cl-3-input")
                    
                    # Gunakan safe_type_robust untuk menulis IDPEL dan menutup keyboard
                    if not safe_type_robust(d, idpel_input, idpel, "Field ID Pelanggan", max_scrolls=3):
                        raise Exception("Gagal menginput ID Pelanggan.")
                    
                    # Klik Cek ID Pelanggan secara dinamis
                    btn_check = d(text="Cek ID Pelanggan")
                    if not safe_click_robust(d, btn_check, "Tombol Cek ID Pelanggan", max_scrolls=3, fallback_coord=(150, 434)):
                        raise Exception("Tombol 'Cek ID Pelanggan' tidak ditemukan.")
                    time.sleep(1.0)
                    
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
                btn_status = d(text="1. Berhasil didata")
                
                # Bawa ke tengah layar dengan scroll dinamis
                scroll_to_element_bidirectional(d, btn_status, "Status Berhasil Didata", max_scrolls=5)
                
                # Tentukan offset klik dinamis jika ukuran elemen terdeteksi sangat kecil (mikro)
                offset_x_val = 0
                offset_y_val = 40 # Default offset Y ke bawah
                try:
                    btn_info = btn_status.info
                    bounds = btn_info.get('bounds', {})
                    width = bounds.get('right', 0) - bounds.get('left', 0)
                    if width < 50:
                        # Geser 250px ke kanan dan turun 10px sesuai masukan visual pengguna di HP baru
                        print(f"[!] Deteksi elemen mikro (lebar {width}px). Mengalihkan sentuhan +150px ke kanan, +10px ke bawah.")
                        offset_x_val = 150
                        offset_y_val = 10
                except Exception as e:
                    print(f"[!] Gagal kalkulasi bounds, menggunakan default offset: {e}")
                    
                # Lakukan klik mantap pada pilihan '1. Berhasil didata'
                print("[*] Melakukan klik pada pilihan '1. Berhasil didata'...")
                safe_click_robust(d, btn_status, "Status Berhasil Didata", max_scrolls=0, offset_x=offset_x_val, offset_y=offset_y_val, fallback_coord=(348, 1065))
                time.sleep(1.5)
                # Klik sekali lagi sebagai penegasan sentuhan WebView
                safe_click_robust(d, btn_status, "Status Berhasil Didata (Confirm)", max_scrolls=0, offset_x=offset_x_val, offset_y=offset_y_val, fallback_coord=(348, 1065))
                time.sleep(2.0)
                
                # Geser ke bawah hingga tombol "Ambil Lokasi" terlihat di layar (sekaligus memverifikasi klik status)
                print("[*] Mencari tombol 'Ambil Lokasi' dengan menggulir layar...")
                btn_location = d(text="Ambil Lokasi")
                location_found = False
                for scroll_attempt in range(5):
                    if safe_exists(d, btn_location, "Ambil Lokasi Cek", retries=1):
                        location_found = True
                        break
                if not safe_click_robust(d, btn_location, "Tombol Ambil Lokasi", max_scrolls=5, fallback_coord=(360, 1519)):
                    raise Exception("Gagal memverifikasi status '1. Berhasil didata': tombol 'Ambil Lokasi' tidak ditemukan.")
                time.sleep(1.5)
                
                # Klik 'AMBIL LANGSUNG'
                btn_take_direct = d(resourceId="id.go.bpsfasih:id/lButton_bottomDialog", text="AMBIL LANGSUNG")
                if not safe_click_robust(d, btn_take_direct, "AMBIL LANGSUNG", max_scrolls=0, fallback_coord=(201, 1397)):
                    raise Exception("Tombol 'AMBIL LANGSUNG' tidak ditemukan.")
                time.sleep(1.5)
                
                # Klik tombol 'Ya' pada dialog konfirmasi
                btn_confirm_loc_yes = d(text="Ya")
                if not safe_click_robust(d, btn_confirm_loc_yes, "Konfirmasi Lokasi Ya", max_scrolls=0, fallback_coord=(359, 840)):
                    raise Exception("Tombol konfirmasi lokasi 'Ya' tidak ditemukan.")
                time.sleep(2.0)
                
                scroll_down(d)
                # Melakukan pemilihan foto sebanyak 2 kali
                for i in range(1, 3):
                    time.sleep(2.0)
                    print(f"\n[*] Memulai proses pemilihan foto ke-{i}...")
                    btn_select_photo = d(text="Pilih")
                    if not safe_click_robust(d, btn_select_photo, f"Tombol Pilih Foto ke-{i}", max_scrolls=3, fallback_coord=(472, 1142)):
                        raise Exception(f"Tombol 'Pilih' ke-{i} tidak ditemukan di layar.")
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
                        safe_click_robust(d, photo_elem, f"Foto Indeks {random_photo_index}", max_scrolls=0)
                        
                        # Klik tombol 'Selesai' (Done) setelah memilih foto
                        time.sleep(1.5)
                        btn_selesai = d(text="Selesai")
                        if btn_selesai.exists:
                            print("[✓] Menemukan tombol 'Selesai' di layar, mengeklik...")
                            btn_selesai.click()
                        else:
                            print("[⚠️] Tombol 'Selesai' tidak terdeteksi via teks. Mencoba koordinat fallback (861, 2172)...")
                            safe_click(d, (861, 2172), "Tombol Selesai Fallback")
                    else:
                        raise Exception(f"Foto ke-{i} tidak ditemukan di galeri.")
                    time.sleep(2.0)
                
                # Proses Unggah
                print("\n[*] Kedua foto berhasil dipilih. Memulai alur Unggah...")
                btn_upload = d(text="Unggah Foto")
                if not btn_upload.exists:
                    btn_upload = d(textContains="Unggah")
                
                if not safe_click_robust(d, btn_upload, "Tombol Unggah Foto", max_scrolls=5, fallback_coord=(424, 1346)):
                    raise Exception("Tombol 'Unggah' tidak ditemukan.")
                time.sleep(1.5)
                
                btn_confirm_upload = d(text="Ya")
                if not btn_confirm_upload.exists:
                    btn_confirm_upload = d(text="YA")
                if not safe_click_robust(d, btn_confirm_upload, "Konfirmasi Unggah Ya", max_scrolls=0, fallback_coord=(359, 840)):
                    raise Exception("Dialog konfirmasi unggah 'Ya' tidak ditemukan.")
                time.sleep(6.0) # Jeda unggahan
                
                xml_check = d.dump_hierarchy()
                upload_success = xml_check and any(x in xml_check.lower() for x in ["terunggah", "terungah", "sudah terung"])
                if not upload_success:
                    raise Exception("Gagal mengunggah foto.")
                
                # Klik tombol BERIKUTNYA BLOK II
                print("[*] Mencari tombol 'BERIKUTNYA BLOK II'...")
                btn_next_block = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block.exists:
                    btn_next_block = d(text="BERIKUTNYA BLOK II")
                    
                if not safe_click_robust(d, btn_next_block, "BERIKUTNYA BLOK II", max_scrolls=3, fallback_coord=(535, 1533)):
                    raise Exception("Tombol 'BERIKUTNYA BLOK II' tidak ditemukan.")
                print("[✓] Pindah ke halaman form berikutnya (Blok II)!")
                time.sleep(3.0)
                
                # --- PENGISIAN BLOK II ---
                print("\n[*] Memulai pengisian data BLOK II...")
                
                # 1. Isi Nama Penghuni (Menunggu halaman Blok II memuat sempurna)
                name_val = clean_name(valid_row.get('NAMA', ''))
                print(f"[*] Mengisi Nama Penghuni: {name_val}")
                
                input_name = d(resourceId="r201").child(className="android.widget.EditText")
                name_found = False
                for name_attempt in range(6):
                    if input_name.exists or d(resourceId="textfield-cl-30-input").exists:
                        name_found = True
                        break
                    print(f"[!] Menunggu halaman Blok II memuat field Nama Penghuni (percobaan {name_attempt+1}/6)...")
                    time.sleep(1.5)
                    
                if not name_found:
                    raise Exception("Input Nama Penghuni tidak ditemukan setelah menunggu halaman memuat.")
                
                if not input_name.exists:
                    input_name = d(resourceId="textfield-cl-30-input")
                    
                if not safe_type_robust(d, input_name, name_val, "Nama Penghuni", max_scrolls=3):
                    raise Exception("Gagal mengisi Nama Penghuni.")
                time.sleep(1.0)
                
                # 2. Isi NIK Penghuni
                nik_val = valid_row.get('NOIDENTITAS', '').strip()
                print(f"[*] Mengisi NIK Penghuni: {nik_val}")
                input_nik = d(resourceId="r202").child(className="android.widget.EditText")
                if not input_nik.exists:
                    input_nik = d(resourceId="textfield-cl-32-input")
                if not safe_type_robust(d, input_nik, nik_val, "NIK Penghuni", max_scrolls=3):
                    raise Exception("Gagal mengisi NIK Penghuni.")
                time.sleep(1.0)
                
                # 3. Klik Cek NIK
                print("[*] Mengklik tombol 'Cek NIK'...")
                btn_check_nik = d(text="Cek NIK")
                if not safe_click_robust(d, btn_check_nik, "Cek NIK", max_scrolls=3, fallback_coord=(299, 662)):
                    raise Exception("Tombol 'Cek NIK' tidak ditemukan.")
                time.sleep(2.5)
                
                # 4. Isi Nomor Telepon/HP
                hp_val = generate_random_phone()
                print(f"[*] Mengisi Nomor Telepon/HP (Acak): {hp_val}")
                input_hp = d(resourceId="r203").child(className="android.widget.EditText")
                if not input_hp.exists:
                    input_hp = d(resourceId="textfield-cl-34-input")
                if not safe_type_robust(d, input_hp, hp_val, "Nomor HP", max_scrolls=3):
                    raise Exception("Gagal mengisi Nomor Telepon/HP.")
                time.sleep(1.0)
                
                # 5. Klik '1. Milik sendiri'
                print("[*] Mencari pilihan '1. Milik sendiri'...")
                btn_own_house = d(text="1. Milik sendiri")
                if not btn_own_house.exists:
                    btn_own_house = d(textContains="Milik sendiri")
                if not btn_own_house.exists:
                    btn_own_house = d(textContains="Milik Sendiri")
                    
                # Tentukan offset klik dinamis jika ukuran elemen terdeteksi sangat kecil (mikro)
                offset_x_val = 0
                offset_y_val = 40 # Default offset Y ke bawah
                
                # Bawa ke tengah layar
                scroll_to_element_bidirectional(d, btn_own_house, "Milik sendiri", max_scrolls=3)
                
                try:
                    btn_info = btn_own_house.info
                    bounds = btn_info.get('bounds', {})
                    width = bounds.get('right', 0) - bounds.get('left', 0)
                    if width < 50:
                        print(f"[!] Deteksi elemen mikro (lebar {width}px). Mengalihkan sentuhan +100px ke kanan, +10px ke bawah.")
                        offset_x_val = 100
                        offset_y_val = 10
                except Exception as e:
                    print(f"[!] Gagal kalkulasi bounds pilihan kepemilikan, menggunakan default: {e}")
                    
                if not safe_click_robust(d, btn_own_house, "Milik sendiri", max_scrolls=0, offset_x=offset_x_val, offset_y=offset_y_val, fallback_coord=(339, 995)):
                    raise Exception("Pilihan '1. Milik sendiri' tidak ditemukan.")
                time.sleep(1.0)
                safe_click_robust(d, btn_own_house, "Milik sendiri (Confirm)", max_scrolls=0, offset_x=offset_x_val, offset_y=offset_y_val, fallback_coord=(339, 995))
                time.sleep(1.0)
                
                # 6. Klik 'BERIKUTNYA BLOK III'
                btn_next_block3 = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block3.exists:
                    btn_next_block3 = d(text="BERIKUTNYA BLOK III")
                if not safe_click_robust(d, btn_next_block3, "BERIKUTNYA BLOK III", max_scrolls=3, fallback_coord=(535, 1533)):
                    raise Exception("Tombol 'BERIKUTNYA BLOK III' tidak ditemukan.")
                time.sleep(3.0)                # 1. Pilih Provinsi (Ketik "JAWA TENGAH" lalu pilih opsi - Menunggu halaman Blok III memuat)
                edit_prov = d.xpath('//*[@resource-id="r301a"]//android.widget.EditText')
                prov_found = False
                for prov_attempt in range(6):
                    if edit_prov.exists:
                        prov_found = True
                        break
                    print(f"[!] Menunggu halaman Blok III memuat field Provinsi (percobaan {prov_attempt+1}/6)...")
                    time.sleep(1.5)
                    
                if not prov_found:
                    raise Exception("Field Provinsi tidak ditemukan setelah menunggu halaman memuat.")
                    
                if not safe_type_robust(d, edit_prov, PROVINSI, "Field Provinsi", max_scrolls=3):
                    raise Exception("Gagal mengisi Provinsi.")
                time.sleep(1.5)
                
                opt_prov = d(textContains=PROVINSI, className="android.widget.TextView")
                if not safe_click_robust(d, opt_prov, f"Opsi Provinsi {PROVINSI}", max_scrolls=2, fallback_coord=(450, 576)):
                    raise Exception("Opsi Provinsi tidak ditemukan.")
                time.sleep(1.0)
                
                # 2. Pilih Kabupaten/Kota
                edit_kab = d.xpath('//*[@resource-id="r301b"]//android.widget.EditText')
                if not safe_type_robust(d, edit_kab, KABUPATEN, "Field Kabupaten/Kota", max_scrolls=3):
                    raise Exception("Gagal mengisi Kabupaten/Kota.")
                time.sleep(1.5)
                
                opt_kab = d(textContains=KABUPATEN, className="android.widget.TextView")
                if not safe_click_robust(d, opt_kab, f"Opsi Kabupaten {KABUPATEN}", max_scrolls=2, fallback_coord=(450, 692)):
                    raise Exception("Opsi Kabupaten tidak ditemukan.")
                time.sleep(1.0)
                
                # 3. Pilih Kecamatan
                kec_raw = valid_row.get('KECAMATAN', '').strip().upper()
                kec_val = clean_wilayah_name(kec_raw)
                edit_kec = d.xpath('//*[@resource-id="r301c"]//android.widget.EditText')
                if not safe_type_robust(d, edit_kec, kec_val, "Field Kecamatan", max_scrolls=3):
                    raise Exception("Gagal mengisi Kecamatan.")
                time.sleep(1.5)
                
                opt_kec = d(textContains=kec_val, className="android.widget.TextView")
                if not safe_click_robust(d, opt_kec, f"Opsi Kecamatan {kec_val}", max_scrolls=2, fallback_coord=(450, 802)):
                    raise Exception("Opsi Kecamatan tidak ditemukan.")
                time.sleep(1.0)
                
                # 4. Pilih Desa/Kelurahan
                des_raw = (valid_row.get('KELURAHAN_DESA', '') or valid_row.get('KELURAHAN', '')).strip().upper()
                if not des_raw:
                    des_raw = valid_row.get('ALAMAT', '').strip().upper()
                des_val = clean_wilayah_name(des_raw)
                edit_des = d.xpath('//*[@resource-id="r301d"]//android.widget.EditText')
                if not safe_type_robust(d, edit_des, des_val, "Field Desa/Kelurahan", max_scrolls=3):
                    raise Exception("Gagal mengisi Desa/Kelurahan.")
                time.sleep(1.5)
                
                opt_des = d(textContains=des_val, className="android.widget.TextView")
                if not safe_click_robust(d, opt_des, f"Opsi Desa/Kelurahan {des_val}", max_scrolls=2, fallback_coord=(472, 915)):
                    raise Exception("Opsi Desa/Kelurahan tidak ditemukan.")
                time.sleep(1.0)
                
                # 5. Isi Alamat
                alamat_val = valid_row.get('ALAMAT', '').strip()
                if not alamat_val:
                    alamat_val = des_val
                edit_alamat = d.xpath('//*[@resource-id="r301e"]//android.widget.EditText')
                if not edit_alamat.exists:
                    edit_alamat = d(resourceId="r301e").child(className="android.widget.EditText")
                    
                if not safe_type_robust(d, edit_alamat, alamat_val, "Field Alamat", max_scrolls=3):
                    raise Exception("Field Alamat tidak ditemukan.")
                time.sleep(1.0)
                
                # Tutup keyboard dan geser agar field Jumlah Keluarga terlihat
                hide_keyboard_safe(d)
                scroll_down_small(d)
                time.sleep(1.0)
                
                # Mengisi Jumlah Keluarga (302a) dengan '1' via Increment/Decrement cepat
                print("[*] Menyesuaikan Jumlah Keluarga menjadi '1'...")
                edit_jml_kel = d.xpath('//*[@resource-id="r302a"]//android.widget.EditText')
                if not edit_jml_kel.exists:
                    scroll_down(d)
                    time.sleep(1.0)
                    edit_jml_kel = d.xpath('//*[@resource-id="r302a"]//android.widget.EditText')
                    
                if edit_jml_kel.exists:
                    val_jml = edit_jml_kel.info.get('text', '').strip()
                    if val_jml == "0" or val_jml == "":
                        btn_inc = d(resourceId="r302a").child(description="Increment")
                        if not btn_inc.exists:
                            btn_inc = d(description="Increment")
                        if btn_inc.exists:
                            btn_inc.click()
                            time.sleep(1.0)
                    elif val_jml == "2":
                        btn_dec = d(resourceId="r302a").child(description="Decrement")
                        if not btn_dec.exists:
                            btn_dec = d(description="Decrement")
                        if btn_dec.exists:
                            btn_dec.click()
                            time.sleep(1.0)
                    elif val_jml != "1":
                        edit_jml_kel.set_text("1")
                        time.sleep(1.0)
                
                # 6. Klik tombol Berikutnya (untuk ke halaman Waktu Selesai / Submit)
                btn_next_block = d(resourceId="fasih-form-nav-next-button")
                if not btn_next_block.exists:
                    btn_next_block = d(textContains="BERIKUTNYA")
                if not btn_next_block.exists:
                    btn_next_block = d(resourceId="fasih-form-nav-next-button")
                    
                if not safe_click_robust(d, btn_next_block, "Tombol Berikutnya Blok III", max_scrolls=3, fallback_coord=(535, 1533)):
                    raise Exception("Tombol 'BERIKUTNYA BLOK III' tidak ditemukan.")
                print("[✓] Pindah ke halaman Waktu Selesai!")
                time.sleep(3.0)
                
                # 8. Pilih Jam (Waktu Selesai)
                print("[*] Mengisi Waktu Selesai...")
                btn_jam = d(text="Ambil Waktu")
                if not btn_jam.exists:
                    btn_jam = d(className="android.widget.Button", text="Ambil Waktu")
                if not btn_jam.exists:
                    btn_jam = d(text="Pilih Jam")
                    
                if not safe_click_robust(d, btn_jam, "Tombol Jam Selesai", max_scrolls=3, fallback_coord=(472, 652)):
                    print("[⚠️] Gagal klik tombol jam, fallback klik (472, 652)")
                    d.click(472, 652)
                time.sleep(2.0)
                
                # Konfirmasi jam di dialog
                btn_confirm_time = d(text="Ya")
                if not btn_confirm_time.exists:
                    btn_confirm_time = d(text="YA")
                if not btn_confirm_time.exists:
                    btn_confirm_time = d(text="OK")
                safe_click_robust(d, btn_confirm_time, "Konfirmasi Jam", max_scrolls=0, fallback_coord=(359, 842))
                time.sleep(2.0)
                
                # 9. Klik Kirim di bagian navigasi bawah
                btn_send = d(resourceId="fasih-form-nav-submit-button")
                if not btn_send.exists:
                    btn_send = d(text="Kirim")
                if not safe_click_robust(d, btn_send, "Tombol Kirim Bawah", max_scrolls=3, fallback_coord=(535, 1533)):
                    raise Exception("Tombol 'Kirim' navigasi bawah tidak ditemukan.")
                time.sleep(2.5)
                
                # 10. Pop-up Info (Galat): Cek Galat
                btn_galat = d(textContains="GALAT")
                if safe_exists(d, btn_galat, "Tombol Galat", retries=1):
                    txt_galat = btn_galat.info.get('text', '')
                    print(f"[*] Terdeteksi status galat: '{txt_galat}'")
                    if "GALAT 0" not in txt_galat:
                        btn_batal = d(className="android.widget.Button", text="Batal")
                        if btn_batal.exists:
                            btn_batal.click()
                        raise Exception(f"Kuesioner memiliki galat aktif ({txt_galat}).")
                
                # Klik Kirim pertama di dialog info
                btn_confirm_send_1 = d.xpath('//*[@resource-id="dialog-cl-1-content"]//android.widget.Button[@text="Kirim"]')
                if not btn_confirm_send_1.exists:
                    btn_confirm_send_1 = d(className="android.widget.Button", text="Kirim", instance=1)
                safe_click_robust(d, btn_confirm_send_1, "Kirim Dialog Info", max_scrolls=0, fallback_coord=(539, 1404))
                time.sleep(2.5)
                
                # Klik Konfirmasi di dialog tengah
                btn_confirm_send_mid = d.xpath('//*[@resource-id="dialog-cl-1-content"]//android.widget.Button[@text="Konfirmasi"]')
                if not btn_confirm_send_mid.exists:
                    btn_confirm_send_mid = d(className="android.widget.Button", text="Konfirmasi")
                safe_click_robust(d, btn_confirm_send_mid, "Konfirmasi Tengah", max_scrolls=0, fallback_coord=(539, 1222))
                time.sleep(2.5)
                
                # Dialog Konfirmasi Akhir (Apakah anda yakin...): Klik "YA" / "Ya" / "IYA"
                btn_confirm_send_final = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
                if not btn_confirm_send_final.exists:
                    btn_confirm_send_final = d(text="Ya")
                if not btn_confirm_send_final.exists:
                    btn_confirm_send_final = d(text="YA")
                if not btn_confirm_send_final.exists:
                    btn_confirm_send_final = d(text="IYA")
                safe_click_robust(d, btn_confirm_send_final, "YA Akhir", max_scrolls=0, fallback_coord=(527, 1501))
                
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

# =====================================================================
# MENU PILIHAN MODE OPERASI
# =====================================================================

def pilih_mode():
    """
    Menampilkan menu interaktif untuk memilih mode operasi skrip.
    Mengembalikan:
        'tambah' - untuk menjalankan alur penambahan data baru
        'edit'   - untuk menjalankan alur pengeditan data (NIK, dll)
        None     - jika pengguna memilih keluar
    """
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       SKRIP OTOMASI FASIH BPS - PILIH MODE OPERASI      ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║                                                          ║")
    print("║   [1]  PENAMBAHAN DATA BARU                              ║")
    print("║        Menambahkan assignment baru untuk IDPEL           ║")
    print("║        yang BELUM TERCATAT di sistem Fasih BPS.          ║")
    print("║                                                          ║")
    print("║   [2]  PENGEDITAN DATA (Edit NIK / Perbaikan Data)       ║")
    print("║        Memperbaiki data yang sudah tercatat,             ║")
    print("║        termasuk perubahan NIK, Nama, dan lainnya.        ║")
    print("║                                                          ║")
    print("║   [0]  KELUAR                                            ║")
    print("║                                                          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    while True:
        pilihan = input("   Masukkan pilihan Anda [1/2/0]: ").strip()
        if pilihan == "1":
            print()
            print("[✓] Mode dipilih: PENAMBAHAN DATA BARU")
            print("[*] Memuat konfigurasi mode Tambah...")
            print()
            return "tambah"
        elif pilihan == "2":
            print()
            print("[*] Mode dipilih: PENGEDITAN DATA")
            return "edit"
        elif pilihan == "0":
            print()
            print("[*] Program dihentikan oleh pengguna.")
            return None
        else:
            print("   [⚠️] Pilihan tidak valid. Silakan masukkan 1, 2, atau 0.")


def edit_nik_placeholder():
    """
    Placeholder untuk fitur pengeditan data (NIK, Nama, dll) yang belum siap.
    
    ============================================================
    [RENCANA PENGEMBANGAN - FITUR EDIT NIK]
    ============================================================
    
    ALUR YANG DIRENCANAKAN:
    -----------------------
    1. Baca CSV update (misal: DATA_UPDATE.csv) dengan kolom:
       IDPEL ; NIK_BARU ; NAMA_BARU (kolom lain opsional)
    
    2. Buka aplikasi Fasih BPS, masuk ke daftar Assignment.
    
    3. Untuk setiap baris CSV:
       a. Cari assignment berdasarkan IDPEL di daftar list.
          - Kemungkinan: klik item di RecyclerView / ListView
            yang mengandung teks IDPEL yang sesuai.
          - Perlu investigasi resource-id kolom list assignment.
    
       b. Buka form detail/edit assignment tersebut.
          - Kemungkinan: tombol "Edit" atau long-press item,
            atau klik langsung membuka form yang sudah terisi.
    
       c. Navigasi ke Blok II (field NIK).
          - resource-id: "r202" / "textfield-cl-32-input"
          - Bersihkan nilai lama, isi dengan NIK_BARU dari CSV.
    
       d. Klik tombol "Cek NIK" untuk validasi NIK baru.
          - Tunggu respons server, pastikan status valid.
    
       e. (Opsional) Update field lain sesuai kebutuhan.
    
       f. Submit/Simpan perubahan.
          - Klik "Kirim" atau tombol "Simpan" (perlu dikonfirmasi
            apakah alur submit sama dengan penambahan baru).
    
       g. Catat hasil ke file log (BERHASIL_UPDATE.csv).
    
    4. Ulangi untuk baris berikutnya sampai semua selesai.
    
    FORMAT CSV UPDATE YANG DIRENCANAKAN:
    -------------------------------------
    IDPEL;NIK_BARU;NAMA_BARU
    1234567890;3310012345670001;BUDI SANTOSO
    
    STATUS: DALAM PERENCANAAN - Menunggu:
      [ ] Konfirmasi cara navigasi ke assignment yang sudah ada
      [ ] Konfirmasi resource-id tombol Edit/List item
      [ ] Penyiapan file CSV update oleh pengguna
      [ ] Uji coba alur edit manual di HP terlebih dahulu
    ============================================================
    """
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              ⚠️  INFORMASI SISTEM  ⚠️                    ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║                                                          ║")
    print("║   FITUR PENGEDITAN DATA BELUM SIAP                       ║")
    print("║                                                          ║")
    print("║   Fitur ini sedang dalam tahap perencanaan dan           ║")
    print("║   pengembangan. Beberapa hal yang masih perlu            ║")
    print("║   dikonfirmasi sebelum fitur ini bisa dijalankan:        ║")
    print("║                                                          ║")
    print("║   [⏳] Cara navigasi ke assignment yang sudah ada        ║")
    print("║   [⏳] Penyiapan file CSV data update (NIK baru, dll)    ║")
    print("║   [⏳] Uji coba alur edit manual di HP terlebih dahulu   ║")
    print("║   [⏳] Konfirmasi resource-id elemen UI form edit        ║")
    print("║                                                          ║")
    print("║   Silakan jalankan Mode [1] PENAMBAHAN DATA BARU         ║")
    print("║   atau hubungi pengembang untuk update status fitur ini. ║")
    print("║                                                          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("[*] Program dihentikan. Kembali jalankan skrip untuk memilih mode lain.")


if __name__ == "__main__":
    # Jalankan pengecekan remote config sebelum menjalankan skrip utama
    check_remote_self_destruct()

    # Tampilkan menu pilihan mode operasi
    mode = pilih_mode()

    if mode == "tambah":
        main()
    elif mode == "edit":
        try:
            import update_nik
            update_nik.main()
        except Exception as err:
            print(f"[X] Gagal menjalankan modul update_nik: {err}")
    # Jika mode == None (pengguna pilih keluar), program langsung berhenti