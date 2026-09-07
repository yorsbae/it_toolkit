"""
Print Bridge - CLIENT
=======================
Kirim file ke PC lain yang menjalankan Print Bridge SERVER (menu [01] di
modul ini), supaya dicetak DI SANA. PC ini (client) TIDAK perlu driver
printer apa pun terpasang - cukup bisa connect ke server lewat jaringan.
Cocok dijalankan dari flashdisk toolkit di PC mana pun tanpa install apa-apa.
"""

import json
import os
import socket


def send_file(host: str, port: int, filepath: str, printer: str = None, timeout: int = 60):
    """Kirim satu file ke Print Bridge server untuk dicetak.
    Return (ok: bool, detail: str)."""
    if not os.path.isfile(filepath):
        return False, f"File tidak ditemukan: {filepath}"

    size = os.path.getsize(filepath)
    if size <= 0:
        return False, "File kosong (0 byte)"

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except Exception as e:
        return False, f"Gagal connect ke {host}:{port} - {e}"

    try:
        sock.settimeout(timeout)
        wfile = sock.makefile("wb")
        rfile = sock.makefile("rb")

        header = {
            "filename": os.path.basename(filepath),
            "size": size,
            "printer": printer or "",
            "sender": socket.gethostname(),
        }
        wfile.write((json.dumps(header) + "\n").encode("utf-8"))
        wfile.flush()

        ready_line = rfile.readline()
        if not ready_line:
            return False, "Tidak ada respon dari server (koneksi terputus)"
        ready = ready_line.decode("utf-8", errors="replace").strip()
        if not ready.startswith("READY"):
            return False, f"Server menolak job: {ready}"

        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                wfile.write(chunk)
        wfile.flush()

        result_line = rfile.readline()
        if not result_line:
            return False, "Server tidak mengirim hasil (koneksi terputus saat mencetak)"
        try:
            result = json.loads(result_line.decode("utf-8", errors="replace").strip())
        except Exception:
            return False, f"Respon server tidak dikenali: {result_line!r}"

        ok = result.get("status") == "PRINTED"
        return ok, result.get("detail", "")
    except socket.timeout:
        return False, "Timeout - server tidak merespon (cek koneksi jaringan / server masih menyala?)"
    except Exception as e:
        return False, f"Error saat kirim file: {e}"
    finally:
        try:
            sock.close()
        except Exception:
            pass


def test_connection(host: str, port: int, timeout: int = 5):
    """Cek cepat apakah ada Print Bridge server aktif di host:port, tanpa kirim file apa pun."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, "Server aktif dan menerima koneksi"
    except socket.timeout:
        return False, "Timeout - tidak ada respon (server mati / firewall / IP salah)"
    except ConnectionRefusedError:
        return False, "Koneksi ditolak - server tidak berjalan di port ini"
    except Exception as e:
        return False, str(e)
