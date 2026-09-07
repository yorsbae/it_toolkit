from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.validate import validate_hostname_or_ip, ValidationError
from . import engine as d


def menu():
    while True:
        header("REPORT")
        console.print("[01] System Report          [06] Hardware Report")
        console.print("[02] Network Report            [07] Sharing Report")
        console.print("[03] Printer Report                [08] Full Diagnostic")
        console.print("[04] Server Report                    [09] View Reports")
        console.print("[05] CCTV Report                          [10] Export Report")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            _run(d.system_report()); pause()
        elif c == "2":
            target = console.input("Target: ").strip()
            try:
                target = validate_hostname_or_ip(target)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            _run(d.network_report(target)); pause()
        elif c == "3":
            _run(d.printer_report()); pause()
        elif c == "4":
            _run(d.server_report()); pause()
        elif c == "5":
            _run(d.cctv_report()); pause()
        elif c == "6":
            _run(d.hardware_report()); pause()
        elif c == "7":
            _run(d.sharing_report()); pause()
        elif c == "8":
            console.print("[dim]Menjalankan seluruh module utama, mungkin memakan waktu...[/dim]")
            _run(d.full_diagnostic()); pause()
        elif c == "9":
            files = d.view_reports()
            if not files:
                console.print("[dim]Belum ada report.[/dim]")
            for f in files:
                console.print(f"- {f.name}")
            pause()
        elif c == "10":
            files = d.view_reports()
            if not files:
                console.print("[dim]Belum ada report untuk di-export.[/dim]"); pause(); continue
            for i, f in enumerate(files, 1):
                console.print(f"[{i}] {f.name}")
            idx = console.input("Pilih nomor report: ").strip()
            try:
                selected = files[int(idx) - 1]
            except (ValueError, IndexError):
                console.print("[red]Invalid[/red]"); pause(); continue
            dest = console.input("Export ke path: ").strip()
            show_results([d.export_report(selected, dest)])
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def _run(report_tuple):
    txt_path, _, overall = report_tuple
    console.print(f"\n[bold]RESULT:[/bold] {overall}")
    console.print(f"[dim]Report saved: {txt_path}[/dim]")
