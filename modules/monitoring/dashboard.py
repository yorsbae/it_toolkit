"""
Monitoring Module (PRD §27) - 11 item
------------------------------------------
Snapshot functions dipanggil berulang oleh main.py (loop + rich.Live) untuk
live dashboard. Nilai bar (CPU/RAM/Disk) dikembalikan sebagai 0-100 float
supaya rendering ASCII bar ada di UI layer, bukan di sini.
"""

from ..core.executor import run_command
from ..core.status import CheckResult
from ..network.basic import ping_target
from ..core.config import load_json


def cpu_usage() -> float:
    result = run_command(
        'powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).LoadPercentage"',
        timeout=8,
    )
    try:
        return float(result["message"].strip())
    except (ValueError, TypeError):
        return 0.0


def ram_usage() -> float:
    result = run_command(
        'powershell -NoProfile -Command '
        '"$os=Get-CimInstance Win32_OperatingSystem; '
        '[math]::Round((($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize)*100,1)"',
        timeout=8,
    )
    try:
        return float(result["message"].strip())
    except (ValueError, TypeError):
        return 0.0


def disk_usage(drive: str = "C:") -> float:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"$d=Get-CimInstance Win32_LogicalDisk -Filter \\"DeviceID=\'{drive}\'\\"; '
        f'[math]::Round((($d.Size-$d.FreeSpace)/$d.Size)*100,1)"',
        timeout=8,
    )
    try:
        return float(result["message"].strip())
    except (ValueError, TypeError):
        return 0.0


def network_throughput_mbps() -> float:
    result = run_command(
        'powershell -NoProfile -Command '
        '"(Get-NetAdapterStatistics | Measure-Object -Property ReceivedBytes -Sum).Sum / 1MB"',
        timeout=8,
    )
    try:
        return round(float(result["message"].strip()), 1)
    except (ValueError, TypeError):
        return 0.0


def process_count() -> int:
    result = run_command('powershell -NoProfile -Command "(Get-Process).Count"', timeout=8)
    try:
        return int(result["message"].strip())
    except (ValueError, TypeError):
        return 0


def service_count() -> int:
    result = run_command('powershell -NoProfile -Command "(Get-Service).Count"', timeout=8)
    try:
        return int(result["message"].strip())
    except (ValueError, TypeError):
        return 0


def uptime() -> str:
    result = run_command(
        'powershell -NoProfile -Command '
        '"$u=(Get-Date)-(Get-CimInstance Win32_OperatingSystem).LastBootUpTime; '
        '\'{0}d {1}h {2}m\' -f $u.Days,$u.Hours,$u.Minutes"',
        timeout=8,
    )
    return result["message"].strip() or "Unknown"


def top_processes(limit: int = 5) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"Get-Process | Sort-Object CPU -Descending | Select-Object -First {limit} Name,CPU | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Top Processes", state, detail=result["message"][:400])


def services_not_running() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-Service | Where-Object {$_.StartType -eq \'Automatic\' -and $_.Status -ne \'Running\'} | '
        'Select-Object -First 10 Name | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    lines = [l for l in result["message"].splitlines() if l.strip()]
    state = "PASS" if not lines else "WARN"
    rec = "" if not lines else "Ada auto-start service yang seharusnya jalan tapi berhenti."
    return CheckResult("Auto-start Services Not Running", state, detail=f"{len(lines)} service(s)", recommendation=rec)


def get_monitor_targets() -> list:
    servers = load_json("servers.json", default={"servers": []}).get("servers", [])
    from ..cctv.diagnostics import get_camera_list
    cameras = get_camera_list()
    targets = [{"name": s["name"], "ip": s["ip"]} for s in servers]
    targets += [{"name": c["name"] or c["ip"], "ip": c["ip"]} for c in cameras]
    return targets


def ping_monitor_snapshot() -> list:
    results = []
    for t in get_monitor_targets():
        r = ping_target(t["ip"], count=1)
        results.append((t["name"], r))
    return results


def server_monitor_snapshot() -> list:
    servers = load_json("servers.json", default={"servers": []}).get("servers", [])
    return [(s["name"], ping_target(s["ip"], count=1)) for s in servers]


def printer_monitor_snapshot() -> list:
    from ..printer.diagnostics import list_printers
    printers = list_printers()
    return [(p["name"], p["status"]) for p in printers]


def cctv_monitor_snapshot() -> list:
    from ..cctv.diagnostics import get_camera_list
    cameras = get_camera_list()
    return [(c.get("name") or c["ip"], ping_target(c["ip"], count=1)) for c in cameras]


def full_dashboard_snapshot() -> dict:
    return {
        "cpu": cpu_usage(),
        "ram": ram_usage(),
        "disk": disk_usage(),
        "network_mbps": network_throughput_mbps(),
        "uptime": uptime(),
        "processes": process_count(),
        "services": service_count(),
    }


def snapshot() -> list:
    """Backward-compat alias dipakai main.py versi sebelumnya."""
    return ping_monitor_snapshot()
