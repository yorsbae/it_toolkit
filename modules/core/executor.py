"""
Command Executor
-----------------
Semua pemanggilan command Windows (ping, ipconfig, powershell, dll)
HARUS lewat sini agar:
1. Tidak pernah membuat aplikasi crash walau exit code != 0.
2. Selalu mengembalikan hasil terstruktur (lihat PRD section 37).
3. Bisa diberi timeout supaya TUI tidak hang.
"""

import subprocess
from datetime import datetime


def run_command(command: str, timeout: int = 15, shell: bool = True):
    """
    Menjalankan command dan mengembalikan dict terstruktur:
    {status, code, message, details, target, timestamp}
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    try:
        proc = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = proc.returncode == 0
        return {
            "status": "success" if success else "failed",
            "code": proc.returncode,
            "message": proc.stdout.strip() or proc.stderr.strip(),
            "details": proc.stderr.strip(),
            "target": command,
            "timestamp": timestamp,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "code": -1,
            "message": "Command timeout",
            "details": f"No response after {timeout}s",
            "target": command,
            "timestamp": timestamp,
        }
    except Exception as e:  # noqa: BLE001 - executor wajib tidak pernah melempar exception
        return {
            "status": "failed",
            "code": -2,
            "message": "Execution error",
            "details": str(e),
            "target": command,
            "timestamp": timestamp,
        }


def is_admin() -> bool:
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
