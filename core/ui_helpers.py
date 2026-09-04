import time


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


def scroll_table_up(d, swipes=15):
    """Menggulir tabel ke baris paling awal."""
    for _ in range(swipes):
        d.swipe(360, 850, 360, 1450, duration=0.12)
        time.sleep(0.05)


def scroll_table_down(d):
    """Menggulir tabel ke bawah sedikit."""
    d.swipe(360, 1350, 360, 850, duration=0.25)
    time.sleep(0.3)


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
