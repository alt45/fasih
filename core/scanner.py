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

        for step in range(35):
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

            m_footer = re.search(r'Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries', xml)
            if m_footer:
                start_ent = int(m_footer.group(1))
                end_ent = int(m_footer.group(2))
                tot_ent = int(m_footer.group(3))
                total_known_entries = tot_ent
                last_footer_text = m_footer.group(0)
                if end_ent < tot_ent:
                    has_more_pages = True
                else:
                    has_more_pages = False

            footer_disp = last_footer_text if last_footer_text else "-"
            print(f"    [Hal {current_page} Step {step+1:2d}] +{new_in_step:2d} {unit_label} baru (Total Terkumpul: {len(collected):2d}) | {footer_disp}")

            if new_in_step == 0:
                consecutive_no_new += 1
                if consecutive_no_new >= 3:
                    print(f"[✓] Mencapai bagian bawah tabel pada Halaman {current_page}.")
                    break
            else:
                consecutive_no_new = 0

            scroll_table_down(d)

        # Cek apakah ada halaman berikutnya
        if has_more_pages:
            next_page_num = current_page + 1
            print(f"[*] Terdeteksi masih ada halaman berikutnya (Total: {total_known_entries} data). Menavigasi ke Halaman {next_page_num}...")
            
            btn_next = d(text="Next")
            if not btn_next.exists:
                btn_next = d(text=str(next_page_num))
            if not btn_next.exists:
                btn_next = d(textContains="Next")
            if not btn_next.exists:
                btn_next = d(textContains="Berikutnya")

            if btn_next.exists:
                print(f"[*] Mengklik tombol navigasi ke Halaman {next_page_num}...")
                btn_next.click()
                time.sleep(2.5)
                current_page += 1
            else:
                print(f"[!] Tombol navigasi ke Halaman {next_page_num} tidak ditemukan di layar. Pemindaian berhenti.")
                break
        else:
            print(f"[✓] Seluruh halaman penugasan ({current_page} halaman) selesai dipindai!")
            break

    # 3. Kembalikan ke paling atas untuk persiapan eksekusi dan kembali ke halaman 1 jika multi-halaman
    print("[*] Mengembalikan posisi tabel ke baris paling atas...")
    btn_p1 = d(text="1")
    if btn_p1.exists and current_page > 1:
        try:
            btn_p1.click()
            time.sleep(1.5)
        except Exception:
            pass
    scroll_table_up(d, swipes=15)

    print(f"[✓] Berhasil mengumpulkan {len(collected)} {unit_label} unik dari HP.")
    return collected


def scan_all_meters_from_hp(d, scan_by="auto"):
    """Fungsi pembungkus agar kompatibel dengan kode sebelumnya."""
    return scan_all_assignments_from_hp(d, scan_by=scan_by)
