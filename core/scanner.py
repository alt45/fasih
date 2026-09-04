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
    print(f"[*] Memulai pemindaian {unit_label} dari baris 1 sampai tuntas...")

    consecutive_no_new = 0
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
        footer_text = m_footer.group(0) if m_footer else "-"

        print(f"    [Pindai Step {step+1:2d}] +{new_in_step:2d} {unit_label} baru (Total: {len(collected):2d}) | {footer_text}")

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

    print(f"[✓] Berhasil mengumpulkan {len(collected)} {unit_label} unik dari HP.")
    return collected


def scan_all_meters_from_hp(d, scan_by="auto"):
    """Fungsi pembungkus agar kompatibel dengan kode sebelumnya."""
    return scan_all_assignments_from_hp(d, scan_by=scan_by)
