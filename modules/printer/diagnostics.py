"""
Printer Diagnostics
----------------------
"""

from ..core.executor import run_command
from ..core.status import CheckResult


def list_printers() -> list:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-Printer | Select-Object Name,PrinterStatus | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    printers = []
    if result["status"] != "success":
        return printers
    for line in result["message"].splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)
        if len(parts) == 2:
            printers.append({"name": parts[0], "status": parts[1]})
    return printers


def check_printer(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"(Get-Printer -Name \'{name}\').PrinterStatus"',
        timeout=10,
    )
    status = result["message"].strip()
    if result["status"] != "success" or not status:
        return CheckResult(f"Printer {name}", "FAIL", detail="Printer tidak ditemukan",
                            recommendation="Cek nama printer sudah benar / driver terpasang.")
    ok = status.lower() in ("normal", "idle")
    state = "PASS" if ok else "WARN"
    rec = "" if ok else "Cek antrian print, restart Print Spooler lewat menu Sharing."
    return CheckResult(f"Printer {name}", state, detail=status, recommendation=rec)


def check_print_queue(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"(Get-PrintJob -PrinterName \'{name}\' -ErrorAction SilentlyContinue).Count"',
        timeout=10,
    )
    try:
        count = int(result["message"].strip() or "0")
    except ValueError:
        count = 0
    state = "PASS" if count == 0 else "WARN"
    rec = "" if count == 0 else "Ada job macet di antrian, clear print queue lewat Maintenance."
    return CheckResult(f"Print Queue {name}", state, detail=f"{count} job in queue", recommendation=rec)


# ---- Item tambahan PRD Printer Module (15 item total) ----

from ..core.executor import is_admin


def get_default_printer() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command "(Get-CimInstance Win32_Printer | Where-Object Default -eq $true).Name"',
        timeout=10,
    )
    name = result["message"].strip()
    state = "PASS" if name else "UNKNOWN"
    return CheckResult("Default Printer", state, detail=name or "Tidak ada default printer")


def set_default_printer(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "(New-Object -ComObject WScript.Network).SetDefaultPrinter(\'{name}\')"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Set Default Printer -> {name}", state, detail=result["message"] or result["details"])


def print_test_page(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "Get-Printer -Name \'{name}\' | Out-Printer"',
        timeout=15,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "Cek printer online & driver terpasang benar."
    return CheckResult(f"Print Test Page {name}", state, detail=result["message"] or "Test page dikirim", recommendation=rec)


def add_printer_ip(name: str, ip: str, driver: str) -> CheckResult:
    if not is_admin():
        return CheckResult("Add Printer", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"Add-PrinterPort -Name \'{ip}_Port\' -PrinterHostAddress \'{ip}\'; '
        f'Add-Printer -Name \'{name}\' -DriverName \'{driver}\' -PortName \'{ip}_Port\'"',
        timeout=30,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Add Printer {name}", state, detail=result["message"] or result["details"])


def remove_printer(name: str) -> CheckResult:
    if not is_admin():
        return CheckResult("Remove Printer", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(f'powershell -NoProfile -Command "Remove-Printer -Name \'{name}\'"', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remove Printer {name}", state, detail=result["message"] or "Removed")


def printer_properties(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "Get-Printer -Name \'{name}\' -Full | Format-List"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Printer Properties {name}", state, detail=result["message"][:500])


def printer_ip_info(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"$p = Get-Printer -Name \'{name}\'; (Get-PrinterPort -Name $p.PortName).PrinterHostAddress"',
        timeout=10,
    )
    ip = result["message"].strip()
    state = "PASS" if ip else "UNKNOWN"
    return CheckResult(f"Printer IP {name}", state, detail=ip or "Tidak ditemukan (mungkin USB/local port)")


# ---- Konfigurasi printer eksternal dari config/printers.json (PRD §33) ----

def get_configured_printers() -> list:
    from ..core.config import load_json
    return load_json("printers.json", default={"printers": []}).get("printers", [])


def diagnose_configured_printer(entry: dict) -> list:
    """Cek printer yang terdaftar di config/printers.json (mis. network printer
    dengan IP tertentu yang belum tentu ter-install lokal)."""
    from ..network.basic import ping_target
    from ..network.advanced import check_port
    results = []
    if entry.get("ip"):
        results.append(ping_target(entry["ip"]))
        results.append(check_port(entry["ip"], 9100))  # port RAW printing standar
    if entry.get("name"):
        results.append(check_printer(entry["name"]))
    return results


def diagnose_all_configured_printers() -> list:
    entries = get_configured_printers()
    results = []
    for entry in entries:
        results.append(CheckResult(f"--- {entry.get('name', entry.get('ip'))} ---", "INFO"))
        results += diagnose_configured_printer(entry)
    return results


# ---- Item terlewat dari list persis PRD §16 (15 item) ----

def ping_printer(ip: str) -> CheckResult:
    from ..network.basic import ping_target
    r = ping_target(ip)
    r.label = f"Ping Printer {ip}"
    return r


def test_printer_port(ip: str, port: int = 9100) -> CheckResult:
    from ..network.advanced import check_port
    return check_port(ip, port)


def printer_diagnostics(name: str, ip: str = None) -> list:
    """PRD §16 item [11] Printer Diagnostics - gabungan check status+queue+spooler+ping."""
    results = [check_printer(name), check_print_queue(name), check_spooler_running_local()]
    if ip:
        results.append(ping_printer(ip))
        results.append(test_printer_port(ip))
    return results


def check_spooler_running_local() -> CheckResult:
    from ..core.executor import run_command
    result = run_command("sc query Spooler", timeout=10)
    running = result["status"] == "success" and "RUNNING" in result["message"]
    state = "PASS" if running else "FAIL"
    rec = "" if running else "Restart Print Spooler lewat menu Printer > Restart Print Spooler / menu Maintenance."
    return CheckResult("Print Spooler", state, detail="Running" if running else "Stopped", recommendation=rec)


def restart_print_spooler_local() -> CheckResult:
    """Verifikasi ulang setelah restart (PRD §41 DoD 'Hasil diverifikasi setelah repair')."""
    from ..sharing.diagnostics import fix_restart_service
    return fix_restart_service("Spooler")
