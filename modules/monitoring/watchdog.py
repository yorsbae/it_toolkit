"""
Internet Watchdog
====================
Menjawab pola klasik: "client kadang no internet, tapi setelah restart
hub/router (AP mode) baru bisa lagi." Modul ini TIDAK menebak satu
penyebab tunggal (karena tanpa akses ke perangkat AP-nya kita tidak bisa
100% pasti), tapi membantu 3 hal nyata yang BISA dilakukan dari PC client:

  1. KLASIFIKASI - bedakan LAN mati vs Internet mati vs DNS rusak, supaya
     jelas letak masalahnya (bukan cuma "internet mati").
  2. RIWAYAT - catat setiap outage (waktu, jenis, durasi) ke histori supaya
     polanya kelihatan (mis. "selalu drop tiap ~6 jam" = indikasi kuat
     firmware AP bocor memori dan butuh reboot terjadwal, bukan masalah
     kabel/ISP).
  3. SELF-HEAL SISI CLIENT - flush DNS, renew DHCP, bersihkan ARP cache,
     restart adapter: ini semua BISA dilakukan client tanpa akses ke AP,
     dan kadang penyebabnya justru cache basi di sisi client, bukan AP-nya.

TIDAK bisa dan tidak berpura-pura bisa:
  - Toolkit ini TIDAK bisa mematikan/menyalakan listrik ke hub/router
    secara fisik lewat jaringan biasa.
  - Restart AP/ROUTER dari jarak jauh HANYA bisa kalau perangkatnya sendiri
    punya fitur remote reboot (SSH/HTTP API) yang diaktifkan & dikonfigurasi
    lewat [14] Configure Watchdog.
  - HUB murni (bukan router/AP/switch managed) TIDAK punya IP, TIDAK punya
    halaman admin, TIDAK punya SSH - alat manajemen APAPUN tidak bisa
    "bicara" ke hub sungguhan sama sekali, cuma bisa lihat GEJALA di sisi
    client (link speed, ada-tidaknya koneksi). Satu-satunya cara restart
    hub dari jarak jauh adalah lewat SMART PLUG (colokan pintar yang
    kontrol LISTRIK-nya, bukan datanya) - didukung lewat method
    "smart_plug_http" di [14] Configure Watchdog.
  - Solusi paling ANDAL untuk AP/router yang memang buggy adalah fitur
    "Scheduled Reboot" BAWAAN perangkat itu sendiri (hampir semua router
    consumer, termasuk yang murah, punya ini di System Tools) - jauh
    lebih reliable daripada reverse-engineer API yang tidak diketahui
    mereknya.
"""

import json
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..core.config import LOGS_DIR, load_json, save_json
from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..core.validate import validate_ip, ValidationError
from ..network.basic import ping_target
from ..network.advanced import resolve_gateway_ip

OUTAGE_LOG = LOGS_DIR / "outage_history.json"
WATCHDOG_CONFIG_FILE = "watchdog.json"

DEFAULT_WATCHDOG_CONFIG = {
    "check_interval_sec": 30,
    "consecutive_fails_before_action": 2,
    "self_heal_enabled": True,
    "remote_reboot_enabled": False,
    "remote_reboot_method": "none",   # "none" | "http" | "ssh" | "smart_plug_http"
    "remote_reboot_http_url": "",
    "remote_reboot_ssh_host": "",
    "remote_reboot_ssh_user": "",
    "remote_reboot_ssh_command": "reboot",
    "smart_plug_off_url": "",
    "smart_plug_on_url": "",
    "smart_plug_off_wait_sec": 5,
}


# --------------------------------------------------------------- Config --

def get_watchdog_config() -> dict:
    cfg = DEFAULT_WATCHDOG_CONFIG.copy()
    cfg.update(load_json(WATCHDOG_CONFIG_FILE, default={}))
    return cfg


def save_watchdog_config(cfg: dict) -> None:
    save_json(WATCHDOG_CONFIG_FILE, cfg)


# --------------------------------------------------------- Classification --

def get_link_speed_hint() -> str:
    """HUB murni tidak punya IP/manajemen sama sekali, jadi satu-satunya
    cara toolkit ini bisa 'melihat' indikasi hub adalah lewat GEJALA di NIC
    client: hub asli (Layer 1, bukan switch) hampir selalu mentok di
    10/100 Mbps half-duplex karena memang begitu batas teknologinya - tidak
    pernah ada hub gigabit yang diproduksi massal. Kalau LinkSpeed adapter
    saat ini menunjukkan 10 Mbps atau 100 Mbps, itu petunjuk kuat perangkat
    di seberang kabel benar-benar hub tua (atau NIC gagal auto-negotiate /
    kabel rusak) - bukan sekadar dugaan tanpa dasar."""
    result = run_command(
        "powershell -NoProfile -Command "
        "\"Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
        "Select-Object -First 1 -ExpandProperty LinkSpeed\"",
        timeout=10,
    )
    if result["status"] != "success":
        return ""
    speed = result["message"].strip()
    if not speed:
        return ""
    if "10 Mbps" in speed or "100 Mbps" in speed:
        return f"Link speed saat ini {speed} - indikasi kuat sedang lewat HUB tua/kabel rusak, bukan switch modern"
    return f"Link speed saat ini {speed}"


