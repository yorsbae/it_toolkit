"""
Printer Share (PRD §22)
----------------------------
Target format: \\\\SERVER\\PrinterName
"""

import re
from ..core.executor import run_command
from ..core.status import CheckResult
from ..network.basic import ping_target
from ..network.advanced import check_port


def _parse_unc(unc: str):
    m = re.match(r"\\\\([^\\]+)\\(.+)", unc)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def list_shared_printers(server: str) -> CheckResult:
    result = run_command(f"net view \\\\{server} /print", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Shared Printers on {server}", state, detail=result["message"][:500] or result["details"])


def test_printer_share(unc: str) -> list:
    server, name = _parse_unc(unc)
    if not server:
        return [CheckResult("Test Printer Share", "FAIL", detail="Format harus \\\\SERVER\\PrinterName")]
    return [ping_target(server), check_port(server, 445), check_port(server, 135)]


def connect_shared_printer(unc: str) -> CheckResult:
    result = run_command(f'rundll32 printui.dll,PrintUIEntry /in /n "{unc}"', timeout=20)
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "Cek driver client kompatibel, dan Point & Print Policy."
    return CheckResult(f"Connect Printer {unc}", state, detail=result["message"] or "Printer connection requested", recommendation=rec)


def test_printer_port(server: str, port: int = 9100) -> CheckResult:
    return check_port(server, port)


def check_spooler_running(server: str = None) -> CheckResult:
    cmd = f"sc \\\\{server} query Spooler" if server else "sc query Spooler"
    result = run_command(cmd, timeout=15)
    running = result["status"] == "success" and "RUNNING" in result["message"]
    state = "PASS" if running else "FAIL"
    return CheckResult(f"Spooler {'@ ' + server if server else ''}".strip(), state,
                        detail="Running" if running else "Stopped/Unreachable")


def diagnose_rpc(server: str) -> CheckResult:
    r = check_port(server, 135)
    r.label = f"RPC (Printer Share) {server}"
    if r.state != "PASS":
        r.recommendation = "Error 0x0000011B biasanya terkait RPC - cek Sharing > Registry/Policy > RPC Configuration."
    return r


def diagnose_point_and_print(server: str) -> CheckResult:
    from .diagnostics import check_point_and_print_policy
    return check_point_and_print_policy()


def check_driver_store() -> CheckResult:
    result = run_command('pnputil /enum-drivers', timeout=20)
    state = "PASS" if result["status"] == "success" else "FAIL"
    count = result["message"].count("Published Name")
    return CheckResult("Driver Store / Package", state, detail=f"{count} driver package(s) terdaftar")


def printer_share_full_check(unc: str) -> list:
    server, name = _parse_unc(unc)
    if not server:
        return [CheckResult("Printer Share", "FAIL", detail="Format harus \\\\SERVER\\PrinterName")]
    results = [ping_target(server)]
    results.append(check_port(server, 445))
    results.append(diagnose_rpc(server))
    results.append(check_spooler_running(server))
    results.append(diagnose_point_and_print(server))
    results.append(check_driver_store())
    return results


def printer_share_full_check_with_permission(unc: str, printer_local_name: str = None) -> list:
    results = printer_share_full_check(unc)
    if printer_local_name:
        results.append(check_printer_permission(printer_local_name))
    return results


def check_printer_permission(printer_name: str, user_or_group: str = "Everyone") -> CheckResult:
    """PRD: Printer Permission (Print/Manage) di level printer object - beda dari share/NTFS folder."""
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"(Get-Printer -Name \'{printer_name}\' -Full).PermissionSDDL"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" and result["message"].strip() else "UNKNOWN"
    detail = result["message"].strip()[:200] or "Tidak bisa membaca SDDL (butuh admin atau printer tidak ditemukan)"
    return CheckResult(f"Printer Permission {printer_name}", state, detail=detail,
                        recommendation="" if state == "PASS" else "Cek printer Properties > Security tab secara manual di server.")
