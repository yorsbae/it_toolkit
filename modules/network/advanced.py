"""
Network Advanced Checks: DNS, ROUTING, PORT, ADAPTER
------------------------------------------------------
"""

import socket
import re
from ..core.executor import run_command
from ..core.status import CheckResult

COMMON_PORTS = {
    135: "RPC",
    139: "NetBIOS",
    445: "SMB",
    3389: "RDP",
    5985: "WinRM",
    80: "HTTP",
    443: "HTTPS",
}


def check_dns(hostname: str) -> CheckResult:
    try:
        ip = socket.gethostbyname(hostname)
        return CheckResult(f"DNS Resolve {hostname}", "PASS", detail=f"Resolved to {ip}")
    except socket.gaierror as e:
        return CheckResult(
            f"DNS Resolve {hostname}", "FAIL",
            detail=str(e),
            recommendation="Cek DNS server, coba flush DNS, atau cek koneksi ke DNS server.",
        )


def check_route(target: str) -> CheckResult:
    result = run_command(f"tracert -h 15 -w 500 {target}", timeout=20)
    if result["status"] != "success":
        return CheckResult(
            f"Traceroute {target}", "WARN",
            detail="Traceroute tidak menghasilkan output normal",
            recommendation="Beberapa hop mungkin memblokir ICMP, ini kadang normal.",
        )
    hops = len(re.findall(r"^\s*\d+\s", result["message"], re.MULTILINE))
    return CheckResult(f"Traceroute {target}", "PASS", detail=f"{hops} hop terdeteksi")


def check_port(target: str, port: int, timeout: float = 3.0) -> CheckResult:
    label = f"{target}:{port} ({COMMON_PORTS.get(port, 'TCP')})"
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return CheckResult(label, "PASS", detail="Port open")
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return CheckResult(
            label, "FAIL",
            detail=str(e),
            recommendation=f"Pastikan service pemilik port {port} berjalan dan firewall mengizinkan.",
        )


def check_adapter() -> list:
    """Layer 1 physical check via PowerShell Get-NetAdapter."""
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-NetAdapter | Select-Object Name,Status,LinkSpeed | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    results = []
    if result["status"] != "success":
        return [CheckResult("Adapter Check", "FAIL", detail=result["details"])]

    for line in result["message"].splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"\s{2,}", line)
        if len(parts) < 2:
            continue
        name = parts[0]
        status = parts[1]
        speed = parts[2] if len(parts) > 2 else "-"
        state = "PASS" if status.lower() == "up" else "FAIL"
        rec = "" if state == "PASS" else "Cek kabel/link fisik, adapter mungkin disabled atau tidak terhubung."
        results.append(CheckResult(f"Adapter {name}", state, detail=f"{status}, {speed}", recommendation=rec))
    return results or [CheckResult("Adapter Check", "UNKNOWN", detail="Tidak ada adapter terdeteksi")]


def routing_table() -> CheckResult:
    result = run_command("route print -4", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Routing Table", state, detail=result["message"][:600])


def default_route() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"(Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Select-Object -First 1).NextHop"',
        timeout=10,
    )
    gw = result["message"].strip()
    state = "PASS" if gw else "FAIL"
    rec = "" if state == "PASS" else "Tidak ada default gateway terdaftar, cek konfigurasi IP."
    return CheckResult("Default Route", state, detail=gw or "Not found", recommendation=rec)


def resolve_gateway_ip() -> str:
    """Cari IP default gateway saja (tanpa ping), dipakai untuk "Ping Gateway"
    di menu PING agar bisa di-live-stream (lihat basic.live_ping_stream)."""
    result = run_command(
        'powershell -NoProfile -Command '
        '"(Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Select-Object -First 1).NextHop"',
        timeout=10,
    )
    return result["message"].strip()


def gateway_test() -> CheckResult:
    gw = resolve_gateway_ip()
    if not gw:
        return CheckResult("Gateway Test", "FAIL", detail="Gateway tidak ditemukan")
    from .basic import ping_target
    r = ping_target(gw)
    r.label = f"Gateway Test ({gw})"
    return r


def route_test(target: str) -> CheckResult:
    """Cek apakah ada route valid ke target tanpa full traceroute."""
    result = run_command(f"ping -n 1 -f -l 1472 {target}", timeout=5)
    state = "PASS" if result["status"] == "success" else "WARN"
    return CheckResult(f"Route Test {target}", state, detail=result["message"][-200:])