def check_connectivity(internet_target: str = "8.8.8.8", dns_hostname: str = "google.com") -> dict:
    """Bedakan LAN vs INTERNET vs DNS, bukan cuma satu ping ke 8.8.8.8.
    Return dict: {state, gateway_ip, gateway_ok, internet_ok, dns_ok, detail}."""
    gw = resolve_gateway_ip()
    try:
        gw = validate_ip(gw)  # guard: kalau resolve_gateway_ip malah balikin pesan error
    except ValidationError:
        gw = ""
    gw_ok = False
    if gw:
        r = ping_target(gw, count=1)
        gw_ok = r.state == "PASS"

    inet_ok = ping_target(internet_target, count=1).state == "PASS"

    dns_ok = False
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname(dns_hostname)
        dns_ok = True
    except Exception:
        dns_ok = False
    finally:
        socket.setdefaulttimeout(None)

    if gw_ok and inet_ok and dns_ok:
        state = "OK"
        detail = "LAN, Internet, dan DNS normal"
    elif not gw:
        state = "LAN_DOWN"
        detail = "Gateway tidak ditemukan/tidak merespon - kemungkinan adapter/AP/kabel/hub"
    elif not gw_ok:
        link_hint = get_link_speed_hint()
        state = "LAN_DOWN"
        detail = f"Gateway ({gw}) tidak merespon - LAN/AP/hub kemungkinan bermasalah, bukan cuma internet"
        if link_hint:
            detail += f". {link_hint}"
    elif gw_ok and not inet_ok:
        state = "INTERNET_DOWN"
        detail = f"Gateway ({gw}) OK, tapi {internet_target} tidak terjangkau - PERSIS pola 'AP hidup tapi upstream mati'"
    elif gw_ok and inet_ok and not dns_ok:
        state = "DNS_DOWN"
        detail = "Ping internet OK tapi resolusi DNS gagal - kemungkinan DNS server/relay di router bermasalah"
    else:
        state = "UNKNOWN"
        detail = "Kombinasi hasil tidak terduga"

    return {
        "state": state, "gateway_ip": gw, "gateway_ok": gw_ok,
        "internet_ok": inet_ok, "dns_ok": dns_ok, "detail": detail,
        "time": datetime.now().isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------- Self-heal --

def flush_dns() -> CheckResult:
    r = run_command("ipconfig /flushdns", timeout=10)
    return CheckResult("Flush DNS", "PASS" if r["status"] == "success" else "WARN", detail=r["message"][:200])


def clear_arp_cache() -> CheckResult:
    if not is_admin():
        return CheckResult("Clear ARP Cache", "WARN", detail="Butuh hak admin, dilewati")
    r = run_command("arp -d *", timeout=10)
    return CheckResult("Clear ARP Cache", "PASS" if r["status"] == "success" else "WARN", detail=r["message"][:200])


def renew_dhcp() -> CheckResult:
    run_command("ipconfig /release", timeout=15)
    time.sleep(1)
    r = run_command("ipconfig /renew", timeout=20)
    return CheckResult("Renew DHCP Lease", "PASS" if r["status"] == "success" else "WARN", detail=r["message"][:200])


def run_self_heal_sequence() -> list:
    """Urutan aman (tidak butuh restart adapter/AP): flush DNS -> clear ARP
    -> renew DHCP. Ini yang PALING SERING sudah cukup kalau akar masalahnya
    memang cache basi di sisi client, bukan AP-nya."""
    results = [flush_dns(), clear_arp_cache(), renew_dhcp()]
    return results


# --------------------------------------------------------- Outage history --

def _load_history() -> list:
    if not OUTAGE_LOG.exists():
        return []
    try:
        with open(OUTAGE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(history: list) -> None:
    with open(OUTAGE_LOG, "w", encoding="utf-8") as f:
        json.dump(history[-2000:], f, indent=2, ensure_ascii=False)  # cap ukuran file


def log_outage_event(state: str, detail: str, duration_sec: float = None, action_taken: str = "") -> None:
    history = _load_history()
    history.append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "state": state,
        "detail": detail,
        "duration_sec": duration_sec,
        "action_taken": action_taken,
    })
    _save_history(history)


def get_outage_history(days: int = 7) -> list:
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for ev in _load_history():
        try:
            t = datetime.fromisoformat(ev["time"])
        except Exception:
            continue
        if t >= cutoff:
            out.append(ev)
    return out


