"""
Shared UI Helpers
----------------------
header() untuk submenu = plain text (sesuai PRD §6-32, semua submenu contoh
di PRD memang plain text tanpa box).
Box ganda + status bar (PRD §3/§5) HANYA dipakai di Main Menu -> lihat
render_main_menu_box() di bawah, dipanggil dari main.py.
"""

from datetime import datetime

from rich.console import Console
from rich.text import Text

from .config import load_config
from .status import render_line, symbol, color
from .report import generate_report
from .executor import is_admin
from .screen import clear_screen
from .theme import get_theme

console = Console()
_cfg = load_config()
APP_NAME = _cfg.get("app_name", "IT SUPPORT TOOLKIT")
VERSION = _cfg.get("version", "1.0.0")

BOX_WIDTH = 78


def header(subtitle: str = ""):
    """Submenu header - breadcrumb + garis aksen (bukan box, sesuai PRD §6-32
    yang contoh submenu-nya memang plain text). Warna ikut theme aktif
    (Settings > Theme) dan bisa berubah langsung tanpa restart.
    Ganti halaman penuh (anti-overlay): lihat modules/core/screen.py."""
    clear_screen()
    theme = get_theme()
    admin_tag = "[green]ADMIN[/green]" if is_admin() else "[yellow]USER[/yellow]"
    clock = datetime.now().strftime("%H:%M:%S")

    if subtitle:
        crumb = f"[{theme['accent']}]{APP_NAME}[/{theme['accent']}] [dim]\u25b8[/dim] [{theme['accent']}]{subtitle}[/{theme['accent']}]"
    else:
        crumb = f"[{theme['accent']}]{APP_NAME}[/{theme['accent']}]"

    left = Text.from_markup(crumb)
    right = Text.from_markup(f"[dim]{admin_tag}  \u2022  {clock}[/dim]")
    pad = max(1, BOX_WIDTH - len(left.plain) - len(right.plain))
    console.print(left + Text(" " * pad) + right)
    console.print(f"[{theme['rule']}]" + "\u2500" * BOX_WIDTH + f"[/{theme['rule']}]\n")


def show_results(results, module_name: str = None, save_report: bool = False):
    for r in results:
        line = render_line(r.label + (f" - {r.detail}" if r.detail else ""), r.state)
        console.print(line)
        if r.recommendation:
            console.print(f"    [yellow]-> {r.recommendation}[/yellow]")
    if save_report and module_name:
        txt_path, _, overall = generate_report(module_name, [r for r in results if hasattr(r, "state")])
        console.print(f"\n[bold]RESULT:[/bold] {overall}")
        console.print(f"[dim]Report saved: {txt_path}[/dim]")


def confirm(prompt: str) -> bool:
    """Ctrl+C saat konfirmasi dianggap 'No' (aman, tidak menjalankan aksi
    destruktif), konsisten dengan read_choice() yang treat Ctrl+C sebagai batal/back."""
    try:
        return console.input(f"[yellow]{prompt} [Y/N]: [/yellow]").strip().lower() == "y"
    except KeyboardInterrupt:
        console.print()
        return False


def pause():
    try:
        console.input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        console.print()


def read_choice(prompt: str = "[bold cyan]> [/bold cyan]") -> str:
    """PRD §38 UX Rule 4: 'ESC should return where supported'.
    Console berbasis line-input (Rich) tidak bisa menangkap tombol ESC mentah
    tanpa library tambahan (msvcrt/readchar) yang mengubah cara render seluruh
    TUI. Sebagai gantinya, Ctrl+C dipetakan ke '0' (BACK) - karena SEMUA menu
    sudah punya cabang `elif c == "0": return`, Ctrl+C otomatis berarti
    'kembali ke menu sebelumnya', bukan keluar paksa dari seluruh aplikasi
    seperti Python default (KeyboardInterrupt traceback).

    Normalisasi angka: menu selalu MENAMPILKAN "[00] BACK/EXIT" (sesuai PRD),
    tapi cabang kode di setiap modul mengecek `c == "0"` (satu digit). Kalau
    user mengetik persis apa yang tertulis di layar ("00"), itu tidak pernah
    cocok -> selalu jatuh ke "Invalid option". Sama juga untuk item bernomor
    satu digit lain, mis. "01" untuk memilih [01]. Di sini input numerik
    dengan leading zero diratakan dulu ("00" -> "0", "01" -> "1", "007" -> "7")
    supaya "0" DAN "00" (begitu juga "1" DAN "01", dst) sama-sama valid,
    tanpa perlu ubah tampilan menu satu per satu di 15 modul."""
    try:
        raw = console.input(prompt).strip()
    except KeyboardInterrupt:
        console.print()
        return "0"
    if raw.isdigit():
        return str(int(raw))
    return raw


def ask(prompt: str) -> str:
    try:
        return console.input(f"{prompt}: ").strip()
    except KeyboardInterrupt:
        console.print()
        return ""


