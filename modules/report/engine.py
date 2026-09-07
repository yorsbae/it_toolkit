"""
Report Module (PRD §31) - 10 item
------------------------------------
Menggabungkan hasil dari module lain jadi laporan per-kategori atau Full Diagnostic.
"""

from ..core.report import generate_report
from ..core.status import CheckResult
from ..core.config import REPORTS_DIR


def system_report() -> tuple:
    from ..windows.diagnostics import get_system_info
    from ..hardware.info import get_cpu_info, get_ram_info, get_disk_info
    results = [get_cpu_info(), get_ram_info()] + get_disk_info()
    return generate_report("SYSTEM", results)


def network_report(target: str) -> tuple:
    from ..network.advanced import full_osi_diagnostic
    results = full_osi_diagnostic(target)
    return generate_report("NETWORK", results)


def printer_report() -> tuple:
    from ..printer.diagnostics import list_printers, check_printer, diagnose_all_configured_printers
    printers = list_printers()
    results = []
    for p in printers:
        results.append(check_printer(p["name"]))
    configured = diagnose_all_configured_printers()
    if configured:
        results.append(CheckResult("--- CONFIGURED PRINTERS (config/printers.json) ---", "INFO"))
        results += configured
    if not results:
        results = [CheckResult("Printer Report", "UNKNOWN", detail="Tidak ada printer terdeteksi")]
    return generate_report("PRINTER", results)


def server_report() -> tuple:
    from ..server.diagnostics import diagnose_all_servers
    results = diagnose_all_servers()
    if not results:
        results = [CheckResult("Server Report", "UNKNOWN", detail="Belum ada server di config/servers.json")]
    return generate_report("SERVER", results)


def cctv_report() -> tuple:
    from ..cctv.diagnostics import camera_status
    results = camera_status()
    return generate_report("CCTV", results)


def hardware_report() -> tuple:
    from ..hardware.info import (get_cpu_info, get_ram_info, get_disk_info,
                                  get_gpu_info, get_motherboard_info, get_bios_info)
    results = [get_cpu_info(), get_ram_info(), get_gpu_info(), get_motherboard_info(), get_bios_info()]
    results += get_disk_info()
    return generate_report("HARDWARE", results)


def sharing_report() -> tuple:
    from ..sharing.diagnostics import full_diagnostic_extended
    results = full_diagnostic_extended()
    return generate_report("SHARING", results)


def full_diagnostic() -> tuple:
    """Gabungan semua module - PRD §31 item 08."""
    results = [CheckResult("=== SYSTEM ===", "INFO")]
    from ..hardware.info import get_cpu_info, get_ram_info, get_disk_info
    results += [get_cpu_info(), get_ram_info()] + get_disk_info()

    results.append(CheckResult("=== NETWORK ===", "INFO"))
    from ..network.basic import ping_internet
    from ..network.advanced import default_route
    results += [default_route(), ping_internet()]

    results.append(CheckResult("=== SHARING ===", "INFO"))
    from ..sharing.diagnostics import full_sharing_diagnostic
    results += full_sharing_diagnostic()

    results.append(CheckResult("=== SECURITY ===", "INFO"))
    from ..security.diagnostics import check_defender_status
    results.append(check_defender_status())

    return generate_report("FULL_DIAGNOSTIC", results)


def view_reports(limit: int = 20) -> list:
    files = sorted(REPORTS_DIR.glob("*.txt"), reverse=True)
    return files[:limit]


def export_report(report_path, dest_path: str) -> CheckResult:
    import shutil
    try:
        shutil.copy(report_path, dest_path)
        return CheckResult("Export Report", "PASS", detail=f"Copied to {dest_path}")
    except Exception as e:
        return CheckResult("Export Report", "FAIL", detail=str(e))
