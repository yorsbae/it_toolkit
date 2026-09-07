"""
Logger
------
Menulis log plain-text harian ke folder logs/, format konsisten
sesuai PRD section 36 (Logging).
"""

from datetime import datetime
from .config import LOGS_DIR


def _log_path():
    return LOGS_DIR / f"{datetime.now():%Y-%m-%d}.log"


def _normalize_result(result: str) -> str:
    """PRD §36 contoh log pakai kata 'SUCCESS'/'FAILED', bukan enum status PASS/FAIL/WARN.
    Fungsi ini menormalkan supaya semua caller (yang kirim CheckResult.state) otomatis benar."""
    mapping = {
        "PASS": "SUCCESS", "FAIL": "FAILED", "WARN": "WARNING",
        "SKIP": "SKIPPED", "UNKNOWN": "UNKNOWN", "INFO": "INFO",
    }
    return mapping.get(result.upper(), result.upper())


def log_action(module: str, action: str, target: str, result: str,
                user: str = "IT-SUPPORT", host: str = "", error: str = ""):
    import socket
    host = host or socket.gethostname()
    lines = [
        f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        f"USER       : {user}",
        f"HOST       : {host}",
        f"MODULE     : {module}",
        f"ACTION     : {action}",
        f"TARGET     : {target}",
        f"RESULT     : {_normalize_result(result)}",
    ]
    if error:
        lines.append(f"ERROR      : {error}")
    lines.append("-" * 40)

    with open(_log_path(), "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
