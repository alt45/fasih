import os
import sys
import datetime
import threading

_CURRENT_LOG_FILE = None
_LOG_LOCK = threading.Lock()


class TimestampStreamWrapper:
    """
    Stream wrapper untuk sys.stdout dan sys.stderr yang secara otomatis
    menambahkan timestamp di awal setiap baris teks non-kosong,
    dan menyalin seluruh output ke file log sesi proses.
    """
    _is_timestamped_wrapper = True

    def __init__(self, original_stream, file_stream=None, date_format="%Y-%m-%d %H:%M:%S"):
        self.original_stream = original_stream
        self.file_stream = file_stream
        self.date_format = date_format
        self.lock = threading.Lock()
        self._at_line_start = True

    def write(self, message):
        if not message:
            return
        with self.lock:
            lines = message.split("\n")
            for i, line in enumerate(lines):
                if i > 0:
                    self.original_stream.write("\n")
                    if self.file_stream:
                        try:
                            self.file_stream.write("\n")
                        except Exception:
                            pass
                    self._at_line_start = True

                if line:
                    if self._at_line_start and line.strip():
                        now_str = datetime.datetime.now().strftime(self.date_format)
                        prefix = f"[{now_str}] "
                        self.original_stream.write(prefix)
                        if self.file_stream:
                            try:
                                self.file_stream.write(prefix)
                            except Exception:
                                pass
                        self._at_line_start = False

                    self.original_stream.write(line)
                    if self.file_stream:
                        try:
                            self.file_stream.write(line)
                        except Exception:
                            pass

    def flush(self):
        with self.lock:
            try:
                self.original_stream.flush()
            except Exception:
                pass
            if self.file_stream:
                try:
                    self.file_stream.flush()
                except Exception:
                    pass

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()

    def fileno(self):
        return getattr(self.original_stream, "fileno", lambda: None)()


def setup_logger(process_name="fasih", log_to_file=True, log_dir="logs", date_format="%Y-%m-%d %H:%M:%S"):
    """
    Mengaktifkan timestamp pada sys.stdout dan sys.stderr serta membuat file log
    khusus untuk proses yang sedang berjalan.
    
    :param process_name: Nama proses / skrip (misal: 'main', 'update_nik', 'cek_idpel')
    :param log_to_file: Apakah menyimpan output ke file .log di log_dir
    :param log_dir: Folder direktori penyimpanan file log
    :param date_format: Format datetime untuk timestamp awalan log
    :return: Path file log yang sedang aktif (atau None jika tidak disimpan ke file)
    """
    global _CURRENT_LOG_FILE

    with _LOG_LOCK:
        # Jika sudah dibungkus sebelumnya, jangan bungkus lagi
        if getattr(sys.stdout, "_is_timestamped_wrapper", False):
            return _CURRENT_LOG_FILE

        file_stream = None
        if log_to_file:
            try:
                os.makedirs(log_dir, exist_ok=True)
                timestamp_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_name = "".join(c for c in process_name if c.isalnum() or c in ("-", "_")).lower() or "app"
                log_filename = f"{clean_name}_{timestamp_file}.log"
                log_path = os.path.join(log_dir, log_filename)
                
                # Membuka file log dalam mode append utf-8
                file_stream = open(log_path, mode="a", encoding="utf-8", buffering=1)
                _CURRENT_LOG_FILE = log_path
            except Exception as e:
                sys.stderr.write(f"[!] Gagal membuat file log: {e}\n")

        # Bungkus stdout dan stderr
        sys.stdout = TimestampStreamWrapper(sys.stdout, file_stream=file_stream, date_format=date_format)
        sys.stderr = TimestampStreamWrapper(sys.stderr, file_stream=file_stream, date_format=date_format)

        if _CURRENT_LOG_FILE:
            print(f"[*] Sesi proses '{process_name}' dimulai. File log disimpan ke: {_CURRENT_LOG_FILE}")

    return _CURRENT_LOG_FILE


def get_current_log_path():
    """Mengembalikan path file log yang saat ini aktif."""
    return _CURRENT_LOG_FILE
