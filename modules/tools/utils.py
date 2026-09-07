"""
Tools Module (PRD §29) - 10 item
--------------------------------------
Launcher untuk utility bawaan Windows + tools jaringan ringan.
"""

import ipaddress
import subprocess
from ..core.status import CheckResult
from ..core.executor import run_command


def _launch(label: str, command: str) -> CheckResult:
    try:
        subprocess.Popen(command, shell=True)
        return CheckResult(label, "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult(label, "FAIL", detail=str(e))


def open_cmd() -> CheckResult:
    return _launch("CMD", "start cmd")


def open_powershell() -> CheckResult:
    return _launch("PowerShell", "start powershell")


def open_windows_terminal() -> CheckResult:
    return _launch("Windows Terminal", "wt")


def open_regedit() -> CheckResult:
    return _launch("Regedit", "regedit")


def open_msconfig() -> CheckResult:
    return _launch("MSConfig", "msconfig")


def open_system_configuration() -> CheckResult:
    return _launch("System Configuration", "control sysdm.cpl")


def open_disk_cleanup() -> CheckResult:
    return _launch("Disk Cleanup", "cleanmgr")


def open_character_map() -> CheckResult:
    return _launch("Character Map", "charmap")


def open_snipping_tool() -> CheckResult:
    return _launch("Snipping Tool", "snippingtool")


def open_calculator() -> CheckResult:
    return _launch("Calculator", "calc")


# ---- Network Tools tambahan (dipakai dari menu Network > [09] NETWORK TOOLS) ----

def subnet_calculator(ip_with_mask: str) -> CheckResult:
    try:
        net = ipaddress.ip_network(ip_with_mask, strict=False)
        detail = (f"Network: {net.network_address}  "
                  f"Broadcast: {net.broadcast_address}  "
                  f"Usable hosts: {net.num_addresses - 2}")
        return CheckResult(f"Subnet Calc {ip_with_mask}", "INFO", detail=detail)
    except ValueError as e:
        return CheckResult(f"Subnet Calc {ip_with_mask}", "FAIL", detail=str(e))


def get_arp_table() -> CheckResult:
    result = run_command("arp -a", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("ARP Table", state, detail=result["message"][:500])
