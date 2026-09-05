"""
Otomasi Perbaikan Data NIK - Fasih BPS (Modular Orchestrator)
"""
import argparse
import os
import sys
import time

# Pastikan output utf-8 aman di terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Re-export semua modul core untuk menjaga 100% backward-compatibility
from core.config import (
    DEVICE_ID,
    CSV_INPUT,
    CSV_DELIMITER,
    OUT_SUKSES,
    OUT_TIDAK_DITEMUKAN,
    OUT_NIK_TIDAK_DITEMUKAN,
    OUT_GAGAL,
)
from core.device import (
    get_connected_devices,
    pilih_perangkat,
    connect_device,
)
from core.csv_utils import (
    detect_delimiter,
    append_to_log,
    load_input_data,
    remove_idpel_from_input_csv,
    pilih_file_csv,
)
from core.ui_helpers import (
    is_keyboard_shown,
    hide_keyboard,
    scroll_up,
    scroll_down,
    swipe_up_to_reveal,
    scroll_down_small,
    scroll_table_up,
    scroll_table_down,
    is_nik_present_on_screen,
    clear_search_box,
    back_to_assignment_list,
)
from core.scanner import (
    scan_all_assignments_from_hp,
    scan_all_meters_from_hp,
)
from core.form_processor import (
    process_update_nik,
)
from core.nik_provider import (
    FallbackNIKProvider,
    is_daya_450,
)


def run_forward_mode(target_device=None, custom_csv=None):
    """
    Mode 2: PENGEDITAN DATA (FORWARD: File CSV -> Cari di HP satu per satu)
    """
    target_csv = custom_csv or ""
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

    if not os.path.exists(target_csv):
        print(f"[X] File CSV '{target_csv}' TIDAK DITEMUKAN!")
        print(f"    Pastikan file '{target_csv}' sudah berada di folder proyek.")
        return

    data_list = load_input_data(target_csv)
    if not data_list:
        print(f"[!] Tidak ada data untuk diproses di '{target_csv}'. Program selesai.")
        return

    d = connect_device(target_device)
    if not d:
        return

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


