"""
Theme System
==============
config.json sudah punya field "theme" sejak awal (Settings > [09] Theme),
tapi sebelum file ini ada, field itu cuma tersimpan tanpa efek visual apa
pun - ganti theme tidak mengubah tampilan sama sekali.

Sekarang header() dan render_main_menu_box() (dipanggil di SEMUA 17 modul)
membaca theme lewat get_theme() setiap kali render, bukan sekali saat start
- jadi ganti theme di Settings langsung terlihat di layar berikutnya, tanpa
perlu restart aplikasi.
"""

from .config import load_config

THEMES = {
    "cyan":    {"accent": "bold cyan",    "border": "cyan",    "rule": "cyan"},
    "green":   {"accent": "bold green",   "border": "green",   "rule": "green"},
    "blue":    {"accent": "bold blue",    "border": "blue",    "rule": "blue"},
    "magenta": {"accent": "bold magenta", "border": "magenta", "rule": "magenta"},
    "amber":   {"accent": "bold yellow",  "border": "yellow",  "rule": "yellow"},
    "red":     {"accent": "bold red",     "border": "red",     "rule": "red"},
}

DEFAULT_THEME = "cyan"


def available_themes() -> list:
    return list(THEMES.keys())


def get_theme_name() -> str:
    name = load_config().get("theme", DEFAULT_THEME)
    return name if name in THEMES else DEFAULT_THEME


def get_theme() -> dict:
    return THEMES[get_theme_name()]
