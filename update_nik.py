import csv
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

import uiautomator2 as u2

# ================== KONFIGURASI UTAMA ==================
DEVICE_ID = ""                    # Kosongkan untuk auto-detect perangkat aktif
CSV_INPUT = "ahzacahyo.csv"       # File data IDPEL dan NIK perbaikan
CSV_DELIMITER = ";"               # Pemisah kolom CSV

OUT_SUKSES = "SUKSES_UPDATE_NIK.csv"
OUT_TIDAK_DITEMUKAN = "IDPEL_TIDAK_DITEMUKAN.csv"
OUT_NIK_TIDAK_DITEMUKAN = "NIK_TIDAK_DITEMUKAN.csv"
OUT_GAGAL = "NIK_GAGAL_UPDATE.csv"
# =======================================================


def append_to_log(filepath, data_dict):
    """Menyimpan catatan hasil ke file CSV log."""
    file_exists = os.path.exists(filepath)
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data_dict.keys()), delimiter=CSV_DELIMITER)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_dict)
    except Exception as e:
        print(f"[!] Gagal mencatat ke log '{filepath}': {e}")


def load_input_data(filepath):
    """Membaca file CSV input dan mengembalikan list data."""
    if not os.path.exists(filepath):
        print(f"[X] File '{filepath}' tidak ditemukan!")
        return []
    
    rows = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=CSV_DELIMITER)
            header = next(reader, None)
            for line_no, r in enumerate(reader, start=2):
                if not r or len(r) < 2:
                    continue
                idpel = str(r[0]).strip()
                nik_baru = str(r[1]).strip()
                if idpel and nik_baru:
                    rows.append({
                        "id_pelanggan": idpel,
                        "NIK_Perbaikan": nik_baru
                    })
        print(f"[OK] Berhasil memuat {len(rows)} data dari '{filepath}'")
        return rows
    except Exception as e:
        print(f"[X] Gagal membaca CSV '{filepath}': {e}")
        return []


def remove_idpel_from_input_csv(filepath, idpel_done):
    """Menghapus baris IDPEL yang sudah sukses dari file CSV input agar tidak diproses ulang."""
    if not os.path.exists(filepath) or not idpel_done:
        return
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=CSV_DELIMITER)
            header = next(reader, None)
            all_rows = list(reader)
        
        remaining = [r for r in all_rows if r and r[0].strip() != idpel_done.strip()]
        
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=CSV_DELIMITER)
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


def connect_device():
    """Menghubungkan ke perangkat Android via uiautomator2."""
    try:
        if DEVICE_ID:
            print(f"[*] Menghubungkan ke perangkat: {DEVICE_ID}...")
            d = u2.connect(DEVICE_ID)
        else:
            print("[*] Mendeteksi perangkat Android secara otomatis...")
            d = u2.connect()
        info = d.info
        print(f"[OK] Terhubung ke: {info.get('brand')} {info.get('model')} (Serial: {d.serial})")
        print(f"     Resolusi: {d.window_size()}")
        return d
    except Exception as e:
        print(f"[X] Gagal terhubung ke Android: {e}")
        return None


