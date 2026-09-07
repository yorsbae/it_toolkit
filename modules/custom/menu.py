from ..core.ui import console, header, show_results, confirm, pause, read_choice
from . import engine as d


def menu():
    while True:
        header("CUSTOM")
        console.print("[01] Run Custom Command      [05] Delete Command")
        console.print("[02] Quick Run (One-Time)       [06] Import Commands")
        console.print("[03] Add Command                   [07] Export Commands")
        console.print("[04] Edit Command                     [08] List Commands")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            run_saved_command()
        elif c == "2":
            quick_run()
        elif c == "3":
            add_command_flow()
        elif c == "4":
            edit_command_flow()
        elif c == "5":
            delete_command_flow()
        elif c == "6":
            console.print("Tempel isi JSON (format {\"commands\": [...]}), lalu Enter kosong untuk selesai:")
            lines = []
            while True:
                line = console.input()
                if line == "":
                    break
                lines.append(line)
            show_results([d.import_commands("\n".join(lines))])
            pause()
        elif c == "7":
            show_results([d.export_commands()]); pause()
        elif c == "8":
            list_commands()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def _print_command_list(commands):
    for cmd in commands:
        admin_flag = " (admin)" if cmd.get("requires_admin") else ""
        console.print(f"[{cmd['id']:02}] {cmd['name']}{admin_flag}  [dim]({cmd.get('category', cmd.get('type', ''))})[/dim]")


def run_saved_command():
    header("RUN CUSTOM COMMAND")
    commands = d.list_custom_commands()
    if not commands:
        console.print("[dim]Belum ada command tersimpan. Gunakan Add Command atau Quick Run.[/dim]")
        pause(); return
    _print_command_list(commands)
    console.print("[00] BACK\n")
    choice = read_choice()
    if choice == "0":
        return
    match = next((c for c in commands if str(c["id"]) == choice), None)
    if not match:
        console.print("[red]Invalid option[/red]"); pause(); return
    if confirm(f"Jalankan '{match['name']}'?"):
        console.print("\n[dim]EXECUTING...[/dim]\n")
        show_results([d.run_custom_command(match)])
    pause()


def quick_run():
    header("QUICK RUN (ONE-TIME)")
    console.print("[1] CMD  [2] PowerShell  [3] Batch/Script  [4] URL/CURL")
    type_choice = console.input("> ").strip()
    type_map = {"1": "CMD", "2": "POWERSHELL", "3": "SCRIPT", "4": "URL"}
    command_type = type_map.get(type_choice, "CMD")

    command = console.input("\nCommand: ").strip()
    requires_admin = confirm("Run as Administrator?")

    console.print("\n[dim]EXECUTING...[/dim]\n")
    result = d.quick_run(command_type, command, requires_admin)
    show_results([result])

    if confirm("\nSave this command for future use?"):
        name = console.input("Name: ").strip()
        existing = next((c for c in d.list_custom_commands() if c["name"].lower() == name.lower()), None)
        overwrite = False
        if existing:
            overwrite = confirm(f"Nama '{name}' sudah ada. Overwrite?")
            if not overwrite:
                name = console.input("Nama baru: ").strip()
        show_results([d.add_command(name, command_type, command, requires_admin, overwrite=overwrite)])
    pause()


def add_command_flow():
    header("ADD COMMAND")
    name = console.input("Name: ").strip()
    console.print("Type: [1] CMD  [2] PowerShell  [3] Batch/Script  [4] Python  [5] Executable  [6] URL  [7] CURL")
    type_choice = console.input("> ").strip()
    type_map = {"1": "CMD", "2": "POWERSHELL", "3": "SCRIPT", "4": "PYTHON", "5": "EXECUTABLE", "6": "URL", "7": "CURL"}
    command_type = type_map.get(type_choice, "CMD")
    command = console.input("Command: ").strip()
    category = console.input("Category (default GENERAL): ").strip() or "GENERAL"
    requires_admin = confirm("Run as Administrator?")
    show_results([d.add_command(name, command_type, command, requires_admin, category)])
    pause()


def edit_command_flow():
    header("EDIT COMMAND")
    commands = d.list_custom_commands()
    if not commands:
        console.print("[dim]Belum ada command.[/dim]"); pause(); return
    _print_command_list(commands)
    cmd_id = console.input("\nID untuk diedit: ").strip()
    try:
        cmd_id = int(cmd_id)
    except ValueError:
        console.print("[red]ID tidak valid[/red]"); pause(); return
    new_command = console.input("Command baru (Enter untuk skip): ").strip()
    fields = {}
    if new_command:
        fields["command"] = new_command
    show_results([d.edit_command(cmd_id, **fields)])
    pause()


def delete_command_flow():
    header("DELETE COMMAND")
    commands = d.list_custom_commands()
    if not commands:
        console.print("[dim]Belum ada command.[/dim]"); pause(); return
    _print_command_list(commands)
    cmd_id = console.input("\nID untuk dihapus: ").strip()
    try:
        cmd_id = int(cmd_id)
    except ValueError:
        console.print("[red]ID tidak valid[/red]"); pause(); return
    if confirm("Yakin hapus command ini?"):
        show_results([d.delete_command(cmd_id)])
    pause()


def list_commands():
    header("LIST COMMANDS")
    commands = d.list_custom_commands()
    if not commands:
        console.print("[dim]Belum ada command tersimpan.[/dim]")
    else:
        _print_command_list(commands)
    pause()
