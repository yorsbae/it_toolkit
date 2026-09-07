"""
Security Diagnostics
------------------------
Bukan vulnerability scanner (PRD Non-Goals) - hanya status dasar.
"""

from ..core.executor import run_command
from ..core.status import CheckResult


def check_firewall_status() -> list:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-NetFirewallProfile | Select-Object Name,Enabled | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    results = []
    if result["status"] != "success":
        return [CheckResult("Firewall Status", "FAIL", detail=result["details"])]
    for line in result["message"].splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        profile, enabled = parts[0], parts[1]
        state = "PASS" if enabled.lower() == "true" else "WARN"
        rec = "" if state == "PASS" else f"Aktifkan Windows Firewall untuk profile {profile}."
        results.append(CheckResult(f"Firewall ({profile})", state, detail=enabled, recommendation=rec))
    return results


def check_defender_status() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"(Get-MpComputerStatus).RealTimeProtectionEnabled"',
        timeout=10,
    )
    val = result["message"].strip().lower()
    state = "PASS" if val == "true" else "WARN"
    rec = "" if state == "PASS" else "Real-time protection Windows Defender tidak aktif."
    return CheckResult("Defender Real-Time Protection", state, detail=val or "unknown", recommendation=rec)


# ---- Item tambahan PRD Security Module (9 item total) ----

from ..core.ps import ps_info
from ..core.executor import run_command


def get_open_ports() -> CheckResult:
    result = run_command("netstat -an | findstr LISTENING", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    lines = result["message"].splitlines()
    return CheckResult("Open Ports", state, detail=f"{len(lines)} port listening")


def get_logged_in_users() -> CheckResult:
    return ps_info("Logged-in Users", "query user")


def get_local_administrators() -> CheckResult:
    return ps_info("Local Administrators", "Get-LocalGroupMember -Group Administrators | Select-Object Name | Format-Table -HideTableHeaders")


def get_security_policy() -> CheckResult:
    result = run_command("secedit /export /cfg %TEMP%\\secpol.cfg && type %TEMP%\\secpol.cfg", timeout=20)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Security Policy", state, detail=result["message"][:500] or result["details"])


def get_windows_update_status() -> CheckResult:
    return ps_info(
        "Windows Update Status",
        "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID,InstalledOn | Format-Table -HideTableHeaders",
    )


def get_bitlocker_status() -> CheckResult:
    result = run_command('manage-bde -status C:', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    protection_on = "Protection On" in result["message"]
    rec = "" if protection_on else "BitLocker tidak aktif di drive C:, pertimbangkan enkripsi untuk data sensitif."
    return CheckResult("BitLocker Status", "PASS" if protection_on else "WARN",
                        detail=result["message"][:300] or result["details"], recommendation=rec)


def system_security_report() -> list:
    return [
        check_defender_status(),
        get_open_ports(),
        get_local_administrators(),
        get_bitlocker_status(),
    ] + check_firewall_status()