def process_update_nik(d, row_data):
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
        remove_idpel_from_input_csv(CSV_INPUT, idpel)
        clear_search_box(d)
        return "IDPEL_NOT_FOUND"

    print(f"[OK] Data IDPEL {idpel} ditemukan di tabel!")

    # 4. Klik tanda '+' untuk expand detail baris
    btn_plus = d(text="+")
    if not btn_plus.exists:
        # Fallback klik area kolom kiri baris pertama hasil pencarian
        d.click(60, 837)
    else:
        btn_plus.click()
    time.sleep(1.5)

    # 5. Klik tombol 'Aksi'
    btn_aksi = d(className="android.widget.Button", text="Aksi")
    if not btn_aksi.exists:
        btn_aksi = d(text="Aksi")
    if not btn_aksi.exists:
        # Fallback koordinat center tombol Aksi yang terverifikasi
        d.click(258, 1275)
    else:
        btn_aksi.click()
    time.sleep(1.5)

    # 6. Klik 'BUKA' pada dialog
    btn_buka = d(resourceId="id.go.bpsfasih:id/openAssignment_b")
    if not btn_buka.exists:
        btn_buka = d(text="BUKA")
    if not btn_buka.exists:
        raise Exception("Tombol 'BUKA' tidak ditemukan di menu dialog Aksi.")
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
    for _ in range(20):
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            time.sleep(1.0)
        else:
            break
    time.sleep(2.0)

    # 8. BLOK I: Verifikasi halaman terbuka, Geser layar ke atas, & Klik 'Cek ID Pelanggan'
    print("[*] Menunggu halaman BLOK I termuat...")
    for _ in range(12):
        if d(text="Cek ID Pelanggan").exists or d(text="BERIKUTNYA BLOK II").exists or d(textContains="ID pelanggan").exists or d(textContains="BLOK I").exists:
            break
        time.sleep(1.0)

    # Geser layar ke atas agar tombol Cek ID Pelanggan di bawah terlihat
    print("[*] BLOK I: Menggeser layar ke atas agar tombol 'Cek ID Pelanggan' terlihat...")
    swipe_up_to_reveal(d)
    time.sleep(1.5)

    btn_cek_idpel = d(text="Cek ID Pelanggan")
    if not btn_cek_idpel.exists:
        print("[*] Belum terlihat, mencoba geser layar sekali lagi...")
        swipe_up_to_reveal(d)
        time.sleep(1.5)
        btn_cek_idpel = d(text="Cek ID Pelanggan")

    if not btn_cek_idpel.exists:
        raise Exception("Gagal masuk ke BLOK I / Tombol 'Cek ID Pelanggan' tidak ditemukan.")

    print("[*] BLOK I: Mengklik 'Cek ID Pelanggan'...")
    btn_cek_idpel.click()
    time.sleep(3.0)  # Tunggu respon server

    # 9. Klik 'BERIKUTNYA BLOK II'
    print("[*] Berpindah ke BLOK II...")
    btn_next_b2 = d(resourceId="fasih-form-nav-next-button")
    if not btn_next_b2.exists:
        btn_next_b2 = d(text="BERIKUTNYA BLOK II")
    if not btn_next_b2.exists:
        btn_next_b2 = d(textContains="BERIKUTNYA")
    
    if btn_next_b2.exists:
        btn_next_b2.click()
    else:
        d.click(532, 1424)
    time.sleep(3.0)

    # 10. BLOK II: Input NIK Baru & Klik 'Cek NIK'
    print("[*] BLOK II: Mencari field input NIK penghuni...")
    input_nik = d(resourceId="r202").child(className="android.widget.EditText")
    if not input_nik.exists:
        input_nik = d(resourceId="textfield-cl-29-input")
    if not input_nik.exists:
        # Ambil EditText kedua yang ada di layar BLOK II
        all_edits = d(className="android.widget.EditText")
        if all_edits.count >= 2:
            input_nik = all_edits[1]

    if not input_nik.exists:
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
        print(f"[*] Mencatat ke '{OUT_NIK_TIDAK_DITEMUKAN}' dan menghapus dari '{CSV_INPUT}'...")
        append_to_log(OUT_NIK_TIDAK_DITEMUKAN, {
            "id_pelanggan": idpel,
            "NIK_Perbaikan": nik_baru,
            "keterangan": "NIK Tidak Ditemukan saat pemadanan",
            "waktu": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        remove_idpel_from_input_csv(CSV_INPUT, idpel)
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
    remove_idpel_from_input_csv(CSV_INPUT, idpel)
    clear_search_box(d)
    return "SUKSES"


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      OTOMASI PERBAIKAN DATA NIK - FASIH BPS             ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  File Target : {CSV_INPUT:<41} ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 1. Load Data CSV
    data_list = load_input_data(CSV_INPUT)
    if not data_list:
        print("[!] Tidak ada data untuk diproses. Program selesai.")
        return

    # 2. Hubungkan ke Perangkat Android
    d = connect_device()
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
            status_hasil = process_update_nik(d, item)
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
