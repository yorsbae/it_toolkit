"""
Remote Module (PRD §25) - 11 item
------------------------------------
External apps (AnyDesk/TeamViewer) hanya dilaunch kalau terdeteksi terinstall.
"""

import subprocess
from ..core.status import CheckResult
from ..core.ps import is_app_installed
from ..core.executor import run_command


def launch_rdp(target: str) -> CheckResult:
    try:
        subprocess.Popen(f"mstsc /v:{target}", shell=True)
        return CheckResult(f"RDP -> {target}", "PASS", detail="mstsc dibuka")
    except Exception as e:
        return CheckResult(f"RDP -> {target}", "FAIL", detail=str(e))


def remote_cmd(target: str, command: str) -> CheckResult:
    result = run_command(f'winrs -r:{target} "{command}"', timeout=30)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remote CMD @ {target}", state, detail=result["message"][:400] or result["details"][:400])


def remote_powershell(target: str, command: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "Invoke-Command -ComputerName {target} -ScriptBlock {{ {command} }}"',
        timeout=30,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remote PowerShell @ {target}", state, detail=result["message"][:400] or result["details"][:400])


def open_computer_management(target: str) -> CheckResult:
    try:
        subprocess.Popen(f"compmgmt.msc /computer:{target}", shell=True)
        return CheckResult(f"Computer Management -> {target}", "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult(f"Computer Management -> {target}", "FAIL", detail=str(e))


def remote_services(target: str) -> CheckResult:
    result = run_command(f"sc \\\\{target} query state= all", timeout=20)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remote Services @ {target}", state, detail=result["message"][:500] or result["details"])


def remote_event_viewer(target: str) -> CheckResult:
    try:
        subprocess.Popen(f'eventvwr.msc /computer={target}', shell=True)
        return CheckResult(f"Event Viewer -> {target}", "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult(f"Event Viewer -> {target}", "FAIL", detail=str(e))


def remote_task_manager(target: str) -> CheckResult:
    return CheckResult(f"Remote Task Manager -> {target}", "WARN",
                        detail="Windows tidak menyediakan remote Task Manager native.",
                        recommendation="Gunakan RDP atau Remote Services untuk melihat proses jarak jauh.")


def remote_registry(target: str) -> CheckResult:
    result = run_command(f"sc \\\\{target} query RemoteRegistry", timeout=15)
    running = result["status"] == "success" and "RUNNING" in result["message"]
    state = "PASS" if running else "WARN"
    rec = "" if running else "Service Remote Registry tidak berjalan di target, aktifkan dulu bila perlu akses regedit jarak jauh."
    return CheckResult(f"Remote Registry @ {target}", state, detail="Running" if running else "Stopped", recommendation=rec)


def launch_anydesk(target_id: str = "") -> CheckResult:
    if not is_app_installed("AnyDesk.exe"):
        return CheckResult("AnyDesk", "WARN", detail="AnyDesk tidak terdeteksi terinstall",
                            recommendation="Install AnyDesk terlebih dahulu.")
    try:
        subprocess.Popen(f"AnyDesk.exe {target_id}", shell=True)
        return CheckResult("AnyDesk", "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult("AnyDesk", "FAIL", detail=str(e))


def launch_teamviewer() -> CheckResult:
    if not is_app_installed("TeamViewer.exe"):
        return CheckResult("TeamViewer", "WARN", detail="TeamViewer tidak terdeteksi terinstall",
                            recommendation="Install TeamViewer terlebih dahulu.")
    try:
        subprocess.Popen("TeamViewer.exe", shell=True)
        return CheckResult("TeamViewer", "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult("TeamViewer", "FAIL", detail=str(e))


def launch_quick_assist() -> CheckResult:
    try:
        subprocess.Popen("quickassist", shell=True)
        return CheckResult("Quick Assist", "PASS", detail="Dibuka")
    except Exception as e:
        return CheckResult("Quick Assist", "FAIL", detail=str(e))


def remote_diagnostic(target: str) -> list:
    from ..network.basic import ping_target
    from ..network.advanced import check_port
    return [
        ping_target(target),
        check_port(target, 3389),
        check_port(target, 5985),
        check_port(target, 135),
    ]
