"""
Status System
-------------
Simbol unicode [✓][ ][!][?][-] kadang tidak render rapi di cmd.exe lama
(code page default). Karena itu tersedia mode ASCII fallback otomatis.
"""

import sys

USE_UNICODE = sys.stdout.encoding and "UTF" in sys.stdout.encoding.upper()

SYMBOLS_UNICODE = {
    "PASS": "[\u2713]",   # [✓]
    "FAIL": "[ ]",
    "WARN": "[!]",
    "UNKNOWN": "[?]",
    "SKIP": "[-]",
    "INFO": "[*]",
}

SYMBOLS_ASCII = {
    "PASS": "[OK]",
    "FAIL": "[XX]",
    "WARN": "[!!]",
    "UNKNOWN": "[??]",
    "SKIP": "[--]",
    "INFO": "[**]",
}

COLORS = {
    "PASS": "green",
    "FAIL": "red",
    "WARN": "yellow",
    "UNKNOWN": "cyan",
    "SKIP": "grey58",
    "INFO": "cyan",
}


def symbol(state: str) -> str:
    table = SYMBOLS_UNICODE if USE_UNICODE else SYMBOLS_ASCII
    return table.get(state, table["UNKNOWN"])


def color(state: str) -> str:
    return COLORS.get(state, "white")


def render_line(label: str, state: str) -> str:
    """Mengembalikan string berwarna (Rich markup) siap print, mis:
    [green][OK] Gateway[/green]
    """
    return f"[{color(state)}]{symbol(state)} {label}[/{color(state)}]"


class CheckResult:
    """Hasil satu pemeriksaan tunggal — dasar untuk semua module."""

    def __init__(self, label: str, state: str, detail: str = "", recommendation: str = ""):
        self.label = label
        self.state = state          # PASS / FAIL / WARN / UNKNOWN / SKIP / INFO
        self.detail = detail
        self.recommendation = recommendation

    def to_dict(self):
        return {
            "label": self.label,
            "state": self.state,
            "detail": self.detail,
            "recommendation": self.recommendation,
        }