def outage_pattern_summary(history: list) -> dict:
    """Ringkasan yang membantu MENJAWAB PERTANYAAN 'kenapa': hitung jumlah
    per jenis outage, dan rata-rata jarak antar outage INTERNET_DOWN (kalau
    jaraknya konsisten, mis. selalu ~6 jam, itu indikasi kuat masalah
    firmware/uptime AP, bukan gangguan acak dari ISP)."""
    by_state = {}
    for ev in history:
        by_state[ev["state"]] = by_state.get(ev["state"], 0) + 1

    internet_down_times = [
        datetime.fromisoformat(ev["time"]) for ev in history if ev["state"] == "INTERNET_DOWN"
    ]
    internet_down_times.sort()
    gaps = [
        (internet_down_times[i] - internet_down_times[i - 1]).total_seconds() / 3600
        for i in range(1, len(internet_down_times))
    ]
    avg_gap_hours = round(sum(gaps) / len(gaps), 1) if gaps else None

    return {
        "total_events": len(history),
        "by_state": by_state,
        "avg_hours_between_internet_down": avg_gap_hours,
    }


# --------------------------------------------------------- Remote reboot --

def trigger_remote_reboot(cfg: dict = None) -> CheckResult:
    """Coba restart perangkat dari jarak jauh, HANYA kalau user sudah
    mengisi metode & alamat di [14] Configure Watchdog. Ini WAJIB
    dikonfigurasi manual per perangkat - tidak ada cara generik yang bisa
    dijamin bekerja di semua merek router/AP.

    Untuk HUB murni (tidak punya IP/manajemen sama sekali): method "http"
    dan "ssh" di atas TIDAK BISA dipakai, karena keduanya butuh perangkat
    yang bisa diajak "bicara" lewat jaringan - hub sungguhan tidak bisa.
    Satu-satunya jalan untuk hub adalah method "smart_plug_http": bukan
    bicara ke hub-nya, tapi ke SMART PLUG yang mencolok hub itu ke listrik.
    Kebanyakan smart plug (Tasmota, Shelly, TP-Link Kasa lewat local API,
    dst) punya URL lokal sederhana untuk on/off - itu yang diisi di sini."""
    cfg = cfg or get_watchdog_config()
    if not cfg.get("remote_reboot_enabled"):
        return CheckResult("Remote Reboot", "WARN", detail="Belum diaktifkan (lihat [14] Configure Watchdog)")

    method = cfg.get("remote_reboot_method", "none")
    if method == "http":
        url = cfg.get("remote_reboot_http_url", "").strip()
        if not url:
            return CheckResult("Remote Reboot AP", "FAIL", detail="URL reboot HTTP belum diisi")
        try:
            import urllib.request
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=10)
            return CheckResult("Remote Reboot AP", "PASS", detail=f"Request reboot terkirim ke {url}")
        except Exception as e:
            return CheckResult("Remote Reboot AP", "FAIL", detail=f"Gagal request ke {url}: {e}")

    elif method == "ssh":
        host = cfg.get("remote_reboot_ssh_host", "").strip()
        user = cfg.get("remote_reboot_ssh_user", "").strip()
        command = cfg.get("remote_reboot_ssh_command", "reboot").strip()
        if not host or not user:
            return CheckResult("Remote Reboot AP", "FAIL", detail="SSH host/user belum diisi")
        r = run_command(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} "{command}"',
            timeout=20,
        )
        state = "PASS" if r["status"] == "success" else "FAIL"
        return CheckResult("Remote Reboot AP", state, detail=r["message"][:200] or "Perintah SSH terkirim")

    elif method == "smart_plug_http":
        off_url = cfg.get("smart_plug_off_url", "").strip()
        on_url = cfg.get("smart_plug_on_url", "").strip()
        wait_sec = max(2, int(cfg.get("smart_plug_off_wait_sec", 5)))
        if not off_url or not on_url:
            return CheckResult("Remote Power-Cycle (Smart Plug)", "FAIL",
                                detail="URL OFF/ON smart plug belum diisi")
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(off_url, method="GET"), timeout=10)
        except Exception as e:
            return CheckResult("Remote Power-Cycle (Smart Plug)", "FAIL",
                                detail=f"Gagal matikan colokan ({off_url}): {e}")
        time.sleep(wait_sec)
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(on_url, method="GET"), timeout=10)
        except Exception as e:
            return CheckResult("Remote Power-Cycle (Smart Plug)", "FAIL",
                                detail=f"Colokan sudah OFF tapi gagal nyalakan lagi ({on_url}): {e}. "
                                       f"PERLU DINYALAKAN MANUAL SEKARANG.")
        return CheckResult("Remote Power-Cycle (Smart Plug)", "PASS",
                            detail=f"Hub dimatikan {wait_sec}s lalu dinyalakan lagi lewat smart plug")

    return CheckResult("Remote Reboot", "FAIL", detail=f"Metode '{method}' tidak dikenal")
