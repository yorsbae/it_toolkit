from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.logger import log_action
from ..core.validate import validate_adapter_name, validate_free_text_for_shell, ValidationError
from . import actions as d


def menu():
    while True:
        header("MAINTENANCE")
        console.print("[01] Temporary Files          [07] DISM Restore")
        console.print("[02] Disk Cleanup                [08] CHKDSK")
        console.print("[03] Flush DNS                       [09] Windows Update Cache")
        console.print("[04] Restart Print Spooler               [10] Component Store")
        console.print("[05] SFC Scan                                [11] Create Restore Point")
        console.print("[06] DISM Check                                 [12] Restart Network Adapter")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            if confirm("Hapus semua file di folder Temp?"):
                r = d.clear_temp_files()
                show_results([r], module_name="MAINTENANCE", save_report=True)
                log_action("MAINTENANCE", "CLEAR TEMP FILES", "LOCAL", r.state)
            pause()
        elif c == "2":
            if confirm("Jalankan Disk Cleanup?"):
                r = d.disk_cleanup()
                show_results([r])
                log_action("MAINTENANCE", "DISK CLEANUP", "LOCAL", r.state)
            pause()
        elif c == "3":
            r = d.flush_dns()
            show_results([r])
            log_action("MAINTENANCE", "FLUSH DNS", "LOCAL", r.state)
            pause()
        elif c == "4":
            if confirm("Restart Print Spooler?"):
                r = d.restart_print_spooler()
                show_results([r])
                log_action("MAINTENANCE", "RESTART PRINT SPOOLER", "LOCAL", r.state)
            pause()
        elif c == "5":
            if confirm("SFC Scan bisa lama. Lanjutkan?"):
                console.print("[dim]RUNNING SFC SCAN - please wait...[/dim]")
                r = d.sfc_scan()
                show_results([r], module_name="MAINTENANCE", save_report=True)
                log_action("MAINTENANCE", "SFC SCAN", "LOCAL", r.state)
            pause()
        elif c == "6":
            if confirm("DISM CheckHealth?"):
                r = d.dism_check()
                show_results([r])
                log_action("MAINTENANCE", "DISM CHECKHEALTH", "LOCAL", r.state)
            pause()
        elif c == "7":
            if confirm("DISM RestoreHealth butuh internet & waktu lama. Lanjutkan?"):
                console.print("[dim]RUNNING DISM RESTORE - please wait...[/dim]")
                r = d.dism_restore()
                show_results([r], module_name="MAINTENANCE", save_report=True)
                log_action("MAINTENANCE", "DISM RESTOREHEALTH", "LOCAL", r.state)
            pause()
        elif c == "8":
            drive = console.input("Drive (default C:): ").strip() or "C:"
            if confirm(f"CHKDSK {drive}?"):
                r = d.chkdsk(drive)
                show_results([r], module_name="MAINTENANCE", save_report=True)
                log_action("MAINTENANCE", "CHKDSK", drive, r.state)
            pause()
        elif c == "9":
            if confirm("Bersihkan Windows Update Cache?"):
                r = d.clear_windows_update_cache()
                show_results([r])
                log_action("MAINTENANCE", "CLEAR WINDOWS UPDATE CACHE", "LOCAL", r.state)
            pause()
        elif c == "10":
            if confirm("Component Store Cleanup bisa lama. Lanjutkan?"):
                r = d.component_store_cleanup()
                show_results([r])
                log_action("MAINTENANCE", "COMPONENT STORE CLEANUP", "LOCAL", r.state)
            pause()
        elif c == "11":
            desc = console.input("Deskripsi restore point: ").strip() or "IT Support Toolkit Checkpoint"
            try:
                desc = validate_free_text_for_shell(desc, "Deskripsi")
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            if confirm("Buat System Restore Point?"):
                r = d.create_restore_point(desc)
                show_results([r])
                log_action("MAINTENANCE", "CREATE RESTORE POINT", desc, r.state)
            pause()
        elif c == "12":
            name = console.input("Adapter name: ").strip()
            try:
                name = validate_adapter_name(name)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            if confirm(f"Restart adapter '{name}'?"):
                r = d.restart_network_adapter(name)
                show_results([r])
                log_action("MAINTENANCE", "RESTART NETWORK ADAPTER", name, r.state)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
