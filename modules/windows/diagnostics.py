"""
Windows Diagnostics: System Info, Services, SFC/DISM/CHKDSK
--------------------------------------------------------------
Tindakan repair (SFC/DISM/CHKDSK) masuk kategori Administrative
(PRD §35) - wajib elevation + confirmation, dipanggil dari menu, bukan otomatis.
"""

from ..core.executor import run_command, is_admin
from ..core.status import CheckResult


def get_system_info() -> dict:
    result = run_command("systeminfo", timeout=20)
    if result["status"] != "success":
        return {"error": result["details"]}
    info = {}
    for line in result["message"].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            if key.strip() and val.strip():
                info[key.strip()] = val.strip()
    return info


def check_service(service_name: str) -> CheckResult:
    result = run_command(f"sc query {service_name}", timeout=10)
    if result["status"] != "success":
        return CheckResult(
            f"Service {service_name}", "FAIL",
            detail="Service tidak ditemukan / tidak bisa diquery",
            recommendation="Pastikan nama service benar, cek di services.msc.",
        )
    running = "RUNNING" in result["message"]
    state = "PASS" if running else "WARN"
    rec = "" if running else f"Service '{service_name}' tidak berjalan, restart lewat menu Sharing/Maintenance."
    return CheckResult(f"Service {service_name}", state,
                        detail="Running" if running else "Stopped", recommendation=rec)


def run_sfc() -> CheckResult:
    if not is_admin():
        return CheckResult("SFC /scannow", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command("sfc /scannow", timeout=600)
    ok = "did not find any integrity violations" in result["message"].lower()
    return CheckResult("SFC /scannow", "PASS" if ok else "WARN",
                        detail=result["message"][-300:])


def run_dism_restore_health() -> CheckResult:
    if not is_admin():
        return CheckResult("DISM RestoreHealth", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command("DISM /Online /Cleanup-Image /RestoreHealth", timeout=900)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("DISM RestoreHealth", state, detail=result["message"][-300:])


def run_chkdsk(drive: str = "C:") -> CheckResult:
    if not is_admin():
        return CheckResult(f"CHKDSK {drive}", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(f"chkdsk {drive}", timeout=120)
    return CheckResult(f"CHKDSK {drive}", "PASS" if result["status"] == "success" else "WARN",
                        detail=result["message"][-300:])


# ---- Item tambahan PRD Windows Module (16 item total) ----

from ..core.ps import launch_app, ps_info


def open_task_manager() -> CheckResult:
    return launch_app("Task Manager", "taskmgr")


def open_device_manager() -> CheckResult:
    return launch_app("Device Manager", "devmgmt.msc")


def open_event_viewer() -> CheckResult:
    return launch_app("Event Viewer", "eventvwr.msc")


def open_computer_management() -> CheckResult:
    return launch_app("Computer Management", "compmgmt.msc")


def open_disk_management() -> CheckResult:
    return launch_app("Disk Management", "diskmgmt.msc")


def open_network_connections() -> CheckResult:
    return launch_app("Network Connections", "ncpa.cpl")


def list_installed_programs() -> CheckResult:
    return ps_info(
        "Installed Programs",
        "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
        "Select-Object -First 20 DisplayName | Format-Table -HideTableHeaders",
        timeout=20,
    )


def list_local_users() -> CheckResult:
    return ps_info("Local Users", "Get-LocalUser | Select-Object Name,Enabled | Format-Table -HideTableHeaders")


def list_environment_variables() -> CheckResult:
    return ps_info("Environment Variables", "Get-ChildItem Env: | Select-Object -First 15 Name,Value | Format-Table -HideTableHeaders")


def view_hosts_file() -> CheckResult:
    result = run_command('type C:\\Windows\\System32\\drivers\\etc\\hosts', timeout=5)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Hosts File", state, detail=result["message"][:400] or result["details"])


# ---- Item yang terlewat dari list persis PRD §14 (16 item) ----

def list_services() -> CheckResult:
    return ps_info("Services", "Get-Service | Where-Object Status -ne 'Running' | Select-Object -First 15 Name,Status | Format-Table -HideTableHeaders")


def open_windows_firewall() -> CheckResult:
    return launch_app("Windows Firewall", "firewall.cpl")


def windows_update_status() -> CheckResult:
    return ps_info("Windows Update Status",
                    "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID,InstalledOn | Format-Table -HideTableHeaders")


def open_system_properties() -> CheckResult:
    return launch_app("System Properties", "sysdm.cpl")


def open_group_policy() -> CheckResult:
    return launch_app("Group Policy Editor", "gpedit.msc")
