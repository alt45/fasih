import subprocess
import uiautomator2 as u2
from . import config


def get_connected_devices():
    """Mengambil daftar perangkat Android yang terhubung via ADB beserta model/nama perangkat."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        devices = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model = ""
                product = ""
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split("model:", 1)[1].replace("_", " ")
                    elif p.startswith("product:"):
                        product = p.split("product:", 1)[1].replace("_", " ")
                dev_name = model or product or "Perangkat Android"
                devices.append({"serial": serial, "name": dev_name})
        return devices
    except Exception as e:
        print(f"[!] Gagal mengecek adb devices: {e}")
        return []


def pilih_perangkat():
    """
    Menampilkan menu interaktif pemilihan perangkat Android jika terdeteksi lebih dari 1 perangkat.
    Mengembalikan serial perangkat yang dipilih, atau None jika dibatalkan/kosong.
    """
    devices = get_connected_devices()
    if not devices:
        print("[!] Tidak ada perangkat yang terdeteksi di 'adb devices'.")
        print("    Pastikan kabel USB terpasang baik dan HP dalam mode USB Debugging aktif.")
        return None
    elif len(devices) == 1:
        chosen = devices[0]
        print(f"[✓] Menggunakan perangkat: {chosen['name']} (Serial: {chosen['serial']})")
        return chosen["serial"]

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║             PILIH PERANGKAT ANDROID TARGET               ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Terdeteksi {len(devices)} perangkat Android aktif:                  ║")
    for i, dev in enumerate(devices, start=1):
        dev_label = f"[{i}] {dev['name']} ({dev['serial']})"
        print(f"║   {dev_label:<54} ║")
    print("║                                                          ║")
    print("║   [0] Batal / Keluar                                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    while True:
        pilihan = input(f"   Pilih perangkat [1-{len(devices)}] atau 0 untuk batal: ").strip()
        if not pilihan or pilihan == "0" or pilihan.lower() in ["batal", "exit", "keluar"]:
            print("[*] Pemilihan perangkat dibatalkan.")
            return None
        if pilihan.isdigit() and 1 <= int(pilihan) <= len(devices):
            chosen = devices[int(pilihan) - 1]
            print(f"[✓] Perangkat dipilih: {chosen['name']} (Serial: {chosen['serial']})\n")
            return chosen["serial"]
        print("   [⚠️] Pilihan tidak valid, silakan coba lagi.")


def connect_device(target_device=None):
    """
    Menghubungkan ke perangkat Android via uiautomator2.
    """
    try:
        chosen_serial = target_device.strip() if target_device else None

        if not chosen_serial:
            chosen_serial = pilih_perangkat()
            if not chosen_serial:
                return None
        else:
            print(f"[*] Menghubungkan ke perangkat target: {chosen_serial}...")

        d = u2.connect(chosen_serial)
        info = d.info
        print(f"[OK] Berhasil terhubung ke: {info.get('brand', '')} {info.get('model', '')} (Serial: {d.serial})")
        print(f"     Resolusi Layar: {d.window_size()}")
        
        config.DEVICE_ID = d.serial
        return d
    except Exception as e:
        print(f"[X] Gagal terhubung ke Android: {e}")
        print("    Tips penanganan:")
        print("    1. Pastikan kabel USB terpasang baik dan HP dalam mode USB Debugging aktif.")
        print("    2. Ketik 'adb devices' di terminal untuk memastikan serial HP terdaftar.")
        return None
