from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.logger import log_action
from ..core.validate import validate_ip, validate_free_text_for_shell, ValidationError
from . import diagnostics as d


def menu():
    while True:
        header("PRINTER")
        console.print("[01] List Printers          [09] Clear Print Queue")
        console.print("[02] Printer Status            [10] Restart Print Spooler")
        console.print("[03] Default Printer             [11] Printer Diagnostics")
        console.print("[04] Printer IP                    [12] Add Printer")
        console.print("[05] Ping Printer                    [13] Remove Printer")
        console.print("[06] Test Port                          [14] Printer Properties")
        console.print("[07] Print Test Page                       [15] Printer Report")
        console.print("[08] Print Queue                              [16] Configured Printers")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            printers = d.list_printers()
            if not printers:
                console.print("[dim]Tidak ada printer terdeteksi.[/dim]")
            for p in printers:
                console.print(f"- {p['name']} ({p['status']})")
            pause()
        elif c == "2":
            name = console.input("Printer name: ").strip()
            show_results([d.check_printer(name)], module_name="PRINTER", save_report=True); pause()
        elif c == "3":
            show_results([d.get_default_printer()])
            if confirm("Ubah default printer?"):
                name = console.input("Printer name: ").strip()
                show_results([d.set_default_printer(name)])
            pause()
        elif c == "4":
            name = console.input("Printer name: ").strip()
            show_results([d.printer_ip_info(name)]); pause()
        elif c == "5":
            ip = console.input("Printer IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.ping_printer(ip)]); pause()
        elif c == "6":
            ip = console.input("Printer IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            port_raw = console.input("Port (default 9100): ").strip()
            try:
                port = int(port_raw) if port_raw else 9100
                if not (1 <= port <= 65535):
                    raise ValueError()
            except ValueError:
                console.print(f"[red]Port tidak valid: '{port_raw}'[/red]")
                pause()
                continue
            show_results([d.test_printer_port(ip, port)]); pause()
        elif c == "7":
            name = console.input("Printer name: ").strip()
            if confirm(f"Print test page ke '{name}'?"):
                show_results([d.print_test_page(name)])
            pause()
        elif c == "8":
            name = console.input("Printer name: ").strip()
            show_results([d.check_print_queue(name)]); pause()
        elif c == "9":
            from ..maintenance.actions import clear_print_queue
            if confirm("Clear print queue (semua printer)?"):
                r = clear_print_queue()
                show_results([r])
                log_action("PRINTER", "CLEAR PRINT QUEUE", "LOCAL", r.state)
            pause()
        elif c == "10":
            if confirm("Restart Print Spooler?"):
                r = d.restart_print_spooler_local()
                show_results([r])
                log_action("PRINTER", "RESTART PRINT SPOOLER", "LOCAL", r.state)
            pause()
        elif c == "11":
            name = console.input("Printer name: ").strip()
            ip_raw = console.input("Printer IP (opsional, Enter untuk skip): ").strip()
            ip = None
            if ip_raw:
                try:
                    ip = validate_ip(ip_raw)
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]")
                    pause()
                    continue
            show_results(d.printer_diagnostics(name, ip), module_name="PRINTER", save_report=True); pause()
        elif c == "12":
            name = console.input("Printer name: ").strip()
            ip = console.input("Printer IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            driver = console.input("Driver name: ").strip()
            try:
                driver = validate_free_text_for_shell(driver, "Driver name")
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            if confirm(f"Tambah printer '{name}' @ {ip}?"):
                r = d.add_printer_ip(name, ip, driver)
                show_results([r])
                log_action("PRINTER", "ADD PRINTER", f"{name} @ {ip}", r.state)
            pause()
        elif c == "13":
            name = console.input("Printer name: ").strip()
            if confirm(f"Hapus printer '{name}'?"):
                r = d.remove_printer(name)
                show_results([r])
                log_action("PRINTER", "REMOVE PRINTER", name, r.state)
            pause()
        elif c == "14":
            name = console.input("Printer name: ").strip()
            show_results([d.printer_properties(name)]); pause()
        elif c == "15":
            from ..report.engine import printer_report
            txt_path, _, overall = printer_report()
            console.print(f"\n[bold]RESULT:[/bold] {overall}")
            console.print(f"[dim]Report saved: {txt_path}[/dim]")
            pause()
        elif c == "16":
            entries = d.get_configured_printers()
            if not entries:
                console.print("[dim]Belum ada printer di config/printers.json. Tambah lewat Settings > Printer List.[/dim]")
            else:
                show_results(d.diagnose_all_configured_printers(), module_name="PRINTER", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
