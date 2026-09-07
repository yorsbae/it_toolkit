"""
Print Bridge - SERVER (Host)
=============================
Jalankan menu ini di PC yang PRINTERNYA SUDAH TERPASANG dan bisa print
normal (driver sudah ada di PC ini). PC LAIN (client) tidak perlu install
driver printer apa pun sama sekali - cukup bisa connect ke PC ini lewat
jaringan (LAN/WiFi yang sama, atau VPN), lalu kirim file untuk dicetak.

Kenapa client tidak butuh driver:
Client TIDAK pernah bicara langsung ke printer atau ke driver-nya. Client
cuma mengirim file mentah (PDF/gambar/teks) lewat socket TCP biasa ke PC
ini. PC ini (server) yang membuka file itu dan mencetaknya pakai driver
YANG SUDAH ADA di PC ini (lewat handler "Print" bawaan Windows - sama
seperti klik kanan file > Print di File Explorer). Jadi tidak ada driver
yang perlu dikirim/diinstall ke client sama sekali.

Protokol (TCP socket sederhana, tanpa dependency tambahan):
  1. Client connect ke <host>:<port>
  2. Client kirim SATU baris JSON header, diakhiri newline:
     {"filename": "...", "size": N, "printer": "" atau nama printer, "sender": "hostname client"}
  3. Server balas "READY\n" (atau "ERROR <pesan>\n" kalau ditolak - mis.
     ukuran file tidak valid)
  4. Client kirim PERSIS N byte isi file
  5. Server simpan ke folder spool lokal, cetak lewat OS, lalu balas SATU
     baris JSON hasil: {"status": "PRINTED"/"FAILED", "detail": "..."}

Karena server mencetak lewat jalur print NORMAL Windows (bukan raw socket
langsung ke port printer), job yang lewat sini otomatis ikut tercatat di
Windows Print Service log - jadi juga akan muncul di modul terpisah
[16] PRINT MANAGEMENT (job history, usage report, dst) tanpa kerja tambahan.
"""

import json
import os
import socket
import socketserver
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from ..core.config import BASE_DIR
from ..core.executor import is_admin, run_command

SPOOL_DIR = BASE_DIR / "print_bridge_spool"
SPOOL_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB, batas aman biar tidak habiskan disk/RAM
RECV_TIMEOUT = 120  # detik, per koneksi client


def _print_file_windows(path: Path, printer_name: str = None):
    """Cetak file pakai handler 'Print' bawaan Windows untuk tipe file itu
    (PDF lewat Edge, DOCX lewat Word, gambar lewat Photos, TXT lewat
    Notepad, dst - sama seperti klik-kanan > Print di Explorer).

    CATATAN JUJUR: os.startfile(path, "print") itu ASYNC (fire-and-forget) -
    Windows tidak memberi cara sinkron untuk menunggu sampai kertas benar-
    benar keluar dari printer. Fungsi ini hanya bisa memastikan PERINTAH
    print berhasil dikirim ke aplikasi handler-nya. Kalau mau kepastian
    100% tercetak, cek [16] PRINT MANAGEMENT > Print Job History setelah
    beberapa detik (itu berdasar Windows Print Service log yang sebenarnya).

    Return (ok: bool, detail: str).
    """
    if sys.platform != "win32":
        return False, "Print hanya didukung saat server berjalan di Windows"

    original_default = None
    try:
        if printer_name:
            from ..printer.diagnostics import get_default_printer, set_default_printer
            current = get_default_printer()
            original_default = current.detail if current.state == "PASS" else None
            r = set_default_printer(printer_name)
            if r.state != "PASS":
                return False, f"Printer '{printer_name}' tidak ditemukan di server: {r.detail}"

        os.startfile(str(path), "print")
        # os.startfile async - beri jeda supaya command print sempat ter-spawn
        # sebelum kita restore default printer (kalau tadi diubah sementara).
        time.sleep(2)
        return True, f"Perintah print terkirim ke {printer_name or '(default printer server)'}"
    except OSError as e:
        return False, (
            f"Gagal print: {e}. Kemungkinan tipe file '{path.suffix}' tidak "
            f"punya aplikasi default dengan verb 'Print' di server ini."
        )
    finally:
        if printer_name and original_default:
            try:
                from ..printer.diagnostics import set_default_printer
                set_default_printer(original_default)
            except Exception:
                pass


