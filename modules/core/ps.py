"""
PowerShell Helper
---------------------
Mengurangi duplikasi kode untuk check info sederhana (GPU, BIOS, Battery, dll)
yang polanya sama: jalankan satu ekspresi PowerShell -> tampilkan hasilnya.
"""

from .executor import run_command
from .status import CheckResult


def run_ps(expression: str, timeout: int = 10):
    return run_command(f'powershell -NoProfile -Command "{expression}"', timeout=timeout)


def ps_info(label: str, expression: str, timeout: int = 10) -> CheckResult:
    """Untuk check yang sifatnya informational (bukan pass/fail biner)."""
    result = run_ps(expression, timeout=timeout)
    if result["status"] != "success" or not result["message"].strip():
        return CheckResult(label, "UNKNOWN", detail=result["details"] or "Tidak ada data")
    return CheckResult(label, "INFO", detail=result["message"].strip()[:400])


def ps_bool_check(label: str, expression: str, true_state="PASS", false_state="WARN",
                   recommendation_if_false: str = "", timeout: int = 10) -> CheckResult:
    """Untuk check yang hasilnya True/False dari PowerShell."""
    result = run_ps(expression, timeout=timeout)
    val = result["message"].strip().lower()
    if val == "true":
        return CheckResult(label, true_state, detail="True")
    elif val == "false":
        return CheckResult(label, false_state, detail="False", recommendation=recommendation_if_false)
    return CheckResult(label, "UNKNOWN", detail=result["details"] or "Tidak bisa dibaca")


def launch_app(label: str, command: str) -> CheckResult:
    """Untuk item Tools/Remote yang cuma membuka aplikasi bawaan Windows."""
    import subprocess
    try:
        subprocess.Popen(command, shell=True)
        return CheckResult(label, "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult(label, "FAIL", detail=str(e))


def is_app_installed(exe_or_path: str) -> bool:
    import shutil
    return shutil.which(exe_or_path) is not None
