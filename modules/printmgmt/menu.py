from datetime import datetime

from rich.table import Table

from ..core.ui import console, header, show_results, pause, read_choice, confirm
from ..core.logger import log_action
from . import usage as u


def _jobs_table(title: str, jobs: list) -> Table:
    table = Table(title=title)
    table.add_column("Time", style="dim")
    table.add_column("User")
    table.add_column("Document")
    table.add_column("Printer")
    table.add_column("Pages", justify="right")
    table.add_column("Size (KB)", justify="right")
    for j in jobs[:200]:  # cegah layar banjir kalau history sangat panjang
        table.add_row(j["time"], j["user"], j["document"], j["printer"], str(j["pages"]), str(j["size_kb"]))
    return table


def _show_jobs_or_hint(jobs: list, err: str, title: str):
    if err:
        console.print(f"[red]{err}[/red]")
        return
    if not jobs:
        console.print("[dim]Belum ada job tercatat pada rentang ini.[/dim]")
        console.print("[dim]Kalau ini pertama kali dipakai di PC ini, jalankan dulu "
                       "[09] Enable/Check Print Job Logging (butuh admin).[/dim]")
        return
    console.print(_jobs_table(title, jobs))
    console.print(f"\n[dim]{len(jobs)} job ditemukan"
                   + (f" (menampilkan 200 pertama)" if len(jobs) > 200 else "") + "[/dim]")


