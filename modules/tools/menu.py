from ..core.ui import console, header, show_results, pause, read_choice
from . import utils as d


def menu():
    while True:
        header("TOOLS")
        console.print("[01] CMD                    [06] System Configuration")
        console.print("[02] PowerShell                [07] Disk Cleanup")
        console.print("[03] Windows Terminal              [08] Character Map")
        console.print("[04] Regedit                          [09] Snipping Tool")
        console.print("[05] MSConfig                             [10] Calculator")
        console.print("\n[00] BACK\n")
        c = read_choice()

        launchers = {
            "1": d.open_cmd, "2": d.open_powershell, "3": d.open_windows_terminal,
            "4": d.open_regedit, "5": d.open_msconfig, "6": d.open_system_configuration,
            "7": d.open_disk_cleanup, "8": d.open_character_map, "9": d.open_snipping_tool,
            "10": d.open_calculator,
        }
        if c in launchers:
            show_results([launchers[c]()]); pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
