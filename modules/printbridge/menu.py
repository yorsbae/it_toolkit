"""
Print Bridge - Menu
======================
Satu modul, DUA peran, dijalankan dari PC mana pun (toolkit ini portable):
  [01] Start Print Server  - jalankan di PC yang printernya sudah terpasang.
  [02] Print via Server    - jalankan di PC LAIN untuk kirim file ke server
                              di atas, TANPA install driver printer apa pun.
"""

import os
import time
from datetime import datetime

from ..core.ui import console, header, pause, read_choice
from ..core.logger import log_action
from ..core.config import load_json, save_json
from ..core.validate import validate_hostname_or_ip, validate_port, ValidationError
from . import server as srv
from . import client as cli

CONFIG_FILE = "print_servers.json"
DEFAULT_PORT = 9600


# --------------------------------------------------------------- Storage --

def get_servers() -> list:
    return load_json(CONFIG_FILE, default={"servers": []}).get("servers", [])


def save_servers(servers: list) -> None:
    save_json(CONFIG_FILE, {"servers": servers})


# ------------------------------------------------------------------ Menu --

def menu():
    while True:
        header("PRINT BRIDGE")
        console.print("[dim]Cetak lintas PC tanpa install driver printer di client - "
                       "client cukup connect ke PC yang jadi server.[/dim]\n")
        console.print("[01] Start Print Server (Host printer PC ini)")
        console.print("[02] Print a File via Server (Client)")
        console.print("[03] Test Connection to Server")
        console.print("[04] Manage Known Servers")
        console.print("[05] View Local Spool Folder")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            _start_server_flow()
        elif c == "2":
            _client_print_flow()
        elif c == "3":
            _test_connection_flow()
        elif c == "4":
            _manage_servers_flow()
        elif c == "5":
            _view_spool_flow()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


# -------------------------------------------------------------- Server --

def _start_server_flow():
    header("PRINT BRIDGE > START SERVER")
    port_raw = console.input(f"Port [{DEFAULT_PORT}]: ").strip() or str(DEFAULT_PORT)
    try:
        port = validate_port(port_raw)
    except ValidationError as e:
        console.print(f"[red]{e}[/red]"); pause(); return

    printer_name = console.input("Target printer (kosongkan = default printer PC ini): ").strip() or None

    hostname = os.environ.get("COMPUTERNAME") or _safe_hostname()
    local_ip = srv.local_ip_guess()
    job_count = {"n": 0}

    def on_job(sender, filename, size, printer, status, detail):
        job_count["n"] += 1
        color = "green" if status == "PRINTED" else "red"
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(
            f"[dim]{ts}[/dim] [bold]{sender}[/bold] -> {filename} "
            f"({size / 1024:.0f} KB) [{color}]{status}[/{color}] - {detail}"
        )
        log_action("PRINT BRIDGE", "JOB RECEIVED", f"{sender}: {filename}", status)

    try:
        server, thread = srv.start_server(host="0.0.0.0", port=port, on_job=on_job)
    except OSError as e:
        console.print(f"[red]Gagal start server di port {port}: {e}[/red]")
        console.print("[dim]Kemungkinan port sudah dipakai, atau butuh izin admin/firewall.[/dim]")
        pause(); return

    console.print("\n[green]Print Bridge Server AKTIF[/green]")
    console.print(f"Host    : {hostname} ({local_ip})")
    console.print(f"Port    : {port}")
    console.print(f"Printer : {printer_name or '(default printer PC ini)'}")
    console.print(f"\n[dim]Client lain: pilih [02] Print a File via Server, lalu masukkan "
                   f"{local_ip}:{port}. Ctrl+C untuk stop server.[/dim]\n")
    log_action("PRINT BRIDGE", "SERVER START", f"{local_ip}:{port}", "SUCCESS")

    try:
        while thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        console.print()
    finally:
        srv.stop_server(server)
        console.print(f"[yellow]Server dihentikan. Total job diterima: {job_count['n']}[/yellow]")
        log_action("PRINT BRIDGE", "SERVER STOP", f"{local_ip}:{port}", "SUCCESS")
    pause()


def _safe_hostname() -> str:
    import socket
    try:
        return socket.gethostname()
    except Exception:
        return "PC"


# -------------------------------------------------------------- Client --

