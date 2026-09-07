from ..core.ui import console, header, show_results, confirm, pause, ask_validated, read_choice
from ..core.status import render_line, CheckResult
from ..core.logger import log_action
from ..core.validate import (
    validate_hostname_or_ip, validate_port, validate_cidr, validate_adapter_name,
    validate_mac_address, ValidationError,
)
import time

from .basic import ping_target, get_ip_configuration, ping_multiple, ping_internet, live_ping_stream
from .advanced import (
    check_dns, check_route, check_port, check_adapter, full_osi_diagnostic,
    routing_table, default_route, gateway_test, route_test, list_listening_ports,
    port_scan, port_scan_range, common_service_port_test, dns_lookup, reverse_lookup,
    dns_server_test, flush_dns, current_dns_configuration, adapter_information,
    enable_adapter, disable_adapter, reset_adapter, interface_statistics,
    scan_subnet, ping_sweep, wake_on_lan, resolve_gateway_ip,
)
from .ip_config import (
    change_ip_address, change_gateway, change_dns, set_dhcp, set_static_ip,
    release_renew_ip, reset_tcpip_stack, verify_after_change,
)
from ..server.diagnostics import get_server_list
from ..cctv.diagnostics import get_camera_list
from ..tools.utils import get_arp_table
from ..core.config import load_json


