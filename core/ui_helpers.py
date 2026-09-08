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


def safe_set_text(element, text_val, d=None):
    """
    Membersihkan dan mengisi teks baru ke elemen input secara aman.
    Mendukung UiObject maupun DeviceXPathSelector tanpa menimbulkan galat:
    AttributeError: ('Invalid attr', 'clear_text').
    """
    try:
        element.click()
        time.sleep(0.2)
    except Exception:
        pass

    if hasattr(element, "clear_text"):
        try:
            element.clear_text()
            time.sleep(0.1)
        except Exception:
            pass

    try:
        element.set_text(str(text_val))
    except Exception:
        try:
            element.set_text("")
            element.set_text(str(text_val))
        except Exception:
            if d is not None:
                d.send_keys(str(text_val))


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
    """Menggulir tabel ke baris paling awal (adaptif terhadap resolusi layar)."""
    try:
        w, h = d.window_size()
        x = w // 2
        y_start = int(h * 0.35)
        y_end = int(h * 0.85)
        for _ in range(swipes):
            d.swipe(x, y_start, x, y_end, duration=0.12)
            time.sleep(0.05)
    except Exception as e:
        print(f"[!] Gagal scroll table up: {e}")


def scroll_table_down(d):
    """Menggulir tabel ke bawah sedikit (adaptif terhadap resolusi layar)."""
    try:
        w, h = d.window_size()
        x = w // 2
        y_start = int(h * 0.80)
        y_end = int(h * 0.40)
        d.swipe(x, y_start, x, y_end, duration=0.25)
        time.sleep(0.3)
    except Exception as e:
        print(f"[!] Gagal scroll table down: {e}")


def is_nik_present_on_screen(d):
    """Mengecek apakah kata atau elemen NIK sudah muncul di layar (menandakan BLOK II aktif)."""
    try:
        # Cek selector langsung yang ringan tanpa melakukan full dump_hierarchy
        if d(resourceId="r202").exists:
            return True
        if d(text="Cek NIK").exists or d(textContains="Cek NIK").exists:
            return True
        if d(text="BERIKUTNYA BLOK III").exists:
            return True
        if not d(text="Cek ID Pelanggan").exists and d(textContains="NIK").exists:
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
    w_dev, h_dev = d.window_size()
    
    # Cek apakah layar sedang tertahan di dialog progress submit (tombol 'OK' / 'Tutup')
    btn_close_sub = d(resourceId="id.go.bpsfasih:id/btn_submit_progress_close")
    if btn_close_sub.exists:
        btn_close_sub.click()
        time.sleep(1.5)
    elif d(className="android.widget.Button", textMatches="(?i)^(ok|tutup)$").exists:
        d(className="android.widget.Button", textMatches="(?i)^(ok|tutup)$").click()
        time.sleep(1.5)

    # Cek apakah dialog filter status terbuka
    btn_tutup_filter = d(resourceId="id.go.bpsfasih:id/tutup_buttomDialogFilterAssignment")
    if btn_tutup_filter.exists or d(text="Filter Assignment By Status").exists:
        print("[*] Recovery: Terdeteksi dialog 'Filter Assignment By Status' aktif. Menutup filter...")
        if btn_tutup_filter.exists:
            btn_tutup_filter.click()
        else:
            d.press("back")
        time.sleep(1.0)

    # Cek apakah ada tombol Batal pada dialog aktif
    btn_batal = d(className="android.widget.Button", text="Batal")
    if btn_batal.exists:
        btn_batal.click()
        time.sleep(1.0)

    # Cek tombol keluar form
    for _ in range(6):
        # Cek lagi jika dialog progress submit masih muncul di loop
        btn_close_sub = d(resourceId="id.go.bpsfasih:id/btn_submit_progress_close")
        if btn_close_sub.exists:
            btn_close_sub.click()
            time.sleep(1.5)
            continue
        elif d(className="android.widget.Button", textMatches="(?i)^(ok|tutup)$").exists:
            d(className="android.widget.Button", textMatches="(?i)^(ok|tutup)$").click()
            time.sleep(1.5)
            continue

        # Jika ada loading progress, tunggu sebentar
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            time.sleep(2.0)
            continue

        curr_act = d.app_current().get("activity", "")

        # Jika sudah di halaman Daftar Assignment
        if "AssignmentActivity" in curr_act or d(text="Daftar Assignment").exists or d(text="Search:").exists:
            print("[OK] Sudah berada di halaman Daftar Assignment.")
            return True
        
        # Jika berada di Halaman Upload, klik tombol back_button
        if "UploadActivity" in curr_act or d(text="Halaman Upload").exists or d(resourceId="id.go.bpsfasih:id/back_button").exists:
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
        btn_confirm = d(resourceId="id.go.bpsfasih:id/rButton_bottomDialog")
        if not btn_confirm.exists:
            btn_confirm = d(className="android.widget.Button", textMatches="(?i)^(ya|iya)$")
        if not btn_confirm.exists:
            btn_confirm = d(textMatches="(?i)^(ya|iya)$")
        if btn_confirm.exists:
            btn_confirm.click()
            time.sleep(1.5)
            # Tunggu card_progress selesai jika ada
            for _ in range(10):
                if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                    time.sleep(1.0)
                else:
                    break
            
    curr_act = d.app_current().get("activity", "")
    return "AssignmentActivity" in curr_act or d(text="Daftar Assignment").exists or d(text="Search:").exists
