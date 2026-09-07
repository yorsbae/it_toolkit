from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.logger import log_action
from ..core.validate import validate_hostname_or_ip, ValidationError
from . import diagnostics as d


def menu():
    while True:
        header("SERVER")
        console.print("[01] Server Ping             [09] Remote Services")
        console.print("[02] RPC Test                   [10] Restart Server")
        console.print("[03] SMB Test                      [11] Shutdown Server")
        console.print("[04] WMI Test                         [12] Remote CMD")
        console.print("[05] WinRM Test                          [13] Remote PowerShell")
        console.print("[06] RDP Test                                [14] Server Information")
        console.print("[07] Server Port Scan                           [15] Server Diagnostics")
        console.print("[08] Server Services                                [16] Server Report")
        console.print("\n[17] Diagnose All Servers (config/servers.json)")
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
            from ..network.basic import ping_target
            show_results([ping_target(target)]); pause()
        elif c == "2":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.rpc_test(target)]); pause()
        elif c == "3":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.smb_test(target)]); pause()
        elif c == "4":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.wmi_test(target)]); pause()
        elif c == "5":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.winrm_test(target)]); pause()
        elif c == "6":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.rdp_test(target)]); pause()
        elif c == "7":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(d.server_port_scan(target)); pause()
        elif c == "8":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(d.server_services(target)); pause()
        elif c == "9":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.remote_services(target)]); pause()
        elif c == "10":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            console.print("\n[bold]REMOTE SERVER RESTART[/bold]")
            console.print(f"Target : {target}\n")
            console.print("[yellow]WARNING: Active sessions may be disconnected.[/yellow]")
            if confirm("Continue?"):
                r = d.restart_server(target)
                show_results([r])
                log_action("SERVER", "RESTART SERVER", target, r.state)
            pause()
        elif c == "11":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            console.print("\n[bold]REMOTE SERVER SHUTDOWN[/bold]")
            console.print(f"Target : {target}\n")
            console.print("[yellow]WARNING: Active sessions may be disconnected.[/yellow]")
            if confirm("Continue?"):
                r = d.shutdown_server(target)
                show_results([r])
                log_action("SERVER", "SHUTDOWN SERVER", target, r.state)
            pause()
        elif c == "12":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            cmd = console.input("Command: ").strip()
            r = d.remote_cmd(target, cmd)
            show_results([r])
            log_action("SERVER", f"REMOTE CMD: {cmd}", target, r.state)
            pause()
        elif c == "13":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            cmd = console.input("Command: ").strip()
            r = d.remote_powershell(target, cmd)
            show_results([r])
            log_action("SERVER", f"REMOTE POWERSHELL: {cmd}", target, r.state)
            pause()
        elif c == "14":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results([d.server_information(target)]); pause()
        elif c == "15":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                pause()
                continue
            show_results(d.server_diagnostics(target), module_name="SERVER", save_report=True); pause()
        elif c == "16":
            from ..report.engine import server_report
            txt_path, _, overall = server_report()
            console.print(f"\n[bold]RESULT:[/bold] {overall}")
            console.print(f"[dim]Report saved: {txt_path}[/dim]")
            pause()
        elif c == "17":
            servers = d.get_server_list()
            if not servers:
                console.print("[dim]Belum ada server di config/servers.json[/dim]")
            else:
                show_results(d.diagnose_all_servers(), module_name="SERVER", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
