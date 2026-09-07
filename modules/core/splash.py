"""
Ghost Toolbox style splash screen.
Ditampilkan sekali saat aplikasi start, sebelum masuk ke main menu.
"""

import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from .config import load_config
from .executor import is_admin
from .screen import clear_screen
from .theme import get_theme

console = Console()
_cfg = load_config()
APP_NAME = _cfg.get("app_name", "IT SUPPORT TOOLKIT")
VERSION = _cfg.get("version", "1.0.0")

GHOST_ART = r"""
[{accent}]           ___
          /   \
         | o o |
         |  ^  |
         | \_/ |
        /|     |\
       / |     | \
      |  |     |  |
       \_|_____|_/
        V  V V  V[/{accent}]
"""

BANNER = r"""
[{accent}] ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
██║  ███╗███████║██║   ██║███████╗   ██║
██║   ██║██╔══██║██║   ██║╚════██║   ██║
╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝[/{accent}]
[bold white]           I T   T O O L B O X[/bold white]
"""

_LOAD_STEPS = [
    "Menyiapkan modul diagnostik...",
    "Memuat konfigurasi...",
    "Mengecek koneksi jaringan...",
    "Menyiapkan menu utama...",
]


def show_splash(skip: bool = False):
    if skip:
        return
    clear_screen()
    theme = get_theme()
    console.print(GHOST_ART.format(accent=theme["accent"]))
    console.print(BANNER.format(accent=theme["accent"]))
    admin_tag = "[green]ADMIN[/green]" if is_admin() else "[yellow]USER (jalankan sebagai Administrator untuk fitur penuh)[/yellow]"
    console.print(f"[dim]{APP_NAME}  v{VERSION}[/dim]  |  {admin_tag}\n")

    with Progress(
        TextColumn("[dim]{task.fields[step]}[/dim]"),
        BarColumn(bar_width=40, style=theme["rule"], complete_style=theme["accent"]),
        TextColumn("{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("loading", total=len(_LOAD_STEPS), step=_LOAD_STEPS[0])
        for step in _LOAD_STEPS:
            progress.update(task, step=step)
            time.sleep(0.15)
            progress.advance(task)
