from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.logger import log_action
from ..core.validate import validate_service_name, ValidationError
from . import diagnostics as d


def menu():
    while True:
        header("WINDOWS")
        console.print("[01] System Info          [09] Installed Programs")
        console.print("[02] Task Manager          [10] Local Users")
        console.print("[03] Device Manager         [11] Environment Variables")
        console.print("[04] Services                [12] Windows Firewall")
        console.print("[05] Event Viewer              [13] Windows Update")
        console.print("[06] Computer Management         [14] Hosts File")
        console.print("[07] Disk Management                [15] System Properties")
        console.print("[08] Network Connections               [16] Group Policy")
        console.print("                                          [17] Check Service")
        console.print("                                          [18] SFC /scannow")
        console.print("                                          [19] DISM RestoreHealth")
        console.print("                                          [20] CHKDSK")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            info = d.get_system_info()
            for k, v in list(info.items())[:15]:
                console.print(f"{k}: {v}")
            pause()
        elif c == "2":
            show_results([d.open_task_manager()]); pause()
        elif c == "3":
            show_results([d.open_device_manager()]); pause()
        elif c == "4":
            show_results([d.list_services()]); pause()
        elif c == "5":
            show_results([d.open_event_viewer()]); pause()
        elif c == "6":
            show_results([d.open_computer_management()]); pause()
        elif c == "7":
            show_results([d.open_disk_management()]); pause()
        elif c == "8":
            show_results([d.open_network_connections()]); pause()
        elif c == "9":
            show_results([d.list_installed_programs()]); pause()
        elif c == "10":
            show_results([d.list_local_users()]); pause()
        elif c == "11":
            show_results([d.list_environment_variables()]); pause()
        elif c == "12":
            show_results([d.open_windows_firewall()]); pause()
        elif c == "13":
            show_results([d.windows_update_status()]); pause()
        elif c == "14":
            show_results([d.view_hosts_file()]); pause()
        elif c == "15":
            show_results([d.open_system_properties()]); pause()
        elif c == "16":
            show_results([d.open_group_policy()]); pause()
        elif c == "17":
            svc = console.input("Service name: ").strip()
            try:
                svc = validate_service_name(svc)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.check_service(svc)]); pause()
        elif c == "18":
            if confirm("SFC /scannow bisa memakan waktu lama. Lanjutkan?"):
                r = d.run_sfc()
                show_results([r], module_name="WINDOWS", save_report=True)
                log_action("WINDOWS", "SFC /SCANNOW", "LOCAL", r.state)
            pause()
        elif c == "19":
            if confirm("DISM RestoreHealth butuh internet & waktu lama. Lanjutkan?"):
                r = d.run_dism_restore_health()
                show_results([r], module_name="WINDOWS", save_report=True)
                log_action("WINDOWS", "DISM RESTOREHEALTH", "LOCAL", r.state)
            pause()
        elif c == "20":
            drive = console.input("Drive (default C:): ").strip() or "C:"
            if confirm(f"CHKDSK {drive}?"):
                r = d.run_chkdsk(drive)
                show_results([r], module_name="WINDOWS", save_report=True)
                log_action("WINDOWS", "CHKDSK", drive, r.state)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
