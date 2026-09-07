from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.report import generate_report
from ..core.logger import log_action
from ..core.validate import validate_unc_path, validate_hostname_or_ip, validate_drive_letter, ValidationError
from . import diagnostics as d
from . import folder as f
from . import printer_share as ps
from . import error_codes as ec


def menu():
    while True:
        header("SHARING")
        console.print("[bold]QUICK DIAGNOSTIC[/bold]")
        console.print("[01] Full Sharing Diagnostic")
        console.print("[02] Diagnose Folder Share")
        console.print("[03] Diagnose Printer Share")
        console.print("[04] Diagnose by Error Code")
        console.print()
        console.print("[bold]COMMON WINDOWS CONFIGURATION[/bold]")
        console.print("[05] Network Discovery          [09] Firewall Sharing Rules")
        console.print("[06] File & Printer Sharing        [10] Credential Manager")
        console.print("[07] Network Profile                  [11] Password Protected Sharing")
        console.print("[08] SMB Configuration                    [12] SMB Protocol / Guest Access")
        console.print()
        console.print("[bold]SERVICES[/bold]")
        console.print("[13] Check RPC                      [16] Check Workstation Service")
        console.print("[14] Check RPC Endpoint Mapper          [17] Check Print Spooler")
        console.print("[15] Check Server Service                  [18] Check Spooler Dependencies")
        console.print()
        console.print("[bold]REPAIR[/bold]")
        console.print("[19] Restart Sharing Services      [22] Reset Sharing Configuration")
        console.print("[20] Restart Print Spooler            [23] Clear Saved Credentials")
        console.print("[21] Restart Server")
        console.print()
        console.print("[bold]REGISTRY / POLICY[/bold]")
        console.print("[24] Check RPC Configuration       [27] Check Anonymous/IPC$ Access")
        console.print("[25] RPC Registry Fix                 [28] Registry Backup")
        console.print("[26] Check Point & Print Policy")
        console.print()
        console.print("[bold]FOLDER[/bold]")
        console.print("[29] List Shared Folders        [32] Map Network Drive")
        console.print("[30] Test Folder Share             [33] Disconnect Network Drive")
        console.print("[31] Test Effective Permission")
        console.print()
        console.print("[bold]PRINTER[/bold]")
        console.print("[34] List Shared Printers        [38] Check Printer Permission")
        console.print("[35] Test Printer Share             [39] Check Driver Store / Package")
        console.print("[36] Connect Shared Printer            [40] Clear Print Queue")
        console.print("[37] Test Printer Port")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            results = d.full_diagnostic_extended()
            show_results(results)

            issues = [r for r in results if r.state in ("FAIL", "WARN") and r.label in d._remediation_registry()]
            if issues:
                console.print(f"\n[yellow]{len(issues)} item bermasalah punya fix tersedia.[/yellow]")
                if confirm("Tinjau & perbaiki satu per satu sekarang?"):
                    fix_results = d.guided_remediation(results, confirm, show_results)
                    results = results + fix_results

            txt_path, _, overall = generate_report("SHARING", [r for r in results if hasattr(r, "state")])
            console.print(f"\n[bold]RESULT:[/bold] {overall}")
            console.print(f"[dim]Report saved: {txt_path}[/dim]")

            console.print("\n[bold]What are you troubleshooting?[/bold]")
            console.print("[1] Folder Share  [2] Printer Share  [3] Both  [0] None")
            sub = console.input("> ").strip()
            if sub == "1":
                folder_share_menu()
            elif sub == "2":
                printer_share_menu()
            elif sub == "3":
                folder_share_menu()
                printer_share_menu()
            else:
                pause()
        elif c == "2":
            folder_share_menu()
        elif c == "3":
            printer_share_menu()
        elif c == "4":
            error_code_menu()
        elif c == "5":
            show_results([d.check_network_discovery()]); pause()
        elif c == "6":
            show_results([d.check_firewall_rule_group()]); pause()
        elif c == "7":
            show_results([d.check_network_profile()]); pause()
        elif c == "8":
            show_results([d.check_smb_config()]); pause()
        elif c == "9":
            show_results([d.check_firewall_sharing_rules()]); pause()
        elif c == "10":
            show_results([d.check_credential_manager()]); pause()
        elif c == "11":
            show_results([d.check_password_protected_sharing()]); pause()
        elif c == "12":
            show_results([d.check_smb_guest_access()]); pause()
        elif c == "13":
            show_results([d.check_service_state("RpcSs", "RPC")]); pause()
        elif c == "14":
            target = console.input("Target (Enter untuk localhost): ").strip() or "127.0.0.1"
            show_results([d.check_rpc_endpoint_mapper(target)]); pause()
        elif c == "15":
            show_results([d.check_service_state("LanmanServer", "Server (File/Printer Sharing)")]); pause()
        elif c == "16":
            show_results([d.check_service_state("LanmanWorkstation", "Workstation")]); pause()
        elif c == "17":
            show_results([d.check_service_state("Spooler", "Print Spooler")]); pause()
        elif c == "18":
            show_results([d.check_spooler_dependencies()]); pause()
        elif c == "19":
            if confirm("Restart semua Sharing Services (Server/Workstation/RPC/Spooler)?"):
                results = d.restart_sharing_services()
                show_results(results)
                overall_state = "FAIL" if any(r.state == "FAIL" for r in results) else "PASS"
                log_action("SHARING", "RESTART SHARING SERVICES", "LOCAL", overall_state)
            pause()
        elif c == "20":
            if confirm("Restart Print Spooler?"):
                r = d.fix_restart_service("Spooler")
                show_results([r])
                log_action("SHARING", "RESTART PRINT SPOOLER", "LOCAL", r.state)
            pause()
        elif c == "21":
            target = console.input("Server: ").strip()
            if confirm(f"RESTART server '{target}'? Active session bisa terputus."):
                from ..server.diagnostics import restart_server
                r = restart_server(target)
                show_results([r])
                log_action("SHARING", "RESTART SERVER", target, r.state)
            pause()
        elif c == "22":
            if confirm("Reset firewall rules sharing ke enabled?"):
                r = d.reset_sharing_configuration()
                show_results([r])
                log_action("SHARING", "RESET SHARING CONFIGURATION", "LOCAL", r.state)
            pause()
        elif c == "23":
            target = console.input("Target credential (kosongkan untuk lihat daftar dulu): ").strip()
            r = d.clear_saved_credentials(target or None)
            show_results([r])
            if target:
                log_action("SHARING", "CLEAR SAVED CREDENTIALS", target, r.state)
            pause()
        elif c == "24":
            show_results([d.check_rpc_configuration()]); pause()
        elif c == "25":
            console.print("[yellow]WARNING: Operasi ini mengubah Windows Registry.[/yellow]")
            if confirm("Buat Registry Backup dulu"):
                if confirm("Lanjutkan apply RPC Registry Fix?"):
                    results = d.rpc_registry_fix(confirm_backup=True)
                    show_results(results)
                    overall_state = "FAIL" if any(r.state == "FAIL" for r in results) else "PASS"
                    log_action("SHARING", "RPC REGISTRY FIX", "LOCAL", overall_state)
            else:
                if confirm("Lanjutkan TANPA backup?"):
                    results = d.rpc_registry_fix(confirm_backup=False)
                    show_results(results)
                    overall_state = "FAIL" if any(r.state == "FAIL" for r in results) else "PASS"
                    log_action("SHARING", "RPC REGISTRY FIX (NO BACKUP)", "LOCAL", overall_state)
            pause()
        elif c == "26":
            show_results([d.check_point_and_print_policy()]); pause()
        elif c == "27":
            show_results([d.check_anonymous_ipc_access()]); pause()
        elif c == "28":
            key_path = console.input(r"Registry key path (mis. HKLM\SOFTWARE\...): ").strip()
            backup_name = console.input("Nama file backup: ").strip()
            show_results([d.registry_backup(key_path, backup_name)]); pause()
        elif c == "29":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([f.list_shared_folders(server)]); pause()
        elif c == "30":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(f.test_share(unc)); pause()
        elif c == "31":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            user = console.input("User/Group (default Everyone): ").strip() or "Everyone"
            show_results([f.test_effective_permission(unc, user)]); pause()
        elif c == "32":
            letter = console.input("Drive letter (mis. Z): ").strip().rstrip(":")
            try:
                letter = validate_drive_letter(letter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            unc = console.input(r"UNC path (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Map {letter}: -> {unc}?"):
                r = f.map_network_drive(letter, unc)
                show_results([r])
                log_action("SHARING", "MAP NETWORK DRIVE", f"{letter}: -> {unc}", r.state)
            pause()
        elif c == "33":
            letter = console.input("Drive letter: ").strip().rstrip(":")
            try:
                letter = validate_drive_letter(letter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Disconnect {letter}:?"):
                r = f.disconnect_network_drive(letter)
                show_results([r])
                log_action("SHARING", "DISCONNECT NETWORK DRIVE", f"{letter}:", r.state)
            pause()
        elif c == "34":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ps.list_shared_printers(server)]); pause()
        elif c == "35":
            unc = console.input(r"Target (\\SERVER\Printer): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(ps.test_printer_share(unc)); pause()
        elif c == "36":
            unc = console.input(r"Target (\\SERVER\Printer): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Connect ke {unc}?"):
                r = ps.connect_shared_printer(unc)
                show_results([r])
                log_action("SHARING", "CONNECT SHARED PRINTER", unc, r.state)
            pause()
        elif c == "37":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ps.test_printer_port(server)]); pause()
        elif c == "38":
            name = console.input("Printer name (local): ").strip()
            show_results([ps.check_printer_permission(name)]); pause()
        elif c == "39":
            show_results([ps.check_driver_store()]); pause()
        elif c == "40":
            from ..maintenance.actions import clear_print_queue
            if confirm("Clear print queue?"):
                r = clear_print_queue()
                show_results([r])
                log_action("SHARING", "CLEAR PRINT QUEUE", "LOCAL", r.state)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def windows_configuration_menu():
    while True:
        header("SHARING > WINDOWS CONFIGURATION")
        console.print("[01] Network Discovery       [05] SMB Guest Access")
        console.print("[02] File & Printer Sharing    [06] Password Protected Sharing")
        console.print("[03] Network Profile              [07] Credential Manager")
        console.print("[04] SMB Configuration")
        console.print("\n[00] BACK\n")
        c = read_choice()

        checks = {
            "1": d.check_network_discovery, "2": d.check_firewall_rule_group,
            "3": d.check_network_profile, "4": d.check_smb_config,
            "5": d.check_smb_guest_access, "6": d.check_password_protected_sharing,
            "7": d.check_credential_manager,
        }
        if c in checks:
            show_results([checks[c]()]); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def registry_policy_menu():
    while True:
        header("SHARING > REGISTRY / POLICY")
        console.print("[01] Check RPC Configuration     [03] Check Point & Print Policy")
        console.print("[02] Apply RPC Registry Fix         [04] Check Anonymous/IPC$ Access")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results([d.check_rpc_configuration()]); pause()
        elif c == "2":
            console.print("[yellow]WARNING: Operasi ini mengubah Windows Registry.[/yellow]")
            if confirm("Buat Registry Backup dulu"):
                if confirm("Lanjutkan apply RPC Registry Fix?"):
                    show_results(d.rpc_registry_fix(confirm_backup=True))
            else:
                if confirm("Lanjutkan TANPA backup?"):
                    show_results(d.rpc_registry_fix(confirm_backup=False))
            pause()
        elif c == "3":
            show_results([d.check_point_and_print_policy()]); pause()
        elif c == "4":
            show_results([d.check_anonymous_ipc_access()]); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def folder_share_menu():
    while True:
        header("FOLDER SHARE")
        console.print("[01] Full Check              [06] Map Network Drive")
        console.print("[02] List Shared Folders       [07] Disconnect Network Drive")
        console.print("[03] Test Share                  [08] Open Folder")
        console.print("[04] Test Permission                [09] Diagnose Access Denied")
        console.print("[05] Test Effective Permission        [10] Diagnose Unavailable Share")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(f.folder_share_full_check(unc), module_name="SHARING_FOLDER", save_report=True); pause()
        elif c == "2":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([f.list_shared_folders(server)]); pause()
        elif c == "3":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(f.test_share(unc)); pause()
        elif c == "4":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([f.test_share_permission(unc)]); pause()
        elif c == "5":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            user = console.input("User/Group (default Everyone): ").strip() or "Everyone"
            show_results([f.test_effective_permission(unc, user)]); pause()
        elif c == "6":
            letter = console.input("Drive letter (mis. Z): ").strip().rstrip(":")
            try:
                letter = validate_drive_letter(letter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            unc = console.input(r"UNC path (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Map {letter}: -> {unc}?"):
                show_results([f.map_network_drive(letter, unc)])
            pause()
        elif c == "7":
            letter = console.input("Drive letter: ").strip().rstrip(":")
            try:
                letter = validate_drive_letter(letter)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Disconnect {letter}:?"):
                show_results([f.disconnect_network_drive(letter)])
            pause()
        elif c == "8":
            unc = console.input(r"UNC path: ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([f.open_folder(unc)]); pause()
        elif c == "9":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(f.diagnose_access_denied(unc)); pause()
        elif c == "10":
            unc = console.input(r"Target (\\SERVER\Share): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(f.diagnose_unavailable_share(unc)); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def printer_share_menu():
    while True:
        header("PRINTER SHARE")
        console.print("[01] Full Check                 [06] Print Test Page")
        console.print("[02] List Shared Printers          [07] Clear Queue")
        console.print("[03] Test Printer Share               [08] Restart Spooler")
        console.print("[04] Connect Shared Printer              [09] Check Driver")
        console.print("[05] Test Printer Port                      [10] Diagnose RPC")
        console.print("                                               [11] Printer Permission")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            unc = console.input(r"Target (\\SERVER\Printer): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(ps.printer_share_full_check(unc), module_name="SHARING_PRINTER", save_report=True); pause()
        elif c == "2":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ps.list_shared_printers(server)]); pause()
        elif c == "3":
            unc = console.input(r"Target (\\SERVER\Printer): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(ps.test_printer_share(unc)); pause()
        elif c == "4":
            unc = console.input(r"Target (\\SERVER\Printer): ").strip()
            try:
                unc = validate_unc_path(unc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            if confirm(f"Connect ke {unc}?"):
                show_results([ps.connect_shared_printer(unc)])
            pause()
        elif c == "5":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ps.test_printer_port(server)]); pause()
        elif c == "6":
            from ..printer.diagnostics import print_test_page
            name = console.input("Printer name (local): ").strip()
            if confirm(f"Print test page ke '{name}'?"):
                show_results([print_test_page(name)])
            pause()
        elif c == "7":
            from ..maintenance.actions import clear_print_queue
            if confirm("Clear print queue?"):
                show_results([clear_print_queue()])
            pause()
        elif c == "8":
            from ..sharing.diagnostics import fix_restart_service
            if confirm("Restart Print Spooler?"):
                show_results([fix_restart_service("Spooler")])
            pause()
        elif c == "9":
            show_results([ps.check_driver_store()]); pause()
        elif c == "10":
            server = console.input("Server: ").strip()
            try:
                server = validate_hostname_or_ip(server)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([ps.diagnose_rpc(server)]); pause()
        elif c == "11":
            name = console.input("Printer name (local): ").strip()
            show_results([ps.check_printer_permission(name)]); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def error_code_menu():
    while True:
        header("DIAGNOSE BY ERROR CODE")
        codes = ec.list_error_codes()
        for i, code in enumerate(codes, 1):
            console.print(f"[{i:02}] {code}")
        console.print("\n[00] BACK\n")
        c = read_choice()
        if c == "0":
            return
        try:
            idx = int(c) - 1
            code = codes[idx]
        except (ValueError, IndexError):
            console.print("[red]Invalid option[/red]"); pause(); continue

        target = console.input("Target server (opsional, Enter untuk skip): ").strip() or None
        info, checks = ec.diagnose_error_code(code, target)
        console.print(f"\n[bold]ERROR: {code}[/bold]")
        console.print(f"[bold]CATEGORY:[/bold] {info['category']}")
        console.print(f"{info['description']}\n")
        show_results(checks)

        console.print("\n[bold]POSSIBLE ACTIONS:[/bold]")
        actions = ec.possible_actions_menu_labels()
        for i, a in enumerate(actions, 1):
            console.print(f"[{i}] {a}")
        console.print("[0] BACK")
        action = console.input("> ").strip()
        if action == "1":
            show_results([d.check_rpc_configuration()])
        elif action == "2":
            if confirm("Apply Registry Configuration (RPC fix)?"):
                show_results(d.rpc_registry_fix())
        elif action == "3":
            if confirm("Restart Print Spooler?"):
                show_results([d.fix_restart_service("Spooler")])
        elif action == "4" and target:
            from ..server.diagnostics import restart_server
            if confirm(f"Restart server {target}?"):
                show_results([restart_server(target)])
        elif action == "6":
            show_results(d.full_diagnostic_extended(), module_name="SHARING", save_report=True)
        pause()
