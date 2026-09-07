from ..core.ui import console, header, show_results, pause, read_choice
from . import diagnostics as d


def menu():
    while True:
        header("SECURITY")
        console.print("[01] Windows Defender Status   [06] Security Policy")
        console.print("[02] Firewall Status               [07] Windows Update Status")
        console.print("[03] Open Ports                       [08] BitLocker Status")
        console.print("[04] Logged-in Users                     [09] System Security Report")
        console.print("[05] Local Administrators")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results([d.check_defender_status()]); pause()
        elif c == "2":
            show_results(d.check_firewall_status()); pause()
        elif c == "3":
            show_results([d.get_open_ports()]); pause()
        elif c == "4":
            show_results([d.get_logged_in_users()]); pause()
        elif c == "5":
            show_results([d.get_local_administrators()]); pause()
        elif c == "6":
            show_results([d.get_security_policy()]); pause()
        elif c == "7":
            show_results([d.get_windows_update_status()]); pause()
        elif c == "8":
            show_results([d.get_bitlocker_status()]); pause()
        elif c == "9":
            show_results(d.system_security_report(), module_name="SECURITY", save_report=True); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