def _pick_server():
    servers = get_servers()
    if servers:
        console.print("Server tersimpan:")
        for i, s in enumerate(servers, 1):
            console.print(f"  [{i}] {s['name']} - {s['ip']}:{s['port']}")
        console.print("  [M] Input manual\n")
        sel = console.input("Pilih nomor / M: ").strip().upper()
        if sel != "M":
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(servers):
                    return servers[idx]["ip"], servers[idx]["port"]
            except ValueError:
                pass
            console.print("[red]Pilihan tidak valid, lanjut input manual.[/red]")

    ip = console.input("Server IP/hostname: ").strip()
    try:
        ip = validate_hostname_or_ip(ip)
    except ValidationError as e:
        console.print(f"[red]{e}[/red]")
        return None, None
    port_raw = console.input(f"Server Port [{DEFAULT_PORT}]: ").strip() or str(DEFAULT_PORT)
    try:
        port = validate_port(port_raw)
    except ValidationError as e:
        console.print(f"[red]{e}[/red]")
        return None, None
    return ip, port


def _client_print_flow():
    header("PRINT BRIDGE > PRINT VIA SERVER (CLIENT)")
    ip, port = _pick_server()
    if not ip:
        pause(); return

    filepath = console.input(r"Path file yang mau dicetak (mis. C:\Users\budi\Report.pdf): ").strip().strip('"')
    if not os.path.isfile(filepath):
        console.print(f"[red]File tidak ditemukan: {filepath}[/red]")
        pause(); return

    printer = console.input("Target printer di server (kosongkan = default): ").strip() or None

    console.print(f"\n[dim]Mengirim {os.path.basename(filepath)} ke {ip}:{port} ...[/dim]")
    ok, detail = cli.send_file(ip, port, filepath, printer=printer)
    if ok:
        console.print(f"[green][\u2713] PRINTED - {detail}[/green]")
    else:
        console.print(f"[red][\u2717] FAILED - {detail}[/red]")
    log_action(
        "PRINT BRIDGE", "CLIENT PRINT", f"{ip}:{port} <- {os.path.basename(filepath)}",
        "SUCCESS" if ok else "FAILED",
    )
    pause()


def _test_connection_flow():
    header("PRINT BRIDGE > TEST CONNECTION")
    ip, port = _pick_server()
    if not ip:
        pause(); return
    ok, detail = cli.test_connection(ip, port)
    color = "green" if ok else "red"
    sym = "[\u2713]" if ok else "[\u2717]"
    console.print(f"[{color}]{sym} {ip}:{port} - {detail}[/{color}]")
    pause()


def _manage_servers_flow():
    while True:
        header("PRINT BRIDGE > MANAGE KNOWN SERVERS")
        servers = get_servers()
        if not servers:
            console.print("[dim]Belum ada server tersimpan.[/dim]\n")
        else:
            for i, s in enumerate(servers, 1):
                console.print(f"[{i}] {s['name']} - {s['ip']}:{s['port']}")
            console.print()
        console.print("[1] Add Server   [2] Remove Server   [0] Back")
        sub = read_choice()
        if sub == "1":
            name = console.input("Name: ").strip()
            ip = console.input("IP/hostname: ").strip()
            try:
                ip = validate_hostname_or_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            port_raw = console.input(f"Port [{DEFAULT_PORT}]: ").strip() or str(DEFAULT_PORT)
            try:
                port = validate_port(port_raw)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            servers = get_servers()
            servers.append({"name": name or ip, "ip": ip, "port": port})
            save_servers(servers)
            console.print("[green]Server ditambahkan.[/green]")
            log_action("PRINT BRIDGE", "ADD SERVER", f"{name} ({ip}:{port})", "SUCCESS")
            pause()
        elif sub == "2":
            if not servers:
                pause(); continue
            idx_raw = console.input("Nomor server yang mau dihapus: ").strip()
            try:
                idx = int(idx_raw) - 1
            except ValueError:
                console.print("[red]Input harus angka.[/red]"); pause(); continue
            if 0 <= idx < len(servers):
                removed = servers.pop(idx)
                save_servers(servers)
                console.print(f"[green]Dihapus: {removed['name']}[/green]")
                log_action("PRINT BRIDGE", "REMOVE SERVER", removed["name"], "SUCCESS")
            else:
                console.print("[red]Nomor tidak valid.[/red]")
            pause()
        elif sub == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def _view_spool_flow():
    header("PRINT BRIDGE > LOCAL SPOOL FOLDER")
    files = sorted(srv.SPOOL_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        console.print("[dim]Spool folder kosong.[/dim]")
    else:
        console.print(f"Folder: {srv.SPOOL_DIR}\n")
        for f in files[:50]:
            size_kb = f.stat().st_size / 1024
            console.print(f"  {f.name}  ({size_kb:.0f} KB)")
    pause()
