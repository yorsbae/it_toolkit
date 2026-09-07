"""
Folder Share (PRD §21)
---------------------------
Target format: \\\\SERVER\\ShareName
"""

import re
from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..network.basic import ping_target
from ..network.advanced import check_port


def _parse_unc(unc: str):
    m = re.match(r"\\\\([^\\]+)\\(.+)", unc)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def list_shared_folders(target: str) -> CheckResult:
    result = run_command(f"net view \\\\{target}", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Shared Folders on {target}", state, detail=result["message"][:500] or result["details"])


def test_share(unc: str) -> list:
    server, share = _parse_unc(unc)
    if not server:
        return [CheckResult("Test Share", "FAIL", detail="Format harus \\\\SERVER\\ShareName")]
    results = [ping_target(server), check_port(server, 445)]
    exists = run_command(f'if exist "{unc}" echo FOUND', timeout=10)
    found = "FOUND" in exists["message"]
    state = "PASS" if found else "FAIL"
    rec = "" if found else "Share tidak ditemukan / tidak bisa diakses, cek nama share dan permission."
    results.append(CheckResult(f"Share Exists: {unc}", state, recommendation=rec))
    return results


def test_share_permission(unc: str) -> CheckResult:
    server, share = _parse_unc(unc)
    result = run_command(
        f'powershell -NoProfile -Command "Get-SmbShareAccess -CimSession \'{server}\' -Name \'{share}\'"',
        timeout=15,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Share Permission {unc}", state, detail=result["message"][:400] or result["details"][:300])


def test_ntfs_permission(local_path: str) -> CheckResult:
    result = run_command(f'icacls "{local_path}"', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"NTFS Permission {local_path}", state, detail=result["message"][:400] or result["details"])


_PERM_RANK = {
    "full": 3, "fullcontrol": 3, "change": 2, "modify": 2, "write": 2,
    "read": 1, "readandexecute": 1, "listfolder": 1,
}

# icacls Windows umumnya keluar sebagai singkatan dalam kurung, mis. "(F)", "(M)", "(RX)".
_ICACLS_ABBR_RANK = {
    "F": 3,   # Full control
    "M": 2,   # Modify
    "W": 2,   # Write
    "RX": 1,  # Read & Execute
    "R": 1,   # Read
}


def _extract_perm_level(text: str) -> tuple:
    """Cari level permission tertinggi dari output PowerShell (kata penuh: Full/Change/Read)
    ATAU output icacls (singkatan dalam kurung: (F)/(M)/(RX)/(R)/(W)).
    Kembalikan (level_name, rank), atau (None, -1) kalau tidak ketemu sama sekali."""
    import re

    text_lower = text.lower()
    best_name, best_rank = None, -1

    # 1) Coba match kata penuh (output PowerShell Get-SmbShareAccess dsb) - pakai word boundary
    #    supaya "full" tidak salah cocok di dalam kata seperti "successfully".
    for name, rank in _PERM_RANK.items():
        if re.search(r"\b" + name + r"\b", text_lower) and rank > best_rank:
            best_name, best_rank = name, rank

    # 2) Coba match singkatan icacls dalam kurung, mis. "(OI)(CI)(F)" atau ":(M)"
    abbr_matches = re.findall(r"\(([A-Z]{1,2})\)", text)
    for abbr in abbr_matches:
        rank = _ICACLS_ABBR_RANK.get(abbr)
        if rank and rank > best_rank:
            best_name = {3: "full", 2: "modify", 1: "read"}[rank]
            best_rank = rank

    return best_name, best_rank


def test_effective_permission(unc: str, user_or_group: str = "Everyone") -> CheckResult:
    """
    Effective Permission = irisan (yang PALING RESTRIKTIF) antara Share Permission
    dan NTFS Permission (PRD: 'Windows memakai permission paling ketat antara
    Share permission dan NTFS permission').

    Catatan: parsing di sini berbasis keyword matching pada output PowerShell/icacls
    (Full/Change/Modify/Read) - cukup untuk kasus umum satu user/group, tapi tidak
    menggantikan audit ACL penuh untuk skenario permission bertingkat/nested group.
    """
    server, share = _parse_unc(unc)
    if not server:
        return CheckResult(f"Effective Permission {unc}", "FAIL", detail="Format harus \\\\SERVER\\ShareName")

    share_perm = test_share_permission(unc)
    ntfs_result = run_command(f'icacls "{unc}"', timeout=15)
    ntfs_text = ntfs_result["message"] if ntfs_result["status"] == "success" else ntfs_result["details"]

    share_name, share_rank = _extract_perm_level(share_perm.detail)
    ntfs_name, ntfs_rank = _extract_perm_level(ntfs_text)

    if share_rank == -1 or ntfs_rank == -1:
        return CheckResult(
            f"Effective Permission {unc}", "UNKNOWN",
            detail=f"Share: {share_perm.detail[:150]} | NTFS: {ntfs_text[:150]}",
            recommendation="Tidak bisa parse level permission otomatis (kemungkinan format ACL non-standar). Cek manual dengan Get-SmbShareAccess dan icacls.",
        )

    if share_rank <= ntfs_rank:
        effective, source = share_name, "Share"
    else:
        effective, source = ntfs_name, "NTFS"

    state = "PASS" if effective in ("full", "fullcontrol", "change", "modify", "write") else "WARN"
    return CheckResult(
        f"Effective Permission {unc} ({user_or_group})", state,
        detail=f"Share={share_name or '?'}, NTFS={ntfs_name or '?'} -> Effective={effective} (dibatasi oleh {source})",
        recommendation="" if state == "PASS" else "Effective permission cuma Read - user mungkin tidak bisa menulis walau salah satu sisi (Share/NTFS) mengizinkan Full.",
    )


def map_network_drive(drive_letter: str, unc: str, persistent: bool = True) -> CheckResult:
    flag = "/persistent:yes" if persistent else "/persistent:no"
    result = run_command(f'net use {drive_letter}: "{unc}" {flag}', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "Cek kredensial, share exists, dan permission."
    return CheckResult(f"Map {drive_letter}: -> {unc}", state, detail=result["message"] or result["details"], recommendation=rec)


def disconnect_network_drive(drive_letter: str) -> CheckResult:
    result = run_command(f'net use {drive_letter}: /delete /y', timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Disconnect {drive_letter}:", state, detail=result["message"] or result["details"])


def open_folder(unc: str) -> CheckResult:
    import subprocess
    try:
        subprocess.Popen(f'explorer "{unc}"', shell=True)
        return CheckResult(f"Open {unc}", "PASS", detail="Explorer dibuka")
    except Exception as e:
        return CheckResult(f"Open {unc}", "FAIL", detail=str(e))


def diagnose_access_denied(unc: str) -> list:
    server, share = _parse_unc(unc)
    results = [ping_target(server), check_port(server, 445)]
    results.append(test_share_permission(unc))
    results.append(CheckResult("Guest/Anonymous Access", "INFO",
                                detail="Cek juga Sharing > Windows Configuration > SMB Guest Access bila user tidak pakai kredensial domain."))
    return results


def diagnose_unavailable_share(unc: str) -> list:
    server, share = _parse_unc(unc)
    results = [ping_target(server), check_port(server, 445), check_port(server, 139)]
    results.append(CheckResult("Server Service", "INFO", detail="Cek Sharing > Services > Server (LanmanServer) berjalan di target."))
    return results


def folder_share_full_check(unc: str) -> list:
    server, _ = _parse_unc(unc)
    if not server:
        return [CheckResult("Folder Share", "FAIL", detail="Format harus \\\\SERVER\\ShareName")]
    results = [ping_target(server)]
    results.append(check_port(server, 445))
    results.append(check_port(server, 135))
    results += test_share(unc)[-1:]
    results.append(test_share_permission(unc))
    results.append(test_effective_permission(unc))
    return results