def menu():
    while True:
        header("NETWORK")
        console.print("[01] OSI 7-LAYER DIAGNOSTIC   [06] DNS")
        console.print("[02] IP CONFIGURATION          [07] ADAPTER")
        console.print("[03] PING                      [08] NETWORK SCAN")
        console.print("[04] ROUTING                   [09] NETWORK TOOLS")
        console.print("[05] PORT / SERVICE            [10] NETWORK REPORT")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            osi_menu()
        elif c == "2":
            ip_configuration_menu()
        elif c == "3":
            ping_menu()
        elif c == "4":
            routing_menu()
        elif c == "5":
            port_service_menu()
        elif c == "6":
            dns_menu()
        elif c == "7":
            adapter_menu()
        elif c == "8":
            network_scan_menu()
        elif c == "9":
            network_tools_menu()
        elif c == "10":
            target = console.input("Target untuk Network Report: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(full_osi_diagnostic(target), module_name="NETWORK", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def osi_menu():
    while True:
        header("OSI 7-LAYER DIAGNOSTIC")
        console.print("[01] Layer 1 - Physical        [05] Layer 5 - Session")
        console.print("[02] Layer 2 - Data Link        [06] Layer 6 - Presentation")
        console.print("[03] Layer 3 - Network          [07] Layer 7 - Application")
        console.print("[04] Layer 4 - Transport        [08] Full 7-Layer Diagnostic")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results(check_adapter())
            pause()
        elif c == "2":
            console.print("[dim]Layer 2 (MAC/ARP) - lihat ARP Table di menu Tools[/dim]")
            show_results([get_arp_table()])
            pause()
        elif c == "3":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ping_target(target), default_route()])
            pause()
        elif c == "4":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(common_service_port_test(target))
            pause()
        elif c == "5":
            target = console.input("Target (SMB): ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([check_port(target, 445)])
            pause()
        elif c == "6":
            target = console.input("Target (HTTPS): ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([check_port(target, 443)])
            pause()
        elif c == "7":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([check_port(target, 80), check_port(target, 445), check_dns(target) if not target[0].isdigit() else check_port(target, 443)])
            pause()
        elif c == "8":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(full_osi_diagnostic(target), module_name="NETWORK_OSI", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def ip_configuration_menu():
    while True:
        header("IP CONFIGURATION")
        console.print("[01] View IP Configuration     [06] Static IP")
        console.print("[02] Change IP Address           [07] Release / Renew IP")
        console.print("[03] Change Gateway               [08] Flush DNS")
        console.print("[04] Change DNS                    [09] Reset TCP/IP Stack")
        console.print("[05] DHCP")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            data = get_ip_configuration()
            for adapter, info in data.items():
                console.print(f"\n[bold]{adapter}[/bold]")
                for k, v in info.items():
                    console.print(f"  {k}: {v}")
            pause()
        elif c == "2":
            adapter = console.input("Adapter name (mis. Ethernet): ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            ip = console.input("New IP Address: ").strip()
            mask = console.input("Subnet Mask: ").strip()
            if confirm(f"Apply IP {ip}/{mask} ke adapter '{adapter}'?"):
                r = change_ip_address(adapter, ip, mask)
                show_results([r])
                log_action("NETWORK", "CHANGE IP ADDRESS", f"{adapter} -> {ip}/{mask}", r.state)
                show_results(verify_after_change(), module_name="NETWORK_IP", save_report=True)
            pause()
        elif c == "3":
            adapter = console.input("Adapter name: ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            gw = console.input("New Gateway: ").strip()
            if confirm(f"Apply gateway {gw}?"):
                r = change_gateway(adapter, gw)
                show_results([r])
                log_action("NETWORK", "CHANGE GATEWAY", f"{adapter} -> {gw}", r.state)
            pause()
        elif c == "4":
            adapter = console.input("Adapter name: ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            dns = console.input("New DNS: ").strip()
            if confirm(f"Apply DNS {dns}?"):
                r = change_dns(adapter, dns)
                show_results([r])
                log_action("NETWORK", "CHANGE DNS", f"{adapter} -> {dns}", r.state)
            pause()
        elif c == "5":
            adapter = console.input("Adapter name: ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Set adapter '{adapter}' ke DHCP?"):
                r = set_dhcp(adapter)
                show_results([r])
                log_action("NETWORK", "SET DHCP", adapter, r.state)
                show_results(verify_after_change())
            pause()
        elif c == "6":
            adapter = console.input("Adapter name: ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            ip = console.input("IP Address: ").strip()
            mask = console.input("Subnet Mask: ").strip()
            gw = console.input("Gateway: ").strip()
            dns = console.input("DNS: ").strip()
            if confirm("Apply static configuration ini?"):
                results = set_static_ip(adapter, ip, mask, gw, dns)
                show_results(results)
                overall_state = "FAIL" if any(r.state == "FAIL" for r in results) else "PASS"
                log_action("NETWORK", "SET STATIC IP", f"{adapter} -> {ip}/{mask}", overall_state)
                show_results(verify_after_change(), module_name="NETWORK_IP", save_report=True)
            pause()
        elif c == "7":
            adapter = console.input("Adapter name: ").strip()
            try:
                adapter = validate_adapter_name(adapter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            results = release_renew_ip(adapter)
            show_results(results)
            overall_state = "FAIL" if any(r.state == "FAIL" for r in results) else "PASS"
            log_action("NETWORK", "RELEASE/RENEW IP", adapter, overall_state)
            pause()
        elif c == "8":
            show_results([flush_dns()])
            pause()
        elif c == "9":
            if confirm("Reset TCP/IP stack? (butuh restart PC agar efektif)"):
                r = reset_tcpip_stack()
                show_results([r])
                log_action("NETWORK", "RESET TCP/IP STACK", "LOCAL", r.state)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def _print_live_ping_line(line: str) -> None:
    """Warnai satu baris keluaran ping asli sesuai isinya (real-time)."""
    low = line.lower()
    if "reply from" in low or "bytes=" in low:
        console.print(f"[green]{line}[/green]")
    elif any(w in low for w in ("request timed out", "unreachable", "could not find", "general failure")):
        console.print(f"[red]{line}[/red]")
    elif "pinging" in low:
        console.print(f"[cyan]{line}[/cyan]")
    elif any(w in low for w in ("statistics", "packets:", "approximate round trip", "minimum =")):
        console.print(f"[bold]{line}[/bold]")
    else:
        console.print(f"[dim]{line}[/dim]")


def run_live_ping(target: str, count: int = 4) -> CheckResult:
    """Ping real-time (4 baris seperti ping pada umumnya) lalu tampilkan
    ringkasan status di akhir. Ganti pengganti pola lama `ping_target()` yang
    hanya menampilkan satu baris statis setelah proses selesai."""
    console.print(f"[dim]Pinging {target} with {count} packets...[/dim]\n")
    result = None
    for item in live_ping_stream(target, count=count):
        if isinstance(item, CheckResult):
            result = item
        else:
            _print_live_ping_line(item)
    if result is None:
        result = CheckResult(f"Ping {target}", "FAIL", detail="Tidak ada respon dari proses ping")
    console.print()
    console.print(render_line(result.label + (f" - {result.detail}" if result.detail else ""), result.state))
    return result


def ping_menu():
    while True:
        header("PING")
        console.print("[01] Ping Gateway        [05] Ping Multiple Targets")
        console.print("[02] Ping Specific IP      [06] Ping DNS")
        console.print("[03] Ping Hostname          [07] Ping Internet")
        console.print("[04] Continuous Ping")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            gw = resolve_gateway_ip()
            if not gw:
                console.print(render_line("Gateway Test", "FAIL") + " - Gateway tidak ditemukan")
                log_action("NETWORK", "PING GATEWAY", "-", "FAIL")
            else:
                r = run_live_ping(gw)
                r.label = f"Gateway Test ({gw})"
                log_action("NETWORK", "PING GATEWAY", gw, r.state)
            pause()
        elif c == "2":
            target = console.input("IP: ").strip()
            r = run_live_ping(target)
            log_action("NETWORK", "PING", target, r.state)
            pause()
        elif c == "3":
            target = console.input("Hostname: ").strip()
            r = run_live_ping(target)
            log_action("NETWORK", "PING", target, r.state)
            pause()
        elif c == "4":
            target = console.input("Target (Ctrl+C untuk stop): ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            console.print(f"[dim]Continuous ping ke {target} - Ctrl+C untuk berhenti[/dim]\n")
            gen = live_ping_stream(target, continuous=True)
            try:
                for item in gen:
                    if isinstance(item, str):
                        _print_live_ping_line(item)
            except KeyboardInterrupt:
                console.print()
            finally:
                gen.close()
            pause()
        elif c == "5":
            servers = get_server_list()
            cams = get_camera_list()
            net_targets = load_json("network.json", default={"targets": []}).get("targets", [])
            targets = [{"label": s["name"], "ip": s["ip"]} for s in servers] + \
                      [{"label": c2["name"], "ip": c2["ip"]} for c2 in cams] + \
                      [{"label": t["name"], "ip": t["ip"]} for t in net_targets]
            if not targets:
                console.print("[dim]Belum ada target di servers.json / cctv.json / network.json[/dim]")
            else:
                show_results(ping_multiple(targets), module_name="NETWORK_PING", save_report=True)
            pause()
        elif c == "6":
            target = console.input("DNS server IP: ").strip()
            r = run_live_ping(target)
            log_action("NETWORK", "PING DNS", target, r.state)
            pause()
        elif c == "7":
            r = run_live_ping("8.8.8.8")
            log_action("NETWORK", "PING INTERNET", "8.8.8.8", r.state)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def routing_menu():
    while True:
        header("ROUTING")
        console.print("[01] Routing Table   [04] Default Route")
        console.print("[02] Traceroute        [05] Gateway Test")
        console.print("[03] Route Test")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results([routing_table()])
            pause()
        elif c == "2":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([check_route(target)])
            pause()
        elif c == "3":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([route_test(target)])
            pause()
        elif c == "4":
            show_results([default_route()])
            pause()
        elif c == "5":
            show_results([gateway_test()])
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def port_service_menu():
    while True:
        header("PORT / SERVICE")
        console.print("[01] TCP Port Test          [04] Port Scan")
        console.print("[02] UDP Test                 [05] Port Scan Range")
        console.print("[03] List Listening Ports     [06] Common Service Port Test")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            try:
                port = validate_port(console.input("Port: ").strip())
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([check_port(target, port)])
            pause()
        elif c == "2":
            console.print("[dim]UDP test terbatas: Windows tidak selalu balas UDP probe (silent drop = ambigu).[/dim]")
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            try:
                port = validate_port(console.input("Port: ").strip())
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([CheckResult(f"UDP {target}:{port}", "UNKNOWN", detail="UDP tidak bisa dipastikan open/closed tanpa listener aktif di sisi lain")])
            pause()
        elif c == "3":
            show_results([list_listening_ports()])
            pause()
        elif c == "4":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            ports_str = console.input("Ports (comma-separated, mis. 80,443,3389): ").strip()
            ports = [int(p.strip()) for p in ports_str.split(",") if p.strip().isdigit()]
            show_results(port_scan(target, ports), module_name="NETWORK_PORT", save_report=True)
            pause()
        elif c == "5":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            try:
                start = validate_port(console.input("Start port: ").strip())
                end = validate_port(console.input("End port (max 100 dari start): ").strip())
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(port_scan_range(target, start, end), module_name="NETWORK_PORT", save_report=True)
            pause()
        elif c == "6":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(common_service_port_test(target), module_name="NETWORK_PORT", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def dns_menu():
    while True:
        header("DNS")
        console.print("[01] DNS Lookup           [04] Flush DNS Cache")
        console.print("[02] Reverse Lookup        [05] Current DNS Configuration")
        console.print("[03] DNS Server Test")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            target = console.input("Hostname: ").strip()
            show_results([dns_lookup(target)])
            pause()
        elif c == "2":
            ip = console.input("IP: ").strip()
            show_results([reverse_lookup(ip)])
            pause()
        elif c == "3":
            show_results(dns_server_test())
            pause()
        elif c == "4":
            show_results([flush_dns()])
            pause()
        elif c == "5":
            show_results([current_dns_configuration()])
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def adapter_menu():
    while True:
        header("ADAPTER")
        console.print("[01] Adapter Status        [04] Disable Adapter")
        console.print("[02] Adapter Information     [05] Reset Adapter")
        console.print("[03] Enable Adapter            [06] Interface Statistics")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results(check_adapter())
            pause()
        elif c == "2":
            name = console.input("Adapter name: ").strip()
            show_results([adapter_information(name)])
            pause()
        elif c == "3":
            name = console.input("Adapter name: ").strip()
            if confirm(f"Enable adapter '{name}'?"):
                r = enable_adapter(name)
                show_results([r])
                log_action("NETWORK", "ENABLE ADAPTER", name, r.state)
            pause()
        elif c == "4":
            name = console.input("Adapter name: ").strip()
            if confirm(f"Disable adapter '{name}'? Ini akan memutus koneksi adapter tersebut."):
                r = disable_adapter(name)
                show_results([r])
                log_action("NETWORK", "DISABLE ADAPTER", name, r.state)
            pause()
        elif c == "5":
            name = console.input("Adapter name: ").strip()
            if confirm(f"Reset adapter '{name}' (disable lalu enable)?"):
                r = reset_adapter(name)
                show_results([r])
                log_action("NETWORK", "RESET ADAPTER", name, r.state)
            pause()
        elif c == "6":
            name = console.input("Adapter name: ").strip()
            show_results([interface_statistics(name)])
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def network_scan_menu():
    while True:
        header("NETWORK SCAN")
        console.print("[01] Scan Subnet           [04] Resolve Hostnames")
        console.print("[02] Scan IP Range            [05] Ping Sweep")
        console.print("[03] Discover Active Hosts      [06] Export Scan Result")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            subnet = console.input("Subnet CIDR (mis. 192.168.10.0/24): ").strip()
            console.print("[dim]Scanning... (bisa memakan waktu)[/dim]")
            show_results(scan_subnet(subnet), module_name="NETWORK_SCAN", save_report=True)
            pause()
        elif c == "2":
            subnet = console.input("Subnet CIDR: ").strip()
            console.print("[dim]Scanning...[/dim]")
            show_results(scan_subnet(subnet))
            pause()
        elif c == "3":
            subnet = console.input("Subnet CIDR: ").strip()
            console.print("[dim]Discovering active hosts (ping sweep)...[/dim]")
            show_results(ping_sweep(subnet), module_name="NETWORK_SCAN", save_report=True)
            pause()
        elif c == "4":
            ips_str = console.input("IPs (comma-separated): ").strip()
            for ip in [x.strip() for x in ips_str.split(",") if x.strip()]:
                show_results([reverse_lookup(ip)])
            pause()
        elif c == "5":
            subnet = console.input("Subnet CIDR: ").strip()
            show_results(ping_sweep(subnet), module_name="NETWORK_SCAN", save_report=True)
            pause()
        elif c == "6":
            console.print("[dim]Export otomatis: hasil scan sudah tersimpan di reports/ setiap kali scan dijalankan dengan opsi report.[/dim]")
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()




def network_tools_menu():
    """PRD §6.1 item [09] NETWORK TOOLS - utility jaringan ringan,
    terpisah dari TOOLS module standalone (§29) yang isinya launcher aplikasi."""
    from ..tools.utils import subnet_calculator, get_arp_table
    while True:
        header("NETWORK TOOLS")
        console.print("[01] Subnet Calculator      [03] Wake-on-LAN")
        console.print("[02] ARP Table")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            val = console.input("IP/CIDR (mis. 192.168.10.10/24): ").strip()
            show_results([subnet_calculator(val)]); pause()
        elif c == "2":
            show_results([get_arp_table()]); pause()
        elif c == "3":
            mac = console.input("MAC Address (mis. 00:11:22:33:44:55): ").strip()
            show_results([wake_on_lan(mac)]); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