def _ensure_firewall_rule(port: int) -> None:
    """Best-effort: buka port di Windows Firewall kalau dijalankan sebagai
    admin. Kalau bukan admin, tidak diblokir - Windows biasanya tetap akan
    menampilkan prompt 'Allow this app' otomatis saat socket mulai listen."""
    if sys.platform != "win32" or not is_admin():
        return
    try:
        run_command(
            'netsh advfirewall firewall add rule '
            'name="IT Support Toolkit - Print Bridge" '
            f'dir=in action=allow protocol=TCP localport={port}',
            timeout=10,
        )
    except Exception:
        pass


class _JobHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(RECV_TIMEOUT)
        client_ip = self.client_address[0]
        rfile = self.request.makefile("rb")
        wfile = self.request.makefile("wb")
        sender = client_ip
        filename = "job.dat"
        size = 0
        try:
            header_line = rfile.readline()
            if not header_line:
                return
            header = json.loads(header_line.decode("utf-8", errors="replace").strip())
            filename = os.path.basename(header.get("filename") or "job.dat")[:100] or "job.dat"
            size = int(header.get("size", 0))
            printer = (header.get("printer") or "").strip() or None
            sender = (header.get("sender") or "").strip() or client_ip

            if size <= 0 or size > MAX_FILE_SIZE:
                wfile.write(b"ERROR Ukuran file tidak valid atau melebihi batas 200MB\n")
                wfile.flush()
                self.server.notify(sender, filename, size, printer, "FAILED", "Ukuran file ditolak")
                return

            wfile.write(b"READY\n")
            wfile.flush()

            data = rfile.read(size)
            if len(data) != size:
                self._send_result(wfile, "FAILED", "Transfer terputus sebelum selesai")
                self.server.notify(sender, filename, size, printer, "FAILED", "Transfer terputus")
                return

            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_sender = "".join(ch for ch in sender if ch.isalnum() or ch in "-_.")[:40] or "client"
            spool_path = SPOOL_DIR / f"{ts}_{safe_sender}_{filename}"
            with open(spool_path, "wb") as f:
                f.write(data)

            ok, detail = _print_file_windows(spool_path, printer)
            status = "PRINTED" if ok else "FAILED"
            self._send_result(wfile, status, detail)
            self.server.notify(sender, filename, size, printer, status, detail)

        except Exception as e:
            try:
                self._send_result(wfile, "FAILED", f"Server error: {e}")
            except Exception:
                pass
            try:
                self.server.notify(sender, filename, size, None, "FAILED", f"Server error: {e}")
            except Exception:
                pass

    @staticmethod
    def _send_result(wfile, status: str, detail: str):
        wfile.write((json.dumps({"status": status, "detail": detail}) + "\n").encode("utf-8"))
        wfile.flush()


class PrintBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host, port, on_job=None):
        super().__init__((host, port), _JobHandler)
        self._on_job = on_job or (lambda *a, **k: None)

    def notify(self, sender, filename, size, printer, status, detail):
        try:
            self._on_job(sender, filename, size, printer, status, detail)
        except Exception:
            pass


def start_server(host: str = "0.0.0.0", port: int = 9600, on_job=None):
    """Mulai Print Bridge server di background thread. Return (server, thread)."""
    _ensure_firewall_rule(port)
    server = PrintBridgeServer(host, port, on_job=on_job)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def stop_server(server: PrintBridgeServer) -> None:
    try:
        server.shutdown()
        server.server_close()
    except Exception:
        pass


def local_ip_guess() -> str:
    """Tebak IP LAN PC ini (bukan 127.0.0.1) supaya bisa ditunjukkan ke client."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
