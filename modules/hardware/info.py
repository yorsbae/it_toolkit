"""
Hardware Information
----------------------
Semua via PowerShell Get-CimInstance (built-in Windows, tidak butuh tool tambahan).
"""

from ..core.executor import run_command
from ..core.status import CheckResult


def get_cpu_info() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-CimInstance Win32_Processor | Select-Object Name,LoadPercentage | Format-List"',
        timeout=10,
    )
    if result["status"] != "success":
        return CheckResult("CPU Info", "FAIL", detail=result["details"])
    return CheckResult("CPU Info", "INFO", detail=result["message"].replace("\n", " | "))


def get_ram_info() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"$os=Get-CimInstance Win32_OperatingSystem; '
        '[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/1MB,2).ToString() '
        '+ \' GB used of \' + [math]::Round($os.TotalVisibleMemorySize/1MB,2).ToString() + \' GB\'"',
        timeout=10,
    )
    if result["status"] != "success":
        return CheckResult("RAM Info", "FAIL", detail=result["details"])
    return CheckResult("RAM Info", "INFO", detail=result["message"].strip())


def get_disk_info() -> list:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-CimInstance Win32_LogicalDisk -Filter \\"DriveType=3\\" | '
        'Select-Object DeviceID,@{N=\'FreeGB\';E={[math]::Round($_.FreeSpace/1GB,1)}},'
        '@{N=\'SizeGB\';E={[math]::Round($_.Size/1GB,1)}} | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    results = []
    if result["status"] != "success":
        return [CheckResult("Disk Info", "FAIL", detail=result["details"])]

    for line in result["message"].splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        drive, free, size = parts[0], parts[1], parts[2]
        try:
            pct_free = float(free) / float(size) * 100
        except (ValueError, ZeroDivisionError):
            pct_free = 100
        state = "PASS" if pct_free > 15 else ("WARN" if pct_free > 5 else "FAIL")
        rec = "" if state == "PASS" else "Disk hampir penuh, bersihkan file lewat menu Maintenance."
        results.append(CheckResult(f"Disk {drive}", state, detail=f"{free} GB free of {size} GB", recommendation=rec))
    return results or [CheckResult("Disk Info", "UNKNOWN", detail="Tidak ada disk terdeteksi")]


# ---- Item tambahan PRD Hardware Module (13 item total) ----

from ..core.ps import ps_info


def get_gpu_info() -> CheckResult:
    return ps_info("GPU Info", "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | Format-List")


def get_motherboard_info() -> CheckResult:
    return ps_info("Motherboard Info", "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product | Format-List")


def get_bios_info() -> CheckResult:
    return ps_info("BIOS Info", "Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | Format-List")


def get_serial_number() -> CheckResult:
    return ps_info("Serial Number", "(Get-CimInstance Win32_BIOS).SerialNumber")


def get_usb_devices() -> CheckResult:
    return ps_info("USB Devices", "Get-PnpDevice -Class USB -Status OK | Select-Object -First 15 FriendlyName | Format-Table -HideTableHeaders")


def get_monitor_info() -> CheckResult:
    return ps_info("Monitor Info", "Get-CimInstance Win32_DesktopMonitor | Select-Object Name,ScreenWidth,ScreenHeight | Format-List")


def get_network_adapter_hardware() -> list:
    """PRD §15 item [10] Network Adapter - dari sisi Hardware (fisik), bukan diagnostic
    konektivitas (itu ada di Network module)."""
    from ..network.advanced import check_adapter
    return check_adapter()


def get_battery_info() -> CheckResult:
    result = ps_info("Battery Info", "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus | Format-List")
    if result.state == "UNKNOWN":
        result.detail = "Tidak ada baterai terdeteksi (mungkin PC desktop)"
    return result


def get_disk_smart_status() -> list:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-CimInstance -Namespace root\\wmi -ClassName MSStorageDriver_FailurePredictStatus | '
        'Select-Object InstanceName,PredictFailure | Format-Table -HideTableHeaders"',
        timeout=15,
    )
    results = []
    if result["status"] != "success" or not result["message"].strip():
        return [CheckResult("Disk SMART Status", "UNKNOWN", detail="SMART data tidak tersedia (butuh admin/driver support)")]
    for line in result["message"].splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)
        if len(parts) != 2:
            continue
        name, failing = parts
        state = "FAIL" if failing.lower() == "true" else "PASS"
        rec = "" if state == "PASS" else "Disk menunjukkan tanda kegagalan SMART, backup data segera."
        results.append(CheckResult(f"SMART {name}", state, detail="Predict Failure: " + failing, recommendation=rec))
    return results or [CheckResult("Disk SMART Status", "UNKNOWN", detail="Tidak ada data SMART")]
