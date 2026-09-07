"""
Sharing Error Code Troubleshooter (PRD §23)
------------------------------------------------
Prinsip PRD: kode error TIDAK otomatis dipetakan ke satu penyebab tunggal.
Tool menampilkan kategori + checklist kemungkinan, lalu opsi aksi manual.

Daftar error code dibaca dari config/sharing/errors.json (DoD PRD §41:
tidak ada hardcoded target yang tidak bisa dikonfigurasi) - bisa ditambah
tanpa ubah source code.
"""

from ..core.status import CheckResult
from ..core.config import load_json
from .diagnostics import (
    check_service_state, check_firewall_rule_group, check_rpc_configuration,
    fix_restart_service, SERVICES,
)
from .folder import diagnose_access_denied

_DEFAULT_ERROR_CODES = {
    "0x0000011B": {"category": "Printer Sharing / RPC", "description": "Windows cannot connect to the printer - biasanya masalah RPC atau Point & Print policy."},
    "0x00000709": {"category": "Printer Connection", "description": "Gagal set default printer / koneksi printer, sering terkait driver atau spooler."},
    "0x00000040": {"category": "Network Path", "description": "The specified network name is no longer available - server down atau SMB terputus."},
    "0x00000057": {"category": "Parameter Error", "description": "The parameter is incorrect - biasanya path/nama share salah atau driver tidak cocok."},
    "0x00000002": {"category": "File Not Found", "description": "System cannot find the file specified - share/printer tidak ada atau driver hilang."},
    "0x00000035": {"category": "Network Path Not Found", "description": "Server tidak reachable, DNS gagal resolve, atau server mati."},
    "0x00000005": {"category": "Access Denied", "description": "Permission ditolak - cek share/NTFS/printer permission dan kredensial."},
    "RPC_ERROR": {"category": "RPC", "description": "RPC server unavailable - cek service RPC, firewall, dan RPC Configuration registry."},
    "ACCESS_DENIED": {"category": "Authentication", "description": "Kredensial ditolak - cek permission, guest access, dan credential manager."},
    "UNKNOWN": {"category": "Unknown", "description": "Error tidak dikenali - jalankan Full Diagnostic untuk melihat gambaran umum."},
}


def _load_error_codes() -> dict:
    data = load_json("sharing/errors.json", default=None)
    if data and data.get("error_codes"):
        return data["error_codes"]
    return _DEFAULT_ERROR_CODES


ERROR_CODES = _load_error_codes()


def list_error_codes() -> list:
    return list(ERROR_CODES.keys())


def diagnose_error_code(code: str, target: str = None) -> tuple:
    """Return (info_dict, list_of_CheckResult) - checklist kondisi terkini, BUKAN vonis penyebab tunggal."""
    info = ERROR_CODES.get(code, ERROR_CODES["UNKNOWN"])
    checks = []

    if target:
        from ..network.basic import ping_target
        from ..network.advanced import check_port
        checks.append(ping_target(target))
        checks.append(check_port(target, 445))

    checks.append(check_service_state("RpcSs", "RPC"))
    checks.append(check_firewall_rule_group())
    checks.append(check_rpc_configuration())

    return info, checks


def possible_actions_menu_labels() -> list:
    return [
        "Check Registry",
        "Apply Registry Configuration",
        "Restart Print Spooler",
        "Restart Server",
        "Retry Connection",
        "Full Diagnostic",
    ]