def list_listening_ports() -> CheckResult:
    result = run_command("netstat -an | findstr LISTENING", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    lines = result["message"].splitlines()
    return CheckResult("Listening Ports", state, detail=f"{len(lines)} port listening")


def port_scan(target: str, ports: list) -> list:
    return [check_port(target, p) for p in ports]


def port_scan_range(target: str, start: int, end: int, limit: int = 200, max_workers: int = 32) -> list:
    from concurrent.futures import ThreadPoolExecutor
    end = min(end, start + limit)
    ports = list(range(start, end + 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(lambda p: check_port(target, p, timeout=0.5), ports))


def common_service_port_test(target: str) -> list:
    return [check_port(target, p) for p in COMMON_PORTS]


def dns_lookup(hostname: str) -> CheckResult:
    return check_dns(hostname)


def reverse_lookup(ip: str) -> CheckResult:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return CheckResult(f"Reverse Lookup {ip}", "PASS", detail=host)
    except socket.herror as e:
        return CheckResult(f"Reverse Lookup {ip}", "FAIL", detail=str(e),
                            recommendation="IP mungkin tidak punya PTR record.")


def dns_server_test() -> list:
    result = run_command(
        'powershell -NoProfile -Command "(Get-DnsClientServerAddress -AddressFamily IPv4).ServerAddresses"',
        timeout=10,
    )
    servers = [s.strip() for s in result["message"].splitlines() if s.strip()]
    results = []
    for s in servers:
        results.append(check_port(s, 53))
    return results or [CheckResult("DNS Server Test", "UNKNOWN", detail="Tidak ada DNS server terkonfigurasi")]


def flush_dns() -> CheckResult:
    result = run_command("ipconfig /flushdns", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Flush DNS Cache", state, detail=result["message"])


def current_dns_configuration() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command "Get-DnsClientServerAddress -AddressFamily IPv4 | Format-Table -HideTableHeaders"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Current DNS Configuration", state, detail=result["message"][:400])


def adapter_status() -> list:
    return check_adapter()


def adapter_information(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "Get-NetAdapter -Name \'{name}\' | Format-List"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Adapter Info {name}", state, detail=result["message"][:500])


def enable_adapter(name: str) -> CheckResult:
    result = run_command(f'powershell -NoProfile -Command "Enable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Enable Adapter {name}", state, detail=result["message"] or "Enabled")


def disable_adapter(name: str) -> CheckResult:
    result = run_command(f'powershell -NoProfile -Command "Disable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Disable Adapter {name}", state, detail=result["message"] or "Disabled")


def reset_adapter(name: str) -> CheckResult:
    r1 = run_command(f'powershell -NoProfile -Command "Disable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    r2 = run_command(f'powershell -NoProfile -Command "Enable-NetAdapter -Name \'{name}\' -Confirm:$false"', timeout=15)
    state = "PASS" if r1["status"] == "success" and r2["status"] == "success" else "FAIL"
    return CheckResult(f"Reset Adapter {name}", state, detail="Adapter di-disable lalu enable kembali")


def interface_statistics(name: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "Get-NetAdapterStatistics -Name \'{name}\' | Format-List"',
        timeout=10,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Interface Statistics {name}", state, detail=result["message"][:500])


def scan_subnet(subnet_cidr: str, port: int = 445, limit: int = 254, max_workers: int = 32) -> list:
    """PRD §13 Network Scan. subnet_cidr contoh '192.168.10.0/24'.
    Multi-threaded supaya scan satu /24 tidak makan waktu bermenit-menit."""
    import ipaddress
    from concurrent.futures import ThreadPoolExecutor
    try:
        net = ipaddress.ip_network(subnet_cidr, strict=False)
    except ValueError as e:
        return [CheckResult(f"Scan {subnet_cidr}", "FAIL", detail=str(e))]

    ips = [str(ip) for i, ip in enumerate(net.hosts()) if i < limit]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(lambda ip: check_port(ip, port, timeout=0.5), ips))
    return results


def ping_sweep(subnet_cidr: str, limit: int = 254, max_workers: int = 32) -> list:
    import ipaddress
    from concurrent.futures import ThreadPoolExecutor
    from .basic import ping_target
    try:
        net = ipaddress.ip_network(subnet_cidr, strict=False)
    except ValueError as e:
        return [CheckResult(f"Ping Sweep {subnet_cidr}", "FAIL", detail=str(e))]

    ips = [str(ip) for i, ip in enumerate(net.hosts()) if i < limit]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(lambda ip: ping_target(ip, count=1), ips))
    active = [r for r in results if r.state == "PASS"]
    return active or [CheckResult(f"Ping Sweep {subnet_cidr}", "INFO", detail="Tidak ada host aktif ditemukan")]


def full_osi_diagnostic(target: str) -> list:
    """Full 7-layer diagnostic (PRD §6.3) - versi ringkas menggabungkan check yang benar-benar bisa diverifikasi."""
    from .basic import ping_target

    results = []
    results += check_adapter()                      # Layer 1
    results.append(check_dns(target) if not re.match(r"^\d+\.\d+\.\d+\.\d+$", target)
                    else CheckResult("Layer 2/3 ARP", "SKIP", detail="Target berupa IP, skip DNS"))
    results.append(ping_target(target))              # Layer 3
    for port in (445, 135, 3389):
        results.append(check_port(target, port))     # Layer 4
    return results


def wake_on_lan(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> CheckResult:
    """Kirim Magic Packet WoL. Bonus network utility (bukan item eksplisit PRD,
    ditambahkan karena relevan dengan Network Tools)."""
    import socket as socket_lib
    try:
        mac_clean = mac_address.replace(":", "").replace("-", "").strip()
        if len(mac_clean) != 12:
            return CheckResult(f"Wake-on-LAN {mac_address}", "FAIL", detail="Format MAC tidak valid (harus 12 hex digit)")
        mac_bytes = bytes.fromhex(mac_clean)
        magic_packet = b"\xff" * 6 + mac_bytes * 16

        sock = socket_lib.socket(socket_lib.AF_INET, socket_lib.SOCK_DGRAM)
        sock.setsockopt(socket_lib.SOL_SOCKET, socket_lib.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
        sock.close()
        return CheckResult(f"Wake-on-LAN {mac_address}", "PASS", detail=f"Magic packet terkirim ke {broadcast_ip}:{port}")
    except Exception as e:
        return CheckResult(f"Wake-on-LAN {mac_address}", "FAIL", detail=str(e))
