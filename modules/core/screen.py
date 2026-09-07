"""
Full Screen Clear (anti-overlay)
--------------------------------
Kenapa file ini ada:
rich.Console.clear() mengirim escape code ANSI ("\\x1b[2J\\x1b[H"). Itu hanya
bekerja kalau terminal punya VIRTUAL TERMINAL PROCESSING aktif. Saat toolkit
dijalankan sebagai .exe hasil PyInstaller langsung dari cmd.exe/conhost lama
(bukan Windows Terminal), VT processing itu SERING tidak aktif secara default,
terutama untuk proses yang baru dibuat/di-attach oleh PyInstaller onefile.

Akibatnya: console.clear() gagal diam-diam (tidak error, tapi juga tidak
menghapus layar). Halaman baru dicetak menimpa sebagian karakter dari frame
sebelumnya (cursor pindah ke 0,0 lalu overwrite), sehingga sisa teks frame
lama (splash art, baris menu lama, dst) masih tampak tertinggal / bertumpuk
dengan frame baru -> persis gejala "overlay/overlapping" di screenshot user.

clear_screen() di bawah ini TIDAK bergantung pada ANSI/VT sama sekali. Di
Windows ia langsung memanggil Win32 Console API (FillConsoleOutputCharacter +
FillConsoleOutputAttribute + SetConsoleCursorPosition) untuk mengosongkan
SELURUH screen buffer, lalu pindahkan cursor ke (0,0). Ini cara yang dipakai
banyak native console app dan selalu berhasil di conhost/cmd.exe/Windows
Terminal/PowerShell, dengan atau tanpa VT aktif. Kalau API itu somehow gagal
(mis. output di-redirect ke file), fallback ke `cls`/`clear` biasa.

Dipanggil dari SETIAP pergantian halaman (header(), render_main_menu_box(),
show_splash()) supaya semua modul konsisten: klik satu pilihan -> seluruh
halaman berganti bersih, bukan menumpuk di atas halaman sebelumnya.
"""

import os
import sys
import ctypes
from ctypes import wintypes


def _win32_clear() -> bool:
    """Return True kalau berhasil clear via Win32 API langsung."""
    try:
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if handle == 0 or handle == -1:
            return False

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short), ("Top", ctypes.c_short),
                ("Right", ctypes.c_short), ("Bottom", ctypes.c_short),
            ]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", wintypes.WORD),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD),
            ]

        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if not kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
            return False

        console_size = csbi.dwSize.X * csbi.dwSize.Y
        chars_written = wintypes.DWORD(0)
        top_left = COORD(0, 0)

        # 1) Timpa seluruh buffer dengan spasi.
        if not kernel32.FillConsoleOutputCharacterW(
            handle, ctypes.c_wchar(" "), console_size, top_left, ctypes.byref(chars_written)
        ):
            return False

        # 2) Reset attribute (warna) seluruh buffer supaya tidak ada sisa background lama.
        kernel32.FillConsoleOutputAttribute(
            handle, csbi.wAttributes, console_size, top_left, ctypes.byref(chars_written)
        )

        # 3) Pindahkan cursor kembali ke pojok kiri-atas.
        kernel32.SetConsoleCursorPosition(handle, top_left)
        return True
    except Exception:
        return False


def clear_screen() -> None:
    """Bersihkan SELURUH layar terminal, cross-platform, tanpa bergantung ANSI/VT."""
    if sys.platform == "win32":
        if _win32_clear():
            return
        # Fallback kalau Win32 API tidak tersedia (mis. output di-pipe ke file/log).
        try:
            os.system("cls")
        except Exception:
            pass
    else:
        try:
            os.system("clear")
        except Exception:
            print("\n" * 100)
