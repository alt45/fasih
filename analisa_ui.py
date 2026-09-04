import os
import sys
import json
import time
from datetime import datetime

# Pastikan output utf-8 aman di terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uiautomator2 as u2

OUTPUT_DIR = "ui_dump"

def connect_device():
    try:
        print("[*] Mendeteksi dan menghubungkan ke perangkat Android...")
        d = u2.connect()  # otomatis connect ke device yang aktif
        info = d.info
        print(f"[OK] Terhubung ke: {info.get('brand')} {info.get('model')} (Serial: {d.serial})")
        print(f"     Resolusi Layar: {d.window_size()}")
        print(f"     Aplikasi Aktif: {info.get('currentPackageName')}")
        return d
    except Exception as e:
        print(f"[X] Gagal terhubung ke device: {e}")
        return None

def analyze_screen(d):
    print("\n" + "=" * 60)
    print("         ANALISIS ELEMEN LAYAR ANDROID (UIAUTOMATOR)")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Simpan dump XML
    xml_file = os.path.join(OUTPUT_DIR, f"hierarchy_{timestamp}.xml")
    try:
        xml_content = d.dump_hierarchy()
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"[OK] Dump XML tersimpan di: {xml_file}")
    except Exception as e:
        print(f"[!] Gagal menyimpan XML: {e}")

    # 2. Screenshot
    img_file = os.path.join(OUTPUT_DIR, f"screen_{timestamp}.png")
    try:
        d.screenshot(img_file)
        print(f"[OK] Screenshot tersimpan di: {img_file}")
    except Exception as e:
        print(f"[!] Gagal screenshot: {e}")

    # 3. Cari Semua EditText (Field Input)
    print("\n[+] MENCARI FIELD INPUT (EditText / Input Form):")
    print("-" * 60)
    
    edit_texts = d(className="android.widget.EditText")
    count_edit = edit_texts.count
    print(f"Total EditText ditemukan: {count_edit}")
    
    inputs_found = []
    for i in range(count_edit):
        try:
            elem = edit_texts[i]
            info = elem.info
            bounds = info.get("bounds", {})
            res_id = info.get("resourceName", "")
            text = info.get("text", "")
            hint = info.get("contentDescription", "")
            focused = info.get("focused", False)
            enabled = info.get("enabled", True)
            
            print(f"  [{i+1}] Resource-ID : {res_id or '(tidak ada ID)'}")
            print(f"      Text Saat Ini : '{text}'")
            if hint:
                print(f"      Hint/Desc     : '{hint}'")
            center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
            center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
            print(f"      Posisi/Bounds : {bounds} (Center: {center_x}, {center_y})")
            print(f"      Enabled/Focus : Enabled={enabled}, Focused={focused}")
            print()
            
            inputs_found.append({
                "index": i,
                "resourceId": res_id,
                "text": text,
                "hint": hint,
                "bounds": bounds,
                "enabled": enabled
            })
        except Exception as e:
            print(f"  [{i+1}] Gagal membaca info: {e}")

    # 4. Cari Elemen Teks yang berdekatan atau Label Form
    print("\n[+] MENCARI LABEL / TEKS TERKAIT INPUT & FORM:")
    print("-" * 60)
    text_views = d(className="android.widget.TextView")
    count_tv = text_views.count
    print(f"Total TextView ditemukan: {count_tv}")
    for i in range(min(count_tv, 40)):
        try:
            tv = text_views[i]
            info = tv.info
            t = info.get("text", "").strip()
            rid = info.get("resourceName", "")
            if t:
                print(f"  - '{t}' (ID: {rid or '-'}) | Bounds: {info.get('bounds')}")
        except:
            pass

    # 5. Cari Tombol (Button / Clickable penting)
    print("\n[+] TOMBOL & AKSI CLICKABLE DI LAYAR:")
    print("-" * 60)
    clickables = d(clickable=True)
    count_click = clickables.count
    print(f"Total Elemen Clickable: {count_click}")
    for i in range(min(count_click, 35)):
        try:
            elem = clickables[i]
            info = elem.info
            txt = info.get("text", "") or info.get("contentDescription", "")
            cls = info.get("className", "").split(".")[-1]
            rid = info.get("resourceName", "")
            print(f"  * [{cls}] '{txt}' | ID: {rid or '-'} | Bounds: {info.get('bounds')}")
        except:
            pass

    print("\n" + "=" * 60)
    print("[OK] Analisis selesai!")

if __name__ == "__main__":
    dev = connect_device()
    if dev:
        analyze_screen(dev)
