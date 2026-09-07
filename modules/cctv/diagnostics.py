"""
CCTV / Network Camera Module (PRD §17)
------------------------------------------
Termasuk sistem labeling: scan -> assign name/location -> simpan ke
config/cctv.json, match by IP saat re-scan supaya label tidak hilang.
"""

import ipaddress
from datetime import datetime
from ..core.config import load_json, save_json
from ..core.status import CheckResult
from ..network.basic import ping_target
from ..network.advanced import check_port

CCTV_FILE = "cctv.json"


# ------------------------------------------------------------ persistence --

def _load_cameras() -> list:
    """PRD §17: cctv.json adalah flat JSON array, BUKAN dibungkus {"cameras": [...]}."""
    data = load_json(CCTV_FILE, default=[])
    if isinstance(data, dict):
        # Backward-compat: kalau file lama masih format lama {"cameras": [...]}
        return data.get("cameras", [])
    return data


def _save_cameras(cameras: list):
    save_json(CCTV_FILE, cameras)


def get_camera_list() -> list:
    return _load_cameras()


def find_camera(ip: str = None, name: str = None) -> dict:
    cameras = _load_cameras()
    for cam in cameras:
        if ip and cam.get("ip") == ip:
            return cam
        if name and cam.get("name", "").lower() == name.lower():
            return cam
    return None


# ------------------------------------------------------------------ scan --

def camera_ip_scan(subnet_cidr: str, limit: int = 254, max_workers: int = 32) -> list:
    """PRD §17.1 - scan subnet, kembalikan list dict {ip, status} MENTAH (belum disimpan).
    Multi-threaded supaya tidak lambat untuk /24 penuh."""
    from concurrent.futures import ThreadPoolExecutor
    try:
        net = ipaddress.ip_network(subnet_cidr, strict=False)
    except ValueError:
        return []

    ips = [str(ip) for i, ip in enumerate(net.hosts()) if i < limit]

    def _check(ip_str):
        r = ping_target(ip_str, count=1)
        return {"ip": ip_str, "status": "ONLINE"} if r.state == "PASS" else None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(_check, ips))
    return [r for r in results if r]


def save_scan_results(found: list, labels: dict = None):
    """
    found: list of {ip, status} dari camera_ip_scan.
    labels: dict {ip: name} untuk device yang mau dilabeli sekarang (opsional).
    Device yang sudah ada di cctv.json (match by IP) di-update statusnya,
    bukan dibuat entry baru.
    """
    labels = labels or {}
    cameras = _load_cameras()
    by_ip = {c["ip"]: c for c in cameras}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for device in found:
        ip = device["ip"]
        if ip in by_ip:
            by_ip[ip]["last_status"] = device["status"]
            by_ip[ip]["last_checked"] = now
            if ip in labels:
                by_ip[ip]["name"] = labels[ip]
        else:
            new_cam = {
                "name": labels.get(ip, ""),
                "ip": ip,
                "mac": "",
                "last_status": device["status"],
                "last_checked": now,
            }
            cameras.append(new_cam)
            by_ip[ip] = new_cam

    _save_cameras(cameras)
    return cameras


def assign_label(ip: str, name: str) -> CheckResult:
    cameras = _load_cameras()
    for cam in cameras:
        if cam["ip"] == ip:
            cam["name"] = name
            _save_cameras(cameras)
            return CheckResult(f"Label {ip}", "PASS", detail=f"-> {name}")
    return CheckResult(f"Label {ip}", "FAIL", detail="IP tidak ditemukan di cctv.json, scan dulu.")


def remove_label(ip: str) -> CheckResult:
    cameras = _load_cameras()
    for cam in cameras:
        if cam["ip"] == ip:
            cam["name"] = ""
            _save_cameras(cameras)
            return CheckResult(f"Remove label {ip}", "PASS", detail="Label dihapus")
    return CheckResult(f"Remove label {ip}", "FAIL", detail="IP tidak ditemukan")


def _display_name(cam: dict) -> str:
    return f"{cam['name']} - {cam['ip']}" if cam.get("name") else cam["ip"]


# -------------------------------------------------------------- checks --

def camera_ping(cam: dict) -> CheckResult:
    r = ping_target(cam["ip"], count=1)
    r.label = _display_name(cam)
    return r


def nvr_ping(ip: str) -> CheckResult:
    r = ping_target(ip, count=1)
    r.label = f"NVR {ip}"
    return r


def nvr_port_test(ip: str, port: int = 80) -> CheckResult:
    return check_port(ip, port)


def rtsp_test(ip: str, port: int = 554) -> CheckResult:
    r = check_port(ip, port)
    r.label = f"RTSP {ip}:{port}"
    return r


def onvif_discovery(ip: str, port: int = 3702) -> CheckResult:
    r = check_port(ip, port)
    r.label = f"ONVIF {ip}:{port}"
    return r


def camera_status() -> list:
    cameras = _load_cameras()
    if not cameras:
        return [CheckResult("Camera Status", "UNKNOWN", detail="Belum ada kamera terdaftar, jalankan Camera IP Scan dulu.")]
    return [camera_ping(cam) for cam in cameras]


def camera_status_table() -> dict:
    """PRD §17 contoh 'Camera Status' - tabel NAMA/IP/STATUS/LATENCY + summary
    TOTAL/ONLINE/OFFLINE. Dipakai UI layer untuk render tabel, bukan list CheckResult polos."""
    import re
    cameras = _load_cameras()
    rows = []
    online_count = 0
    for cam in cameras:
        r = camera_ping(cam)
        online = r.state == "PASS"
        online_count += 1 if online else 0
        ms_match = re.search(r"avg (\d+)ms", r.detail)
        latency = f"{ms_match.group(1)}ms" if ms_match else "---"
        rows.append({
            "display_name": _display_name(cam),
            "ip": cam["ip"],
            "status": "ONLINE" if online else "OFFLINE",
            "latency": latency if online else "---",
            "online": online,
        })
    return {
        "rows": rows,
        "total": len(rows),
        "online": online_count,
        "offline": len(rows) - online_count,
    }


def offline_camera_finder() -> list:
    results = camera_status()
    offline = [r for r in results if r.state == "FAIL"]
    return offline or [CheckResult("Offline Camera Finder", "PASS", detail="Semua kamera online")]


def nvr_information(ip: str) -> CheckResult:
    r = ping_target(ip)
    r.label = f"NVR Information {ip}"
    return r


def diagnose_all_cameras() -> list:
    """Dipakai oleh main.py untuk 'Full Sharing/CCTV Report' cepat."""
    return camera_status()
