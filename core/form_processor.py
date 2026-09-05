import time
from .config import (
    CSV_INPUT,
    OUT_SUKSES,
    OUT_TIDAK_DITEMUKAN,
    OUT_NIK_TIDAK_DITEMUKAN,
    OUT_GAGAL,
)
from .csv_utils import append_to_log, remove_idpel_from_input_csv
from .ui_helpers import (
    back_to_assignment_list,
    clear_search_box,
    hide_keyboard,
    scroll_down_small,
    is_nik_present_on_screen,
)
from .nik_provider import is_daya_450


def process_update_nik(d, row_data, csv_input_path=CSV_INPUT, skip_cek_idpel=False, fallback_nik_provider=None):
    """
    Memproses satu baris data IDPEL:
    Cari IDPEL -> Buka -> BLOK I (Cek IDPEL jika Prabayar / Skip jika Pasca) -> BLOK II Ganti NIK & Cek NIK (Dukungan Fallback Daya) -> Kirim
    """
    idpel = str(row_data["id_pelanggan"]).strip()
    nik_baru = str(row_data["NIK_Perbaikan"]).strip()
    
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
        remove_idpel_from_input_csv(csv_input_path, idpel)
        clear_search_box(d)
        return "IDPEL_NOT_FOUND"

    print(f"[OK] Data IDPEL {idpel} ditemukan di tabel!")

    # 4. Klik tanda '+' untuk expand detail baris (ikon '+' berada di sisi kiri sel kolom pertama)
    print("[*] Meng-expand baris tabel (klik '+')...")
    expanded = False
    for attempt in range(4):
        btn_plus = d(textContains="+")
        if btn_plus.exists:
            try:
                b = btn_plus.bounds()
                x_plus = b[0] + 25  # Sentuh sisi kiri sel tepat di ikon '+'
                y_plus = (b[1] + b[3]) // 2
                d.click(x_plus, y_plus)
            except Exception:
                btn_plus.click()
        else:
            d.click(57, 886)

        # Tunggu sampai tombol Aksi muncul
        for _ in range(6):
            time.sleep(0.5)
            if d(className="android.widget.Button", text="Aksi").exists or d(text="Aksi").exists:
                expanded = True
                break
        if expanded:
            print("[OK] Baris tabel berhasil diexpand! Tombol 'Aksi' tersedia.")
            break
        print(f"[*] Tombol Aksi belum tampak (percobaan {attempt+1}), mencoba klik '+' lagi...")

    # 5. Klik tombol 'Aksi'
    print("[*] Mengklik tombol 'Aksi'...")
    btn_aksi = d(className="android.widget.Button", text="Aksi")
    if not btn_aksi.exists:
        btn_aksi = d(text="Aksi")
    if btn_aksi.exists:
        btn_aksi.click()
    else:
        # Fallback koordinat center tombol Aksi yang terverifikasi
        d.click(258, 1325)

    # 6. Tunggu dan klik 'BUKA' pada dialog
    print("[*] Menunggu menu dialog 'BUKA'...")
    btn_buka = None
    for _ in range(8):
        time.sleep(0.5)
        if d(resourceId="id.go.bpsfasih:id/openAssignment_b").exists:
            btn_buka = d(resourceId="id.go.bpsfasih:id/openAssignment_b")
            break
        elif d(text="BUKA").exists:
            btn_buka = d(text="BUKA")
            break

    if not btn_buka or not btn_buka.exists:
        # Percobaan ulang klik Aksi jika dialog belum terbuka
        btn_aksi = d(className="android.widget.Button", text="Aksi")
        if btn_aksi.exists:
            btn_aksi.click()
            time.sleep(1.5)
            if d(resourceId="id.go.bpsfasih:id/openAssignment_b").exists:
                btn_buka = d(resourceId="id.go.bpsfasih:id/openAssignment_b")
            elif d(text="BUKA").exists:
                btn_buka = d(text="BUKA")

    if not btn_buka or not btn_buka.exists:
        raise Exception("Tombol 'BUKA' tidak ditemukan di menu dialog Aksi.")
    
    print("[OK] Tombol 'BUKA' ditemukan! Mengklik 'BUKA'...")
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
    for _ in range(30):
        if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
            time.sleep(0.3)
        else:
            break
    time.sleep(0.5)

    # 8. BLOK I: Verifikasi halaman terbuka, Geser layar agar Cek ID Pelanggan terangkat, & Klik
    print("[*] Menunggu halaman BLOK I termuat...")
    for _ in range(20):
        if d(text="Cek ID Pelanggan").exists or d(text="BERIKUTNYA BLOK II").exists or d(textContains="ID pelanggan").exists or d(textContains="BLOK I").exists:
            break
        time.sleep(0.3)

    if not skip_cek_idpel:
        # Pastikan posisi tombol 'Cek ID Pelanggan' tidak terhimpit di batas bawah layar.
        # Secara default di BLOK I tombol berada di y > 1400 mepet navigation bar.
        # Selalu geser layar 1 kali jika posisi tombol mepet bawah (y > 1300) atau belum terlihat.
        btn_cek_idpel = d(text="Cek ID Pelanggan")
        need_scroll = True
        if btn_cek_idpel.exists:
            try:
                info = btn_cek_idpel.info
                bounds = info.get("bounds", {})
                top_y = bounds.get("top", 0)
                bottom_y = bounds.get("bottom", 1600)
                if 250 <= top_y and bottom_y <= 1300:
                    need_scroll = False
            except Exception:
                pass

        if need_scroll:
            print("[*] BLOK I: Menggeser layar sedikit agar tombol 'Cek ID Pelanggan' terangkat ke area nyaman...")
            scroll_down_small(d, duration=0.35)
            time.sleep(0.6)
            btn_cek_idpel = d(text="Cek ID Pelanggan")

        if not btn_cek_idpel.exists:
            # Coba scroll 1 kali lagi jika belum terlihat
            scroll_down_small(d, duration=0.35)
            time.sleep(0.6)
            btn_cek_idpel = d(text="Cek ID Pelanggan")

        if not btn_cek_idpel or not btn_cek_idpel.exists:
            raise Exception("Gagal masuk ke BLOK I / Tombol 'Cek ID Pelanggan' tidak ditemukan.")

        # Ambil koordinat fisik tombol untuk sentuhan langsung (menjamin event onclick WebView terpemicu)
        try:
            cx, cy = btn_cek_idpel.center()
            print(f"[*] BLOK I: Mengklik fisik 'Cek ID Pelanggan' di ({cx}, {cy})...")
            d.click(cx, cy)
            time.sleep(0.5)
            # Penegasan sentuhan kedua jika belum memicu respon
            if not (d(textContains="Hasil pengecekan").exists or d(textContains="STATUS").exists or d(resourceId="id.go.bpsfasih:id/card_progress").exists):
                d.click(cx, cy)
        except Exception as e:
            print(f"[!] Gagal klik fisik ({e}), fallback klik logis...")
            btn_cek_idpel.click()
        
        # Tunggu respon verifikasi ID Pelanggan dari server (card_progress atau teks hasil pengecekan)
        print("[*] Menunggu respon Cek ID Pelanggan...")
        for _ in range(25):
            time.sleep(0.3)
            if d(textContains="Hasil pengecekan").exists or d(textContains="STATUS").exists:
                print("[OK] Hasil pengecekan ID Pelanggan berhasil terverifikasi!")
                break
            if not d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                pass
        hide_keyboard(d)
        time.sleep(0.5)
    else:
        print("[*] BLOK I (Pasca Bayar): Melewati 'Cek ID Pelanggan' sesuai konfigurasi...")
        time.sleep(0.5)

    # 9. Klik 'BERIKUTNYA BLOK II' (Hanya klik 1x -> Cek kata NIK di layar -> Jika belum ada, klik lagi)
    print("[*] Berpindah ke BLOK II...")
    in_blok2 = False
    
    for attempt in range(1, 8):
        # 1. Cek terlebih dahulu apakah kata NIK sudah muncul di layar
        if is_nik_present_on_screen(d):
            print(f"[OK] Kata/elemen NIK sudah terdeteksi di layar (Percobaan {attempt})! Masuk ke BLOK II.")
            in_blok2 = True
            break

        print(f"[*] Percobaan {attempt}/7: Mengklik tombol 'BERIKUTNYA BLOK II' (1 KALI)...")
        hide_keyboard(d)

        # Cari tombol BERIKUTNYA BLOK II
        btn_next_b2 = d(resourceId="fasih-form-nav-next-button")
        if not btn_next_b2.exists:
            btn_next_b2 = d(text="BERIKUTNYA BLOK II")
        if not btn_next_b2.exists:
            btn_next_b2 = d(textContains="BERIKUTNYA")

        # Jika tombol navigasi belum terlihat di layar, scroll sedikit ke bawah
        if not btn_next_b2.exists:
            print("[*] Tombol belum tampak, mencoba scroll ke bawah...")
            scroll_down_small(d)
            time.sleep(0.8)
            btn_next_b2 = d(resourceId="fasih-form-nav-next-button")
            if not btn_next_b2.exists:
                btn_next_b2 = d(text="BERIKUTNYA BLOK II")

        # KLIK HANYA 1 KALI (TIDAK DOUBLE CLICK)
        if btn_next_b2.exists:
            try:
                cx, cy = btn_next_b2.center()
                print(f"[*] Klik 1x sentuhan fisik tombol di ({cx}, {cy})...")
                d.click(cx, cy)
            except Exception:
                print(f"[*] Klik 1x logis tombol BERIKUTNYA...")
                btn_next_b2.click()
        else:
            # Fallback koordinat adaptif persentase layar (sudut kanan-bawah area navigasi)
            w, h = d.window_size()
            fb_x = int(w * 0.75)
            fb_y = int(h * 0.94)
            print(f"[*] Fallback: Klik 1x di area navigasi ({fb_x}, {fb_y})...")
            d.click(fb_x, fb_y)

        # 2. Tunggu respon dan cek apakah kata/field 'NIK' sudah muncul di layar
        print("[*] Memeriksa apakah kata 'NIK' sudah muncul di layar...")
        for wait_t in range(4):
            time.sleep(1.0)
            if d(resourceId="id.go.bpsfasih:id/card_progress").exists:
                continue
            if is_nik_present_on_screen(d):
                print(f"[OK] Kata 'NIK' terdeteksi di layar pada detik ke-{wait_t+1}! Berhasil masuk ke BLOK II.")
                in_blok2 = True
                break

        if in_blok2:
            break
        else:
            print("[!] Kata 'NIK' belum muncul di layar. Bersiap klik tombol Berikutnya lagi...")

    if not in_blok2:
        if is_nik_present_on_screen(d):
            print("[OK] Kata 'NIK' terkonfirmasi aktif di layar.")
            in_blok2 = True
        else:
            raise Exception("Gagal berpindah ke BLOK II: kata 'NIK' tidak ditemukan setelah mencoba klik tombol Berikutnya.")

    # 10. BLOK II: Input NIK Baru & Klik 'Cek NIK'
    print("[*] BLOK II: Mencari field input NIK penghuni...")
    input_nik = None
    
    # Tunggu dan cari elemen input NIK dengan polling adaptif
    for poll in range(8):
        # 1. Coba resourceId r202 child EditText
        cand = d(resourceId="r202").child(className="android.widget.EditText")
        if cand.exists:
            input_nik = cand
            break
            
        # 2. Coba XPath di dalam r202
        cand_xp = d.xpath('//*[@resource-id="r202"]//android.widget.EditText')
        if cand_xp.exists:
            input_nik = cand_xp
            break

        # 3. Coba ID dinamis FormGear
        for dyn_id in ["textfield-cl-29-input", "textfield-cl-30-input", "textfield-cl-32-input", "textfield-cl-28-input"]:
            cand_dyn = d(resourceId=dyn_id)
            if cand_dyn.exists:
                input_nik = cand_dyn
                break
        if input_nik:
            break

        # 4. Coba ambil dari seluruh EditText di layar Blok II
        all_edits = d(className="android.widget.EditText")
        if all_edits.count >= 2:
            # Di BLOK II: index 0 biasanya Nama Penghuni (r201), index 1 adalah NIK (r202)
            input_nik = all_edits[1]
            break
        elif all_edits.count == 1:
            # Jika r201 di-collapse atau tidak tampak, bisa jadi input pertama adalah NIK
            res_n = all_edits[0].info.get("resourceName", "")
            if "r202" in res_n or "nik" in res_n.lower():
                input_nik = all_edits[0]
                break

        # Jika di percobaan ke-2 belum tampak, scroll down sedikit untuk memunculkan NIK ke viewport
        if poll in [2, 4]:
            print("[*] NIK belum tampak di viewport, mencoba scroll down sedikit...")
            scroll_down_small(d)

        time.sleep(1.0)

    if not input_nik or not input_nik.exists:
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
    
    # Jika belum tampak, coba scroll down sedikit agar tombol Cek NIK terlihat
    if not btn_cek_nik.exists:
        scroll_down_small(d)
        time.sleep(1.0)
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
        daya = str(row_data.get("daya", "")).strip()
        
        # Cek apakah fallback NIK aktif dan daya pelanggan diperbolehkan untuk fallback (bukan daya 450)
        if fallback_nik_provider is not None:
            if is_daya_450(daya):
                print(f"[!] IDPEL {idpel}: Daya 450 terdeteksi ('{daya}'). Sesuai aturan, TIDAK ADA fallback NIK cadangan.")
            elif not daya:
                print(f"[!] IDPEL {idpel}: Nilai daya kosong/tidak terdefinisi. Fallback NIK dilewati demi keamanan.")
            else:
                print(f"[*] IDPEL {idpel}: Daya '{daya}' (bukan daya 450). Menjalankan Fallback NIK dari nik.json...")
                fallback_nik = fallback_nik_provider.get_next()
                if fallback_nik:
                    print(f"[*] Menginput Fallback NIK: {fallback_nik}...")
                    input_nik.click()
                    time.sleep(0.3)
                    input_nik.clear_text()
                    time.sleep(0.2)
                    input_nik.set_text(fallback_nik)
                    time.sleep(0.5)
                    hide_keyboard(d)
                    time.sleep(1.0)
                    
                    # Klik Cek NIK ulang
                    if btn_cek_nik.exists:
                        cx, cy = btn_cek_nik.center()
                        print(f"[*] Mengklik 'Cek NIK' ulang di ({cx}, {cy})...")
                        d.click(cx, cy)
                        time.sleep(0.6)
                        d.click(cx, cy)
                    else:
                        d.click(99, 935)
                        time.sleep(0.6)
                        d.click(99, 935)
                    
                    print("[*] Menunggu pemadanan Fallback NIK dari server (max 12 detik)...")
                    for wait_fb in range(12):
                        time.sleep(1.0)
                        xml_chk_fb = d.dump_hierarchy()
                        if d(textContains="TIDAK DITEMUKAN").exists or "TIDAK DITEMUKAN" in xml_chk_fb:
                            print(f"[!] Fallback NIK {fallback_nik} detik ke-{wait_fb+1}: TIDAK DITEMUKAN!")
                            break
                        elif d(textContains="SESUAI").exists or "SESUAI" in xml_chk_fb or "DITEMUKAN" in xml_chk_fb:
                            print(f"[OK] Fallback NIK {fallback_nik} detik ke-{wait_fb+1}: SESUAI / DITEMUKAN!")
                            nik_baru = fallback_nik
                            nik_match_result = "DITEMUKAN"
                            break

    # Jika setelah evaluasi fallback NIK tetap TIDAK DITEMUKAN:
    if nik_match_result == "TIDAK DITEMUKAN":
        daya = str(row_data.get("daya", "")).strip()
        if is_daya_450(daya):
            ket_log = f"NIK Tidak Ditemukan (Daya 450: {daya})"
        elif fallback_nik_provider is not None and daya:
            ket_log = f"NIK Awal & Fallback Tidak Ditemukan (Daya: {daya})"
        else:
            ket_log = "NIK Tidak Ditemukan saat pemadanan"

        print(f"[!] Pemadanan Gagal: NIK {nik_baru} untuk IDPEL {idpel} TIDAK DITEMUKAN.")
        print(f"[*] Mencatat ke '{OUT_NIK_TIDAK_DITEMUKAN}' dan menghapus dari '{csv_input_path}'...")
        append_to_log(OUT_NIK_TIDAK_DITEMUKAN, {
            "id_pelanggan": idpel,
            "NIK_Perbaikan": nik_baru,
            "keterangan": ket_log,
            "waktu": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        remove_idpel_from_input_csv(csv_input_path, idpel)
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
    remove_idpel_from_input_csv(csv_input_path, idpel)
    clear_search_box(d)
    return "SUKSES"
