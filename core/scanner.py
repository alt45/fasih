import re
import time
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

    # 2. Gulir ke baris paling awal
    print("[*] Menggulir tabel ke posisi paling awal...")
    scroll_table_up(d, swipes=15)

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
        print("[*] Memeriksa bagian bawah halaman untuk kontrol navigasi / pagination...")
        for _ in range(3):
            d.swipe(360, 1300, 360, 700, duration=0.25)
            time.sleep(0.3)
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

        # Deteksi apakah tombol halaman berikutnya ada di layar
        btn_target_page = d(text=str(next_page_num))
        has_page_button = btn_target_page.exists

        if has_more_pages or has_page_button:
            print(f"[*] Terdeteksi masih ada halaman berikutnya (Halaman {next_page_num}" + (f" dari total {total_known_entries} entri" if total_known_entries else "") + ")...")
            
            nav_clicked = False
            # Strategi 1: Klik tombol nomor halaman langsung (misal "2", "3")
            if btn_target_page.exists:
                print(f"[*] Mengklik tombol nomor Halaman '{next_page_num}'...")
                btn_target_page.click()
                nav_clicked = True
            
            # Strategi 2: Jika tombol angka tidak ada, cari tombol "Next" / "Berikutnya"
            if not nav_clicked:
                for nav_text in ["Next", "Berikutnya"]:
                    btn_n = d(text=nav_text)
                    if not btn_n.exists:
                        btn_n = d(textContains=nav_text)
                    if btn_n.exists:
                        print(f"[*] Mengklik tombol '{nav_text}' untuk ke Halaman {next_page_num}...")
                        btn_n.click()
                        nav_clicked = True
                        break

            # Strategi 3: Coba scroll sedikit lagi jika belum tampak
            if not nav_clicked:
                d.swipe(360, 1200, 360, 600, duration=0.25)
                time.sleep(0.5)
                btn_target_page = d(text=str(next_page_num))
                if btn_target_page.exists:
                    print(f"[*] Mengklik tombol nomor Halaman '{next_page_num}' setelah scroll...")
                    btn_target_page.click()
                    nav_clicked = True
                else:
                    btn_next = d(text="Next")
                    if btn_next.exists:
                        print(f"[*] Mengklik tombol 'Next' setelah scroll...")
                        btn_next.click()
                        nav_clicked = True

            if nav_clicked:
                time.sleep(2.5)
                current_page += 1
                if current_page > 20:
                    print("[!] Mencapai batas maksimal 20 halaman. Pemindaian diakhiri demi keamanan.")
                    break
            else:
                print(f"[!] Tombol navigasi ke Halaman {next_page_num} tidak ditemukan di layar. Pemindaian diakhiri.")
                break
        else:
            print(f"[✓] Seluruh halaman penugasan ({current_page} halaman) selesai dipindai!")
            break

    # 3. Kembalikan ke paling atas untuk persiapan eksekusi dan kembali ke halaman 1 jika multi-halaman
    print("[*] Mengembalikan posisi tabel ke baris paling atas...")
    if current_page > 1:
        # Coba klik kembali ke Halaman 1
        btn_p1 = d(text="1")
        if btn_p1.exists:
            try:
                print("[*] Mengklik kembali ke Halaman 1...")
                btn_p1.click()
                time.sleep(1.5)
            except Exception:
                pass
        else:
            # Atau klik tombol Previous / Pertama
            for prev_txt in ["Previous", "Sebelumnya", "First", "Pertama"]:
                btn_prev = d(text=prev_txt)
                if btn_prev.exists:
                    try:
                        btn_prev.click()
                        time.sleep(1.5)
                        break
                    except Exception:
                        pass

    scroll_table_up(d, swipes=15)

    print(f"[✓] Berhasil mengumpulkan {len(collected)} {unit_label} unik dari seluruh halaman HP.")
    return collected


def scan_all_meters_from_hp(d, scan_by="auto"):
    """Fungsi pembungkus agar kompatibel dengan kode sebelumnya."""
    return scan_all_assignments_from_hp(d, scan_by=scan_by)

