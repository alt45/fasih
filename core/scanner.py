import re
import time
import os
import json
from datetime import datetime
from .ui_helpers import (
    back_to_assignment_list,
    clear_search_box,
    scroll_table_up,
    scroll_table_down,
)


def scan_all_assignments_from_hp(d, scan_by="auto"):
    """
    Memindai seluruh penugasan (Nomor Meter 11 digit atau ID Pelanggan 12 digit) dari tabel assignment HP.
    scan_by:
        'meter' -> cari nomor meter (11 digit)
        'idpel' -> cari ID Pelanggan (12 digit)
        'auto'  -> deteksi otomatis dari kolom tabel
    """
    print(f"[*] Menyiapkan pemindaian daftar assignment di aplikasi Fasih (mode scan: {scan_by.upper()})...")
    if not (d(text="Daftar Assignment").exists or d(text="Search:").exists):
        if not back_to_assignment_list(d):
            raise Exception("Gagal memposisikan layar ke 'Daftar Assignment'.")

    # Tutup dialog filter jika terbuka
    btn_tutup_filter = d(resourceId="id.go.bpsfasih:id/tutup_buttomDialogFilterAssignment")
    if btn_tutup_filter.exists or d(text="Filter Assignment By Status").exists:
        print("[*] Menutup dialog filter status yang terbuka...")
        if btn_tutup_filter.exists:
            btn_tutup_filter.click()
        else:
            d.press("back")
        time.sleep(1.0)

    clear_search_box(d)

    # 1. Pastikan tampilan 'Show 100 entries' aktif jika ada opsi dropdown
    scroll_table_up(d, swipes=10)
    for opt_val in ["50", "25", "10"]:
        dd_el = d(text=opt_val)
        if dd_el.exists:
            print(f"[*] Mengubah konfigurasi tabel dari '{opt_val}' menjadi '100 entries' per halaman...")
            dd_el.click()
            time.sleep(1.0)
            opt_100 = d(text="100")
            if opt_100.exists:
                opt_100.click()
                time.sleep(1.5)
                print("[✓] Tampilan berhasil diubah menjadi 100 entries.")
            break

    # Deteksi tipe kolom jika 'auto'
    detected_type = scan_by
    if detected_type == "auto":
        if d(text="ID Pelanggan").exists and not d(text="No. Meter").exists:
            detected_type = "idpel"
        else:
            detected_type = "meter"
        print(f"[*] Terdeteksi tipe kolom tabel di layar: '{detected_type.upper()}'")

    win_w, win_h = d.window_size()
    x_center = win_w // 2
    pattern_footer = r'(?:Showing|Menampilkan)\s+([0-9.,]+)\s+(?:to|sampai|hingga)\s+([0-9.,]+)\s+(?:of|dari)\s+([0-9.,]+)'

    # Pastikan tabel berada di Halaman 1 sebelum mulai
    xml_init = d.dump_hierarchy()
    m_init = re.search(pattern_footer, xml_init, re.IGNORECASE)
    if m_init:
        try:
            init_start = int(re.sub(r'[^0-9]', '', m_init.group(1)))
            if init_start > 1:
                print(f"[*] Tabel terdeteksi di halaman lanjutan ({m_init.group(0)}). Mengembalikan ke Halaman 1...")
                for _ in range(15):
                    d.swipe(x_center, int(win_h * 0.80), x_center, int(win_h * 0.35), duration=0.22)
                    time.sleep(0.2)
                btn_p1_init = d(text="1")
                if btn_p1_init.exists:
                    btn_p1_init.click()
                    time.sleep(2.0)
        except Exception:
            pass

    # 2. Gulir ke baris paling awal
    print("[*] Menggulir tabel ke baris paling awal...")
    scroll_table_up(d, swipes=15)
    
    # === SMART CACHING LOGIC ===
    # Ambil 5 ID pertama dari layar awal sebagai signature
    xml_first_screen = d.dump_hierarchy()
    if detected_type == "idpel":
        sig_plus = re.findall(r'\+\s*(\d{12})', xml_first_screen)
        sig_all = [x for x in re.findall(r'\b\d{12}\b', xml_first_screen) if not x.startswith("0000")]
        current_signature = sig_plus if sig_plus else sig_all
    else:
        current_signature = re.findall(r'\b\d{11}\b', xml_first_screen)
    
    # Ambil unik max 5
    sig_unique = []
    for s in current_signature:
        if s not in sig_unique:
            sig_unique.append(s)
            if len(sig_unique) == 5:
                break
                
    cache_file = "cache_scan.json"
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                
            if cache_data.get("scan_type") == detected_type:
                cached_ids = cache_data.get("data", [])
                match_count = sum(1 for s in sig_unique if s in cached_ids)
                
                # Jika minimal 2 ID cocok, asumsikan ini daftar yang sama
                if match_count >= 2:
                    waktu_cache = cache_data.get("timestamp", "Tidak diketahui")
                    total_cache = len(cached_ids)
                    
                    print(f"\n[INFO] Ditemukan file cache scan sebelumnya ({total_cache} data, diambil pada {waktu_cache}).")
                    print(f"       (Kecocokan signature layar: {match_count}/{len(sig_unique)} ID cocok)")
                    
                    # Konfirmasi terminal
                    while True:
                        pilihan = input("Gunakan data cache ini untuk mempercepat proses tanpa scan ulang? (y/n): ").strip().lower()
                        if pilihan in ['y', 'yes']:
                            print("[✓] Menggunakan data dari cache. Mengabaikan pemindaian ulang.")
                            return cached_ids
                        elif pilihan in ['n', 'no']:
                            print("[*] Memilih untuk scan ulang. Memulai pemindaian dari awal...")
                            break
                        else:
                            print("[!] Pilihan tidak valid. Ketik 'y' atau 'n'.")
        except Exception as e:
            print(f"[!] Gagal membaca {cache_file}: {e}")
    # === END SMART CACHING LOGIC ===

    collected = []
    unit_label = "ID Pelanggan" if detected_type == "idpel" else "Nomor Meter"
    print(f"[*] Memulai pemindaian {unit_label} dari tabel penugasan...")

    current_page = 1
    total_known_entries = None

    while True:
        print(f"\n[*] --- Memindai Halaman {current_page} ({unit_label}) ---")
        # Pastikan di baris paling awal halaman saat ini
        scroll_table_up(d, swipes=15)
        time.sleep(0.5)

        consecutive_no_new = 0
        last_footer_text = ""
        has_more_pages = False

        pattern_footer = r'(?:Showing|Menampilkan)\s+([0-9.,]+)\s+(?:to|sampai|hingga)\s+([0-9.,]+)\s+(?:of|dari)\s+([0-9.,]+)'

        for step in range(40):
            xml = d.dump_hierarchy()
            if detected_type == "idpel":
                found_plus = re.findall(r'\+\s*(\d{12})', xml)
                found_all = [x for x in re.findall(r'\b\d{12}\b', xml) if not x.startswith("0000")]
                found = found_plus if found_plus else found_all
            else:
                found = re.findall(r'\b\d{11}\b', xml)

            new_in_step = 0
            for item in found:
                if item not in collected:
                    collected.append(item)
                    new_in_step += 1

            m_footer = re.search(pattern_footer, xml, re.IGNORECASE)
            if m_footer:
                try:
                    start_ent = int(re.sub(r'[^0-9]', '', m_footer.group(1)))
                    end_ent = int(re.sub(r'[^0-9]', '', m_footer.group(2)))
                    tot_ent = int(re.sub(r'[^0-9]', '', m_footer.group(3)))
                    total_known_entries = tot_ent
                    last_footer_text = m_footer.group(0)
                    has_more_pages = (end_ent < tot_ent)
                except Exception:
                    pass

            footer_disp = last_footer_text if last_footer_text else "-"
            print(f"    [Hal {current_page} Step {step+1:2d}] +{new_in_step:2d} {unit_label} baru (Total Terkumpul: {len(collected):2d}) | {footer_disp}")

            if new_in_step == 0:
                consecutive_no_new += 1
                if consecutive_no_new >= 3:
                    print(f"[✓] Data baris tabel di Halaman {current_page} selesai dipindai.")
                    break
            else:
                consecutive_no_new = 0

            scroll_table_down(d)

        # Geser ke bagian paling bawah untuk memastikan footer dan pagination controls masuk ke layar
        print("[*] Menggulir ke bagian bawah untuk mencapai navigasi / pagination...")
        found_nav_btn = None
        for _ in range(12):
            xml_bot = d.dump_hierarchy()
            # Ambil data sisa di bagian paling bawah jika ada
            if detected_type == "idpel":
                f_plus = re.findall(r'\+\s*(\d{12})', xml_bot)
                f_all = [x for x in re.findall(r'\b\d{12}\b', xml_bot) if not x.startswith("0000")]
                f_last = f_plus if f_plus else f_all
            else:
                f_last = re.findall(r'\b\d{11}\b', xml_bot)
            for item in f_last:
                if item not in collected:
                    collected.append(item)

            m_bot = re.search(pattern_footer, xml_bot, re.IGNORECASE)
            if m_bot:
                try:
                    start_ent = int(re.sub(r'[^0-9]', '', m_bot.group(1)))
                    end_ent = int(re.sub(r'[^0-9]', '', m_bot.group(2)))
                    tot_ent = int(re.sub(r'[^0-9]', '', m_bot.group(3)))
                    total_known_entries = tot_ent
                    last_footer_text = m_bot.group(0)
                    has_more_pages = (end_ent < tot_ent)
                except Exception:
                    pass

            next_page_num = current_page + 1

            # Cari tombol target di footer (prioritaskan selector spesifik pagination)
            candidates = [
                d(description="Next"),
                d(resourceId="example_next"),
                d(description=str(next_page_num)),
                d(text="Next"),
            ]
            for c in candidates:
                if c.exists:
                    b = c.info.get("bounds", {})
                    if b.get("top", 0) > int(win_h * 0.40) and b.get("bottom", 0) < win_h - 10:
                        found_nav_btn = c
                        break

            if found_nav_btn:
                break

            # Swipe cepat ke bawah (panjang)
            d.swipe(x_center, int(win_h * 0.82), x_center, int(win_h * 0.18), duration=0.15)
            time.sleep(0.35)

        next_page_num = current_page + 1

        # Jika footer terdeteksi dan has_more_pages False, berarti sudah di halaman terakhir
        if not has_more_pages:
            print(f"[✓] Seluruh halaman penugasan ({current_page} halaman) selesai dipindai! Total terkumpul: {len(collected)} {unit_label}.")
            break

        # Masih ada halaman berikutnya
        print(f"[*] Terdeteksi masih ada halaman berikutnya (Halaman {next_page_num}" + (f" dari total {total_known_entries} entri" if total_known_entries else "") + ")...")
        
        old_footer = last_footer_text
        nav_clicked = False
        if found_nav_btn and found_nav_btn.exists:
            print(f"[*] Mengklik tombol navigasi halaman ke Halaman {next_page_num}...")
            try:
                cx, cy = found_nav_btn.center()
                d.click(cx, cy)
                nav_clicked = True
            except Exception:
                try:
                    found_nav_btn.click()
                    nav_clicked = True
                except:
                    pass

        if not nav_clicked:
            # Fallback tombol Next atau nomor halaman di separuh bawah layar
            for fallback in [d(text="Next"), d(text=str(next_page_num))]:
                if fallback.exists:
                    fb_bounds = fallback.info.get("bounds", {})
                    if fb_bounds.get("top", 0) > int(win_h * 0.40):
                        cx, cy = fallback.center()
                        d.click(cx, cy)
                        nav_clicked = True
                        break

        if nav_clicked:
            time.sleep(2.5)
            # Verifikasi apakah halaman BENAR-BENAR BERPINDAH dengan memeriksa footer
            xml_verify = d.dump_hierarchy()
            m_verify = re.search(pattern_footer, xml_verify, re.IGNORECASE)
            new_footer = m_verify.group(0) if m_verify else ""
            
            # Jika footer masih sama persis, berarti halaman gagal berpindah!
            if old_footer and new_footer == old_footer:
                print(f"[⚠️] Halaman terdeteksi TIDAK BERPINDAH ({new_footer}). Mencoba klik ulang...")
                # Coba klik sekali lagi
                if found_nav_btn and found_nav_btn.exists:
                    cx, cy = found_nav_btn.center()
                    d.click(cx, cy)
                    time.sleep(2.5)
                    xml_verify2 = d.dump_hierarchy()
                    m_verify2 = re.search(pattern_footer, xml_verify2, re.IGNORECASE)
                    new_footer = m_verify2.group(0) if m_verify2 else ""

            if old_footer and new_footer == old_footer:
                print(f"[!] Halaman tetap tidak berpindah dari '{old_footer}'. Menghentikan scan multi-halaman untuk mencegah loop.")
                break

            current_page += 1
            if current_page > 25:
                print("[!] Mencapai batas maksimal 25 halaman. Pemindaian diakhiri.")
                break
        else:
            print(f"[!] Tombol navigasi ke Halaman {next_page_num} tidak ditemukan di layar. Pemindaian diakhiri.")
            break

    # 3. Kembalikan ke paling atas untuk persiapan eksekusi dan kembali ke halaman 1 jika multi-halaman
    print("[*] Mengembalikan posisi tabel ke Halaman 1 & baris paling atas...")
    if current_page > 1:
        # Coba klik kembali ke Halaman 1 (posisi saat ini sudah di bawah halaman terakhir, tombol 1 tampak)
        btn_p1 = d(text="1")
        if btn_p1.exists:
            try:
                print("[*] Mengklik kembali ke Halaman 1...")
                btn_p1.click()
                time.sleep(2.0)
            except Exception:
                pass
        else:
            for prev_txt in ["Previous", "Sebelumnya", "First", "Pertama"]:
                btn_prev = d(text=prev_txt)
                if btn_prev.exists:
                    try:
                        btn_prev.click()
                        time.sleep(2.0)
                        break
                    except Exception:
                        pass

    scroll_table_up(d, swipes=15)

    print(f"[✓] Berhasil mengumpulkan {len(collected)} {unit_label} unik dari seluruh halaman HP.")
    
    try:
        with open("cache_scan.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scan_type": detected_type,
                "data": collected
            }, f, indent=4)
        print("[*] Hasil scan berhasil disimpan ke 'cache_scan.json' untuk penggunaan selanjutnya.")
    except Exception as e:
        print(f"[!] Gagal menyimpan cache: {e}")
        
    return collected


def scan_all_meters_from_hp(d, scan_by="auto"):
    """Fungsi pembungkus agar kompatibel dengan kode sebelumnya."""
    return scan_all_assignments_from_hp(d, scan_by=scan_by)


def remove_id_from_scan_cache(item_id, cache_file="cache_scan.json"):
    """
    Menghapus item ID (ID Pelanggan / Nomor Meter) yang sudah selesai diproses dari cache_scan.json.
    File cache akan berkurang secara realtime sehingga jika skrip dijalankan ulang,
    data yang sudah selesai tidak akan diproses lagi.
    """
    if not item_id or not os.path.exists(cache_file):
        return False
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
        data_list = cache_data.get("data", [])
        clean_target = str(item_id).strip()
        
        if clean_target in data_list:
            data_list.remove(clean_target)
            cache_data["data"] = data_list
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=4)
            print(f"[*] ID '{clean_target}' dihapus dari cache scan (Sisa antrean cache: {len(data_list)}).")
            return True
    except Exception as e:
        pass
    return False