def menu():
    while True:
        header("PRINT MANAGEMENT")
        console.print("[dim]Terinspirasi PaperCut - job tracking, usage & cost report, "
                       "tanpa perlu server tambahan (baca native Windows Print log).[/dim]\n")
        console.print("[01] Live Print Queue (All Printers)")
        console.print("[02] Print Job History - Today")
        console.print("[03] Print Job History - Custom Range")
        console.print("[04] Search Print Jobs")
        console.print("[05] Usage by User (Top Users)")
        console.print("[06] Usage by Printer (Top Printers)")
        console.print("[07] Estimated Cost Report")
        console.print("[08] Export Job History to CSV")
        console.print("[09] Enable/Check Print Job Logging")
        console.print("[10] Set Cost per Page")
        console.print("[11] Print Test Page (Client Test)")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            jobs = u.live_queue_all()
            if not jobs:
                console.print("[dim]Tidak ada job di antrian printer lokal saat ini.[/dim]")
            else:
                table = Table(title="Live Print Queue")
                table.add_column("Printer")
                table.add_column("Document")
                table.add_column("Submitted By")
                table.add_column("Progress", justify="right")
                table.add_column("Status")
                for j in jobs:
                    printed = j.get("PagesPrinted", 0) or 0
                    total = j.get("TotalPages", 0) or 0
                    progress = f"{printed}/{total}" if total else "-"
                    table.add_row(
                        str(j.get("PrinterName", "")), str(j.get("DocumentName", "")),
                        str(j.get("SubmittedBy", "")), progress, str(j.get("JobStatus", "")),
                    )
                console.print(table)
            pause()

        elif c == "2":
            jobs, err = u.jobs_today()
            _show_jobs_or_hint(jobs, err, "Print Job History - Today")
            pause()

        elif c == "3":
            days_raw = console.input("Rentang berapa hari terakhir (mis. 7): ").strip()
            try:
                days = max(1, int(days_raw))
            except ValueError:
                console.print("[red]Input harus angka.[/red]")
                pause()
                continue
            jobs, err = u.jobs_last_days(days)
            _show_jobs_or_hint(jobs, err, f"Print Job History - {days} Hari Terakhir")
            pause()

        elif c == "4":
            keyword = console.input("Cari (user/printer/nama dokumen): ").strip()
            jobs, err = u.jobs_last_days(30)
            if err:
                console.print(f"[red]{err}[/red]")
            else:
                filtered = u.search_jobs(jobs, keyword)
                _show_jobs_or_hint(filtered, None, f"Hasil Pencarian: '{keyword}' (30 hari terakhir)")
            pause()

        elif c == "5":
            jobs, err = u.jobs_last_days(30)
            if err:
                console.print(f"[red]{err}[/red]")
            elif not jobs:
                console.print("[dim]Belum ada data (30 hari terakhir).[/dim]")
            else:
                table = Table(title="Top Users (30 Hari Terakhir)")
                table.add_column("User")
                table.add_column("Jobs", justify="right")
                table.add_column("Pages", justify="right")
                for row in u.usage_by_user(jobs):
                    table.add_row(row["user"], str(row["jobs"]), str(row["pages"]))
                console.print(table)
            pause()

        elif c == "6":
            jobs, err = u.jobs_last_days(30)
            if err:
                console.print(f"[red]{err}[/red]")
            elif not jobs:
                console.print("[dim]Belum ada data (30 hari terakhir).[/dim]")
            else:
                table = Table(title="Top Printers (30 Hari Terakhir)")
                table.add_column("Printer")
                table.add_column("Jobs", justify="right")
                table.add_column("Pages", justify="right")
                for row in u.usage_by_printer(jobs):
                    table.add_row(row["printer"], str(row["jobs"]), str(row["pages"]))
                console.print(table)
            pause()

        elif c == "7":
            jobs, err = u.jobs_last_days(30)
            if err:
                console.print(f"[red]{err}[/red]")
            elif not jobs:
                console.print("[dim]Belum ada data (30 hari terakhir).[/dim]")
            else:
                cfg = u.get_cost_config()
                console.print(f"[dim]Tarif: {cfg['currency']} {cfg['cost_per_page']}/halaman "
                               f"(flat, ubah lewat [10] Set Cost per Page)[/dim]\n")
                rows = u.cost_report_by_user(jobs)
                table = Table(title="Estimated Cost Report - 30 Hari Terakhir")
                table.add_column("User")
                table.add_column("Pages", justify="right")
                table.add_column("Estimated Cost", justify="right")
                total = 0
                for row in rows:
                    table.add_row(row["user"], str(row["pages"]), f"{row['currency']} {row['cost']:,.0f}")
                    total += row["cost"]
                console.print(table)
                console.print(f"\n[bold]TOTAL: {cfg['currency']} {total:,.0f}[/bold]")
            pause()

        elif c == "8":
            jobs, err = u.jobs_last_days(30)
            if err:
                console.print(f"[red]{err}[/red]")
            elif not jobs:
                console.print("[dim]Belum ada data untuk di-export (30 hari terakhir).[/dim]")
            else:
                path = u.export_csv(jobs)
                console.print(f"[green]Exported: {path}[/green]")
                log_action("PRINT MANAGEMENT", "EXPORT CSV", str(path), "SUCCESS")
            pause()

        elif c == "9":
            show_results([u.check_logging_enabled()])
            if confirm("Aktifkan Print Job Logging sekarang?"):
                r = u.enable_logging()
                show_results([r])
                log_action("PRINT MANAGEMENT", "ENABLE LOGGING", "LOCAL", r.state)
            pause()

        elif c == "10":
            cfg = u.get_cost_config()
            console.print(f"[dim]Tarif saat ini: {cfg['currency']} {cfg['cost_per_page']}/halaman[/dim]")
            rate_raw = console.input("Tarif baru per halaman (angka saja): ").strip()
            currency = console.input(f"Mata uang [{cfg['currency']}]: ").strip() or cfg["currency"]
            try:
                rate = float(rate_raw)
            except ValueError:
                console.print("[red]Input tarif harus angka.[/red]")
                pause()
                continue
            u.save_cost_config(rate, currency)
            console.print(f"[green]Tarif disimpan: {currency} {rate:,.0f}/halaman[/green]")
            log_action("PRINT MANAGEMENT", "SET COST PER PAGE", f"{currency} {rate}", "SUCCESS")
            pause()

        elif c == "11":
            from ..printer.diagnostics import list_printers, print_test_page
            printers = list_printers()
            if not printers:
                console.print("[dim]Tidak ada printer terdeteksi lokal.[/dim]")
                pause()
                continue
            for i, p in enumerate(printers, 1):
                console.print(f"[{i}] {p['name']}  ({p['status']})")
            sel = console.input("\nPilih nomor printer: ").strip()
            try:
                idx = int(sel)
                name = printers[idx - 1]["name"]
            except (ValueError, IndexError):
                console.print("[red]Pilihan tidak valid.[/red]")
                pause()
                continue
            r = print_test_page(name)
            show_results([r])
            console.print("[dim]Cek [02] Print Job History - Today setelah beberapa detik "
                           "untuk verifikasi job tercatat.[/dim]")
            log_action("PRINT MANAGEMENT", "CLIENT TEST PAGE", name, r.state)
            pause()

        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
