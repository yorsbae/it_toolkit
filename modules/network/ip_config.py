"""
IP Configuration Actions (PRD §7)
--------------------------------------
Menggunakan `netsh interface ip` - built-in Windows, tidak butuh tool tambahan.
Semua fungsi di sini Administrative (butuh admin) dan HARUS dipanggil setelah
user confirm di UI.
"""

from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from .basic import get_ip_configuration


def _require_admin(action_label: str):
    if not is_admin():
        return CheckResult(action_label, "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    return None


def change_ip_address(adapter: str, ip: str, mask: str) -> CheckResult:
    guard = _require_admin("Change IP Address")
    if guard:
        return guard
    result = run_command(f'netsh interface ip set address name="{adapter}" static {ip} {mask}', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Change IP -> {ip}", state, detail=result["message"] or result["details"])


def change_gateway(adapter: str, gateway: str) -> CheckResult:
    guard = _require_admin("Change Gateway")
    if guard:
        return guard
    result = run_command(f'netsh interface ip set address name="{adapter}" gateway={gateway} gwmetric=1', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Change Gateway -> {gateway}", state, detail=result["message"] or result["details"])


def change_dns(adapter: str, dns: str) -> CheckResult:
    guard = _require_admin("Change DNS")
    if guard:
        return guard
    result = run_command(f'netsh interface ip set dns name="{adapter}" static {dns}', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Change DNS -> {dns}", state, detail=result["message"] or result["details"])


def set_dhcp(adapter: str) -> CheckResult:
    guard = _require_admin("Set DHCP")
    if guard:
        return guard
    r1 = run_command(f'netsh interface ip set address name="{adapter}" source=dhcp', timeout=15)
    r2 = run_command(f'netsh interface ip set dns name="{adapter}" source=dhcp', timeout=15)
    state = "PASS" if r1["status"] == "success" and r2["status"] == "success" else "FAIL"
    return CheckResult("Set DHCP", state, detail="Adapter diset ke DHCP (IP & DNS otomatis)")


def set_static_ip(adapter: str, ip: str, mask: str, gateway: str, dns: str) -> list:
    guard = _require_admin("Set Static IP")
    if guard:
        return [guard]
    results = [change_ip_address(adapter, ip, mask)]
    if gateway:
        results.append(change_gateway(adapter, gateway))
    if dns:
        results.append(change_dns(adapter, dns))
    return results


def release_renew_ip(adapter: str) -> list:
    guard = _require_admin("Release/Renew IP")
    if guard:
        return [guard]
    r1 = run_command(f'ipconfig /release "{adapter}"', timeout=15)
    r2 = run_command(f'ipconfig /renew "{adapter}"', timeout=20)
    state1 = "PASS" if r1["status"] == "success" else "WARN"
    state2 = "PASS" if r2["status"] == "success" else "FAIL"
    return [
        CheckResult("Release IP", state1, detail=r1["message"][-200:]),
        CheckResult("Renew IP", state2, detail=r2["message"][-200:]),
    ]


def reset_tcpip_stack() -> CheckResult:
    guard = _require_admin("Reset TCP/IP Stack")
    if guard:
        return guard
    result = run_command("netsh int ip reset", timeout=20)
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "Coba jalankan manual sebagai admin."
    return CheckResult("Reset TCP/IP Stack", state,
                        detail="Restart PC diperlukan agar efektif" if state == "PASS" else result["details"],
                        recommendation=rec)


def verify_after_change() -> list:
    """Verifikasi standar setelah perubahan IP (PRD §7 'Applying...' block)."""
    from .basic import ping_target
    results = []
    data = get_ip_configuration()
    gw = None
    for adapter, info in data.items():
        if "Default Gateway" in info and info["Default Gateway"]:
            gw = info["Default Gateway"]
            break
    if gw:
        r = ping_target(gw)
        r.label = "Gateway reachable"
        results.append(r)
    results.append(ping_target("8.8.8.8"))
    return results
