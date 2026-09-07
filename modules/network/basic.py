"""
Network Basic Checks: PING & IP CONFIGURATION
-----------------------------------------------
Contoh implementasi nyata (bukan dummy) mengikuti prinsip PRD:
Input target -> Pemeriksaan -> Status -> Detail -> Rekomendasi.
"""

import re
import time
import subprocess
from ..core.executor import run_command
from ..core.status import CheckResult


def live_ping_stream(target: str, count: int = 4, continuous: bool = False, max_seconds: int = 60):
    """Ping REAL-TIME, persis seperti `ping` di CMD pada umumnya.

    `ping_target()` di bawah memakai `run_command()` (subprocess.run dengan
    capture_output=True) yang MENUNGGU seluruh proses ping selesai baru
    mengembalikan satu ringkasan statis. Di layar itu terasa seperti "diam
    saja lalu tiba-tiba muncul satu baris" - bukan ping sungguhan yang balas
    satu-satu (4 baris "Reply from ..." muncul berurutan seiring waktu).

    Generator ini jalankan `ping` lewat subprocess.Popen dan yield SETIAP
    baris keluaran SAAT proses masih berjalan (real-time), sehingga tampilan
    di layar berubah/update setiap ada balasan - persis seperti ping command
    pada umumnya (Windows default: 4 baris balasan + 1 blok statistik).

    - continuous=False (default): `ping -n {count} target`. Generator selesai
      sendiri setelah paket terakhir, lalu meng-yield SATU CheckResult
      ringkasan di baris paling akhir (dipakai caller untuk log_action() /
      simpan ke report, seperti ping_target() sebelumnya).
    - continuous=True: `ping -t target` (tanpa henti, untuk menu
      "Continuous Ping"). Tidak pernah meng-yield CheckResult karena memang
      tidak berhenti sendiri; caller yang menghentikan (mis. Ctrl+C / close
      generator). Proses ping.exe otomatis dimatikan di background lewat
      blok `finally` supaya tidak ada proses menggantung/zombie.
    """
    cmd = f"ping -t {target}" if continuous else f"ping -n {count} {target}"
    lines = []
    start = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
    except Exception as e:
        yield CheckResult(f"Ping {target}", "FAIL", detail=f"Gagal menjalankan ping: {e}")
        return

    try:
        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            if line:
                lines.append(line)
                yield line
            if not continuous and (time.time() - start) > max_seconds:
                break
        if not continuous:
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
    finally:
        # Selalu pastikan proses ping.exe berhenti, baik karena selesai
        # normal, dibatalkan (Ctrl+C -> generator.close()), atau timeout.
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    if continuous:
        return

    output = "\n".join(lines)
    loss_match = re.search(r"\((\d+)% loss\)", output)
    loss_pct = int(loss_match.group(1)) if loss_match else None

    if not lines or loss_pct == 100:
        yield CheckResult(
            label=f"Ping {target}",
            state="FAIL",
            detail="Request timed out / unreachable",
            recommendation="Periksa kabel/koneksi, IP target, atau firewall ICMP.",
        )
        return
    if loss_pct and loss_pct > 0:
        yield CheckResult(
            label=f"Ping {target}",
            state="WARN",
            detail=f"Packet loss {loss_pct}%",
            recommendation="Cek kestabilan link / interferensi jaringan.",
        )
        return
    avg_match = re.search(r"Average = (\d+)ms", output)
    avg = f", avg {avg_match.group(1)}ms" if avg_match else ""
    yield CheckResult(label=f"Ping {target}", state="PASS", detail=f"0% loss{avg}")


def ping_target(target: str, count: int = 4) -> CheckResult:
    result = run_command(f"ping -n {count} {target}", timeout=10)
    output = result["message"]

    loss_match = re.search(r"\((\d+)% loss\)", output)
    loss_pct = int(loss_match.group(1)) if loss_match else None

    if result["status"] != "success" or loss_pct == 100:
        return CheckResult(
            label=f"Ping {target}",
            state="FAIL",
            detail="Request timed out / unreachable",
            recommendation="Periksa kabel/koneksi, IP target, atau firewall ICMP.",
        )
    if loss_pct and loss_pct > 0:
        return CheckResult(
            label=f"Ping {target}",
            state="WARN",
            detail=f"Packet loss {loss_pct}%",
            recommendation="Cek kestabilan link / interferensi jaringan.",
        )
    avg_match = re.search(r"Average = (\d+)ms", output)
    avg = f", avg {avg_match.group(1)}ms" if avg_match else ""
    return CheckResult(
        label=f"Ping {target}",
        state="PASS",
        detail=f"0% loss{avg}",
    )


def ping_multiple(targets: list) -> list:
    """targets: list of dict {label, ip}. PRD §8 'Ping Multiple Targets'."""
    results = []
    for t in targets:
        r = ping_target(t["ip"], count=1)
        r.label = f"{t['label']}  {t['ip']}"
        results.append(r)
    return results


def ping_internet() -> CheckResult:
    return ping_target("8.8.8.8")


def get_ip_configuration() -> dict:
    """Parsing dasar 'ipconfig /all' menjadi dict per-adapter (ringkas)."""
    result = run_command("ipconfig /all", timeout=10)
    if result["status"] != "success":
        return {"error": result["details"]}

    adapters = {}
    current = None
    for line in result["message"].splitlines():
        if line and not line.startswith(" ") and ":" not in line[:1]:
            current = line.strip().rstrip(":")
            adapters[current] = {}
        elif current and ":" in line:
            key, _, val = line.strip().partition(":")
            if key and val.strip():
                adapters[current][key.strip()] = val.strip()
    return adapters
