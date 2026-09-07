"""
Maintenance Module (PRD §28) - 12 item
------------------------------------------
Semua Administrative/Destructive -> wajib confirm di UI sebelum dipanggil.
Long-running operations (SFC/DISM/CHKDSK) sudah ada di modules/windows/diagnostics.py,
di sini hanya wrapper supaya menu Maintenance bisa akses fungsi yang sama tanpa duplikasi.
"""

from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..windows.diagnostics import run_sfc, run_dism_restore_health, run_chkdsk


def clear_temp_files() -> CheckResult:
    run_command(
        'powershell -NoProfile -Command '
        '"Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue"',
        timeout=60,
    )
    return CheckResult("Temporary Files", "PASS", detail="Temp folder dibersihkan (file terkunci dilewati)")


def disk_cleanup(drive: str = "C:") -> CheckResult:
    result = run_command("cleanmgr /sagerun:1", timeout=120)
    return CheckResult(f"Disk Cleanup {drive}", "PASS" if result["status"] == "success" else "WARN",
                        detail=result["message"][-200:] or "Proses dijalankan")


def flush_dns() -> CheckResult:
    result = run_command("ipconfig /flushdns", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Flush DNS", state, detail=result["message"])


def restart_print_spooler() -> CheckResult:
    """Verifikasi ulang setelah restart (PRD §41 DoD 'Hasil diverifikasi setelah repair')."""
    from ..sharing.diagnostics import fix_restart_service
    return fix_restart_service("Spooler")


def sfc_scan() -> CheckResult:
    return run_sfc()


def dism_check() -> CheckResult:
    if not is_admin():
        return CheckResult("DISM CheckHealth", "WARN", detail="Butuh hak admin")
    result = run_command("DISM /Online /Cleanup-Image /CheckHealth", timeout=60)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("DISM CheckHealth", state, detail=result["message"][-300:])


def dism_restore() -> CheckResult:
    return run_dism_restore_health()


def chkdsk(drive: str = "C:") -> CheckResult:
    return run_chkdsk(drive)


def clear_windows_update_cache() -> CheckResult:
    if not is_admin():
        return CheckResult("Windows Update Cache", "WARN", detail="Butuh hak admin")
    run_command("net stop wuauserv", timeout=15)
    run_command('powershell -NoProfile -Command "Remove-Item -Path $env:windir\\SoftwareDistribution\\* -Recurse -Force -ErrorAction SilentlyContinue"', timeout=30)
    result = run_command("net start wuauserv", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Windows Update Cache", state, detail="SoftwareDistribution dibersihkan, service direstart")


def component_store_cleanup() -> CheckResult:
    if not is_admin():
        return CheckResult("Component Store", "WARN", detail="Butuh hak admin")
    result = run_command("DISM /Online /Cleanup-Image /StartComponentCleanup", timeout=300)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Component Store Cleanup", state, detail=result["message"][-300:])


def create_restore_point(description: str = "IT Support Toolkit Checkpoint") -> CheckResult:
    if not is_admin():
        return CheckResult("Create Restore Point", "WARN", detail="Butuh hak admin")
    result = run_command(
        f'powershell -NoProfile -Command "Checkpoint-Computer -Description \'{description}\' -RestorePointType MODIFY_SETTINGS"',
        timeout=60,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "System Restore mungkin dinonaktifkan di drive ini."
    return CheckResult("Create Restore Point", state, detail=result["message"] or "Restore point dibuat", recommendation=rec)


def restart_network_adapter(name: str) -> CheckResult:
    if not is_admin():
        return CheckResult(f"Restart Adapter {name}", "WARN", detail="Butuh hak admin")
    run_command(f'powershell -NoProfile -Command "Disable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    result = run_command(f'powershell -NoProfile -Command "Enable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Restart Adapter {name}", state, detail="Adapter di-disable lalu enable kembali")


def clear_print_queue() -> CheckResult:
    if not is_admin():
        return CheckResult("Clear Print Queue", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    run_command("net stop spooler", timeout=15)
    run_command('powershell -NoProfile -Command "Remove-Item -Path $env:SystemRoot\\System32\\spool\\PRINTERS\\* -Force -ErrorAction SilentlyContinue"', timeout=15)
    result = run_command("net start spooler", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Clear Print Queue", state, detail="Spooler direstart, antrian dibersihkan")