def ask_validated(prompt: str, validator, max_attempts: int = 3):
    """PRD §41 DoD: 'Input tervalidasi'. Minta input, validasi, ulang kalau salah
    (maks `max_attempts` kali), tampilkan pesan error yang jelas ke teknisi.
    Return None kalau user gagal terus setelah max_attempts (caller harus cek None)."""
    from .validate import ValidationError
    for attempt in range(max_attempts):
        raw = console.input(f"{prompt}: ").strip()
        try:
            return validator(raw)
        except ValidationError as e:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                console.print(f"[red]{e}[/red] [dim]({remaining} percobaan lagi)[/dim]")
            else:
                console.print(f"[red]{e}[/red]")
    console.print("[red]Terlalu banyak input tidak valid, dibatalkan.[/red]")
    return None


# ------------------------------------------------------------ Main Menu Box --
# Sesuai PRD §3.1 & §5: double-line box + status bar bawah, HANYA di Main Menu.
# Warna border/aksen ikut theme aktif (Settings > Theme), lihat core/theme.py.

def _box_top(width=BOX_WIDTH, style="white"):
    return f"[{style}]" + "\u2554" + "\u2550" * (width - 2) + "\u2557" + f"[/{style}]"


def _box_mid(width=BOX_WIDTH, style="white"):
    return f"[{style}]" + "\u2560" + "\u2550" * (width - 2) + "\u2563" + f"[/{style}]"


def _box_bottom(width=BOX_WIDTH, style="white"):
    return f"[{style}]" + "\u255a" + "\u2550" * (width - 2) + "\u255d" + f"[/{style}]"


def _box_line(segments, width=BOX_WIDTH, center=False, border_style="white"):
    """segments: string biasa, atau list of (text, style) tuple untuk multi-warna."""
    text = Text()
    if isinstance(segments, str):
        text.append(segments)
    else:
        for seg in segments:
            if isinstance(seg, tuple):
                text.append(seg[0], style=seg[1])
            else:
                text.append(str(seg))

    inner_width = width - 4
    plain_len = len(text.plain)
    if plain_len > inner_width:
        text.truncate(inner_width)
        plain_len = inner_width

    if center:
        left_pad = (inner_width - plain_len) // 2
        right_pad = inner_width - plain_len - left_pad
    else:
        left_pad, right_pad = 0, inner_width - plain_len

    line = Text("\u2551 ", style=border_style)
    line.append(" " * left_pad)
    line.append(text)
    line.append(" " * right_pad)
    line.append(" \u2551", style=border_style)
    return line


def get_status_bar_segments():
    """Cek cepat untuk status bar bawah (PRD: NETWORK/RPC/SMB/SPOOLER/INTERNET).
    Dipanggil hanya saat Main Menu render (bukan tiap submenu) supaya tidak lambat.
    """
    segments = []
    try:
        from ..network.advanced import check_adapter
        adapters = check_adapter()
        net_ok = any(a.state == "PASS" for a in adapters)
    except Exception:
        net_ok = False
    segments.append(("NETWORK", net_ok))

    try:
        from ..sharing.diagnostics import check_service_state
        rpc = check_service_state("RpcSs", "RPC")
        segments.append(("RPC", rpc.state == "PASS"))
    except Exception:
        segments.append(("RPC", False))

    try:
        from ..sharing.diagnostics import check_service_state
        smb = check_service_state("LanmanServer", "SMB")
        segments.append(("SMB", smb.state == "PASS"))
    except Exception:
        segments.append(("SMB", False))

    try:
        from ..sharing.diagnostics import check_service_state
        spl = check_service_state("Spooler", "SPOOLER")
        segments.append(("SPOOLER", spl.state == "PASS"))
    except Exception:
        segments.append(("SPOOLER", False))

    try:
        from ..network.basic import ping_internet
        inet = ping_internet()
        segments.append(("INTERNET", inet.state == "PASS"))
    except Exception:
        segments.append(("INTERNET", False))

    return segments


def render_main_menu_box(menu_rows: list):
    """
    menu_rows: list of tuple (col1_text, col2_text, col3_text) untuk baris menu.
    Menggambar box PERSIS sesuai PRD §5, dengan warna aksen mengikuti theme
    aktif (Settings > Theme) dan info live (jam) supaya terasa seperti
    dashboard, bukan layar statis.
    """
    clear_screen()
    theme = get_theme()
    border = theme["border"]
    accent = theme["accent"]

    console.print(_box_top(style=border))
    console.print(_box_line([(APP_NAME, accent)], center=True, border_style=border))
    clock = datetime.now().strftime("%a, %d %b %Y  %H:%M:%S")
    console.print(_box_line([(f"v{VERSION}", "dim"), (f"   \u2022   {clock}", "dim")], center=True, border_style=border))
    console.print(_box_mid(style=border))
    console.print(_box_line("", border_style=border))
    for c1, c2, c3 in menu_rows:
        row = [
            (f"{c1:<22}", accent if c1 else "white"),
            (f"{c2:<22}", accent if c2 else "white"),
            (c3, accent if c3 else "white"),
        ]
        console.print(_box_line(row, border_style=border))
    console.print(_box_line("", border_style=border))
    console.print(_box_line([("[00] EXIT", "bold white")], border_style=border))
    console.print(_box_mid(style=border))

    status_segments = get_status_bar_segments()
    bar = []
    for label, ok in status_segments:
        dot = "\u25cf" if ok else "\u25cb"
        style = "green" if ok else "red"
        bar.append((f"{dot} {label}  ", style))
    console.print(_box_line(bar, border_style=border))
    console.print(_box_bottom(style=border))

