from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.logger import log_action
from ..core.validate import validate_ip, ValidationError
from . import manager as d


def menu():
    while True:
        header("SETTINGS")
        console.print("[01] General Settings        [07] Report Settings")
        console.print("[02] Network Targets            [08] Logging")
        console.print("[03] Server List                   [09] Theme")
        console.print("[04] Printer List                     [10] Reset Configuration")
        console.print("[05] CCTV List                           [11] About")
        console.print("[06] Custom Commands")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            cfg = d.general_settings()
            for k, v in cfg.items():
                console.print(f"{k}: {v}")
            if confirm("\nUbah technician_name?"):
                name = console.input("Technician name baru: ").strip()
                r = d.update_general_setting("technician_name", name)
                show_results([r])
                log_action("SETTINGS", "UPDATE TECHNICIAN NAME", name, r.state)
            pause()
        elif c == "2":
            targets = d.network_targets()
            for t in targets:
                console.print(f"- {t['name']}: {t['ip']}")
            if confirm("Tambah target baru?"):
                name = console.input("Name: ").strip()
                ip = console.input("IP: ").strip()
                try:
                    ip = validate_ip(ip)
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]"); pause(); continue
                r = d.add_network_target(name, ip)
                show_results([r])
                log_action("SETTINGS", "ADD NETWORK TARGET", f"{name} ({ip})", r.state)
            pause()
        elif c == "3":
            servers = d.server_list()
            for s in servers:
                console.print(f"- {s['name']}: {s['ip']} (ports: {s.get('ports')})")
            console.print("\n[1] Add Server  [2] Remove Server  [0] Back")
            sub = console.input("> ").strip()
            if sub == "1":
                name = console.input("Name: ").strip()
                ip = console.input("IP: ").strip()
                try:
                    ip = validate_ip(ip)
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]"); pause(); continue
                ports_str = console.input("Ports (comma-separated): ").strip()
                ports = [int(p.strip()) for p in ports_str.split(",") if p.strip().isdigit()]
                r = d.add_server(name, ip, ports)
                show_results([r])
                log_action("SETTINGS", "ADD SERVER", f"{name} ({ip})", r.state)
            elif sub == "2":
                name = console.input("Name to remove: ").strip()
                if confirm(f"Hapus server '{name}'?"):
                    r = d.remove_server(name)
                    show_results([r])
                    log_action("SETTINGS", "REMOVE SERVER", name, r.state)
            pause()
        elif c == "4":
            printers = d.printer_list()
            for p in printers:
                console.print(f"- {p['name']}: {p.get('ip', '-')}")
            if confirm("Tambah printer entry baru?"):
                name = console.input("Name: ").strip()
                ip = console.input("IP: ").strip()
                try:
                    ip = validate_ip(ip)
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]"); pause(); continue
                r = d.add_printer_entry(name, ip)
                show_results([r])
                log_action("SETTINGS", "ADD PRINTER ENTRY", f"{name} ({ip})", r.state)
            pause()
        elif c == "5":
            cams = d.cctv_list()
            for cam in cams:
                console.print(f"- {cam.get('name') or '(no label)'}: {cam['ip']}")
            console.print("[dim]Gunakan menu CCTV > Camera IP Scan untuk menambah & melabeli kamera.[/dim]")
            pause()
        elif c == "6":
            cmds = d.custom_commands_settings()
            for cmd in cmds:
                console.print(f"- [{cmd['id']}] {cmd['name']} ({cmd.get('type', '-')})")
            console.print("[dim]Gunakan menu Custom untuk Add/Edit/Delete.[/dim]")
            pause()
        elif c == "7":
            settings = d.report_settings()
            console.print(f"Report formats: {settings['formats']}")
            pause()
        elif c == "8":
            settings = d.logging_settings()
            console.print(f"Log level: {settings['log_level']}")
            if confirm("Ubah log level?"):
                level = console.input("Level baru (INFO/DEBUG/WARNING): ").strip().upper()
                r = d.update_log_level(level)
                show_results([r])
                log_action("SETTINGS", "UPDATE LOG LEVEL", level, r.state)
            pause()
        elif c == "9":
            from ..core.theme import available_themes
            theme = d.theme_settings()
            console.print(f"Current theme: {theme}")
            console.print(f"[dim]Pilihan: {', '.join(available_themes())}[/dim]")
            if confirm("Ubah theme?"):
                new_theme = console.input("Theme baru: ").strip()
                r = d.update_theme(new_theme)
                show_results([r])
                log_action("SETTINGS", "UPDATE THEME", new_theme, r.state)
            pause()
        elif c == "10":
            console.print("[yellow]WARNING: config.json akan dikembalikan ke default.[/yellow]")
            console.print("[dim](servers/printers/cctv/custom_commands TIDAK terhapus)[/dim]")
            if confirm("Lanjutkan reset?"):
                r = d.reset_configuration()
                show_results([r])
                log_action("SETTINGS", "RESET CONFIGURATION", "config.json", r.state)
            pause()
        elif c == "11":
            about = d.about()
            for k, v in about.items():
                console.print(f"{k}: {v}")
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
