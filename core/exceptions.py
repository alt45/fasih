import re
import sys


class ApiLimitError(Exception):
    """
    Exception yang dilempar saat server BPS mengembalikan respon 'API LIMIT' saat pengecekan NIK.
    Seluruh proses otomasi harus dihentikan dan akun BPS harus diganti.
    """
    def __init__(self, message, cooldown_info=None):
        super().__init__(message)
        self.cooldown_info = cooldown_info


class ApiLimitResult:
    """
    Objek hasil deteksi API limit yang kompatibel dengan evaluasi boolean (if res:)
    dan unpacking (detected, cooldown = res).
    """
    def __init__(self, detected=False, cooldown=None, message=""):
        self.detected = detected
        self.cooldown = cooldown
        self.message = message

    def __bool__(self):
        return self.detected

    def __iter__(self):
        return iter((self.detected, self.cooldown))

    def __str__(self):
        return f"ApiLimitResult(detected={self.detected}, cooldown='{self.cooldown}')"


def print_api_limit_banner(cooldown_info=None, raw_message=None):
    """
    Mencetak banner peringatan bahwa akun BPS terkena API LIMIT dan harus diganti.
    Menggunakan karakter ASCII aman agar tidak error di berbagai encoding Windows (cp1252/cp437).
    """
    msg_display = raw_message.strip() if raw_message else "Permintaan API check-nikpln sudah terlampaui (limit)"
    if len(msg_display) > 52:
        msg_display = msg_display[:49] + "..."
        
    cd_display = f"Coba lagi dalam: {cooldown_info}" if cooldown_info else "Silakan ganti/rotasi ke akun BPS lain."
    if len(cd_display) > 52:
        cd_display = cd_display[:49] + "..."

    banner = (
        "\n" + "=" * 65 + "\n"
        "+----------------------------------------------------------+\n"
        "|              PERINGATAN KRITIS: API LIMIT                |\n"
        "+----------------------------------------------------------+\n"
        "| Server BPS merespon:                                     |\n"
        f"|   '{msg_display:<51}' |\n"
        f"|   {cd_display:<53} |\n"
        "|                                                          |\n"
        "| Kuota / batas panggilan API akun survei BPS telah habis. |\n"
        "| Seluruh proses OTOMASI DIHENTIKAN untuk keamanan data.   |\n"
        "|                                                          |\n"
        "| >>> SILAKAN GANTI AKUN / LOGOUT & LOGIN AKUN LAIN! <<<   |\n"
        "+----------------------------------------------------------+\n"
        + "=" * 65 + "\n"
    )
    try:
        print(banner)
    except Exception:
        pass


def check_api_limit(d=None, xml_content=None):
    """
    Mengecek apakah di layar / dialog muncul indikasi 'API LIMIT' dari server BPS.
    Mendukung format resmi FormGear Fasih BPS:
    'Permintaan API check-nikpln sudah terlampaui (limit). Coba lagi dalam 14 jam 35 menit.'
    dan berbagai variasi teks batas API lainnya.
    """
    if xml_content is None and d is not None:
        try:
            xml_content = d.dump_hierarchy()
        except Exception:
            xml_content = ""

    xml_text = xml_content or ""
    xml_lower = xml_text.lower()

    # 1. Deteksi kata kunci spesifik BPS & variasi API limit
    api_limit_keywords = [
        "terlampaui (limit)",
        "check-nikpln",
        "permintaan api",
        "sudah terlampaui",
        "terlampaui",
        "api limit",
        "api_limit",
        "limit api",
        "apilimit",
        "quota api",
        "kuota api",
        "reach api limit",
        "api rate limit",
        "rate limit",
        "batas limit api",
    ]

    matched_kw = None
    for kw in api_limit_keywords:
        if kw in xml_lower:
            matched_kw = kw
            break

    # 2. Cek regex gabungan
    if not matched_kw:
        if re.search(r"(api.*terlampaui|terlampaui.*limit|api.*limit|limit.*api|check-nikpln)", xml_lower):
            matched_kw = "regex_match"

    # 3. Cek selector uiautomator2 langsung jika tersedia
    if not matched_kw and d is not None:
        try:
            if (d(textContains="terlampaui").exists or
                    d(textContains="check-nikpln").exists or
                    d(textContains="limit").exists or
                    d(textMatches=r"(?i).*(api.*limit|limit.*api|terlampaui|check-nikpln).*").exists):
                matched_kw = "u2_selector"
        except Exception:
            pass

    if matched_kw:
        # Ekstrak waktu tunggu jika tertera di teks (misal: '14 jam 35 menit')
        cooldown = None
        m_time = re.search(r"coba lagi dalam ([^.<>\n]+)", xml_text, re.IGNORECASE)
        if m_time:
            cooldown = m_time.group(1).strip()

        # Ekstrak pesan lengkap dari teks BPS jika ada
        raw_msg = ""
        m_full = re.search(r"Permintaan API [^.<>\n]+(?:\. Coba lagi dalam [^.<>\n]+)?", xml_text, re.IGNORECASE)
        if m_full:
            raw_msg = m_full.group(0).strip()
        else:
            raw_msg = "Permintaan API check-nikpln sudah terlampaui (limit)"

        return ApiLimitResult(detected=True, cooldown=cooldown, message=raw_msg)

    return ApiLimitResult(detected=False)
