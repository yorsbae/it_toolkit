from ..core.ui import console, header, show_results, pause, read_choice, confirm
from ..core.logger import log_action
from ..core.validate import validate_hostname_or_ip, ValidationError
from . import launcher as d


def menu():
    while True:
        header("REMOTE")
        console.print("[01] RDP                    [07] Remote Task Manager")
        console.print("[02] Remote CMD               [08] Remote Registry")
        console.print("[03] Remote PowerShell          [09] AnyDesk")
        console.print("[04] Computer Management          [10] TeamViewer")
        console.print("[05] Remote Services                 [11] Quick Assist")
        console.print("[06] Remote Event Viewer               [12] Remote Diagnostic")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            target = console.input("Target host/IP: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.launch_rdp(target)]); pause()
        elif c == "2":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            cmd = console.input("Command: ").strip()
            console.print(f"\nTarget  : {target}\nCommand : {cmd}\n")
            if confirm("Jalankan command ini di server remote?"):
                r = d.remote_cmd(target, cmd)
                show_results([r])
                log_action("REMOTE", f"REMOTE CMD: {cmd}", target, r.state)
            pause()
        elif c == "3":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            cmd = console.input("Command: ").strip()
            console.print(f"\nTarget  : {target}\nCommand : {cmd}\n")
            if confirm("Jalankan command ini di server remote?"):
                r = d.remote_powershell(target, cmd)
                show_results([r])
                log_action("REMOTE", f"REMOTE POWERSHELL: {cmd}", target, r.state)
            pause()
        elif c == "4":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.open_computer_management(target)]); pause()
        elif c == "5":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.remote_services(target)]); pause()
        elif c == "6":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.remote_event_viewer(target)]); pause()
        elif c == "7":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.remote_task_manager(target)]); pause()
        elif c == "8":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.remote_registry(target)]); pause()
        elif c == "9":
            target_id = console.input("AnyDesk ID (opsional): ").strip()
            show_results([d.launch_anydesk(target_id)]); pause()
        elif c == "10":
            show_results([d.launch_teamviewer()]); pause()
        elif c == "11":
            show_results([d.launch_quick_assist()]); pause()
        elif c == "12":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results(d.remote_diagnostic(target)); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