def run_reverse_mode(target_device=None, custom_csv=None, is_pasca=False, enable_daya_fallback=False):
    """
    Mode 3 / 4 / 5: PENGEDITAN DATA TERBALIK (REVERSE)
    1. Memindai seluruh nomor meter (Mode 3) atau ID Pelanggan (Mode 4 Pasca / Mode 5 Pasca Daya) dari HP.
    2. Mencocokkan dengan file master (mastermeter.csv, masterpasca.csv, atau masterpascadaya.csv).
    3. Mengeksekusi pembaruan NIK hanya untuk data yang cocok (BLOK I dilewati jika pasca).
    4. Jika enable_daya_fallback aktif, NIK yang gagal dan daya bukan 450 akan difallback ke nik.json.
    """
    target_csv = custom_csv or ""
    if not target_csv:
        if enable_daya_fallback:
            if os.path.exists("masterpascadaya.csv"):
                print("[*] File 'masterpascadaya.csv' terdeteksi otomatis sebagai file master pasca bayar + daya.")
                target_csv = "masterpascadaya.csv"
            else:
                target_csv = pilih_file_csv(judul_mode="Pengeditan NIK Pasca + Daya (Master CSV)")
                if not target_csv:
                    return
        elif is_pasca:
            if os.path.exists("masterpasca.csv"):
                print("[*] File 'masterpasca.csv' terdeteksi otomatis sebagai file master pasca bayar.")
                target_csv = "masterpasca.csv"
            else:
                target_csv = pilih_file_csv(judul_mode="Pengeditan NIK Pasca Bayar (Master CSV)")
                if not target_csv:
                    return
        else:
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

    if enable_daya_fallback:
        judul_banner = "OTOMASI PENGEDITAN NIK PASCA + DAYA (MODE 5)"
    elif is_pasca:
        judul_banner = "OTOMASI PENGEDITAN NIK PASCA BAYAR (REVERSE MODE)"
    else:
        judul_banner = "OTOMASI PENGEDITAN NIK TERBALIK (REVERSE MODE)"
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║   {judul_banner:<54} ║")
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

    has_meter_col = any("no_meter" in r for r in raw_data)
    master_by_meter = {}
    master_by_idpel = {}
    for r in raw_data:
        idp = str(r["id_pelanggan"]).strip()
        nik = str(r["NIK_Perbaikan"]).strip()
        master_by_idpel[idp] = r
        if "no_meter" in r and r["no_meter"]:
            m_val = str(r["no_meter"]).strip()
            if len(m_val) != 16:
                master_by_meter[m_val] = r

    print(f"[OK] Berhasil memuat {len(raw_data)} data master.")
    if is_pasca:
        print(f"     Terdeteksi {len(master_by_idpel)} data ID Pelanggan unik di master pasca.")
    elif has_meter_col:
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
    scan_type = "idpel" if is_pasca else "meter"
    hp_items = scan_all_assignments_from_hp(d, scan_by=scan_type)
    if not hp_items:
        label_tipe = "ID Pelanggan" if is_pasca else "nomor meter"
        print(f"[!] Tidak ada {label_tipe} yang berhasil discan dari HP. Program berhenti.")
        return

    # 4. Cocokkan data HP dengan file master
    antrean_eksekusi = []
    dilewati = []

    if is_pasca:
        for idp in hp_items:
            if idp in master_by_idpel:
                antrean_eksekusi.append(master_by_idpel[idp])
            else:
                dilewati.append(idp)
    else:
        for m in hp_items:
            if m in master_by_meter:
                antrean_eksekusi.append(master_by_meter[m])
            elif m in master_by_idpel:
                antrean_eksekusi.append(master_by_idpel[m])
            else:
                dilewati.append(m)

    total_hp = len(hp_items)
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

    # 5. Inisialisasi Fallback NIK Provider jika enable_daya_fallback aktif
    fallback_provider = None
    if enable_daya_fallback:
        print("[*] Menginisialisasi penyedia Fallback NIK dari 'nik.json'...")
        fallback_provider = FallbackNIKProvider(json_path="nik.json")

    print(f"[*] Memulai pemrosesan {total_cocok} data penugasan yang cocok...\n")

    # 6. Eksekusi pembaruan NIK untuk data yang cocok
    sukses_count = 0
    idpel_tidak_ada_count = 0
    nik_tidak_ditemukan_count = 0
    gagal_count = 0

    for idx, item in enumerate(antrean_eksekusi, start=1):
        idpel = item["id_pelanggan"]
        nik = item["NIK_Perbaikan"]
        meter = item.get("no_meter", "")
        meter_info = f" (No. Meter: {meter})" if meter else ""
        daya_val = item.get("daya", "")
        daya_info = f" (Daya: {daya_val})" if daya_val else ""
        print(f"\n>>> Progress Reverse: [{idx}/{total_cocok}] IDPEL: {idpel}{meter_info}{daya_info} <<<")

        try:
            status_hasil = process_update_nik(
                d,
                item,
                target_csv,
                skip_cek_idpel=is_pasca,
                fallback_nik_provider=fallback_provider
            )
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
    parser.add_argument("--mode", "-m", type=str, default="forward", help="Pilih mode: 'forward' ('2') / 'reverse' ('3') / 'pasca' ('4') / 'pascadaya' ('5')")
    
    args, _ = parser.parse_known_args()
    target_device = custom_device or args.device or DEVICE_ID
    target_csv = custom_csv or args.csv or ""
    selected_mode = mode or args.mode or "forward"

    if selected_mode.lower() in ["pascadaya", "5", "pasca_daya", "daya"]:
        run_reverse_mode(target_device=target_device, custom_csv=target_csv, is_pasca=True, enable_daya_fallback=True)
        return
    elif selected_mode.lower() in ["reverse", "3", "terbalik", "rev"]:
        run_reverse_mode(target_device=target_device, custom_csv=target_csv, is_pasca=False)
        return
    elif selected_mode.lower() in ["pasca", "4", "pascabayar", "reverse_pasca"]:
        run_reverse_mode(target_device=target_device, custom_csv=target_csv, is_pasca=True)
        return
    else:
        run_forward_mode(target_device=target_device, custom_csv=target_csv)


if __name__ == "__main__":
    main()
