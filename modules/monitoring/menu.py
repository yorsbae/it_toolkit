import time
from datetime import datetime
from rich.live import Live
from rich.table import Table
from ..core.ui import console, header, show_results, pause, read_choice, confirm
from ..core.status import render_line
from ..core.logger import log_action
from . import dashboard as d
from . import watchdog as w


def _bar(pct: float, width: int = 10) -> str:
    filled = int(round((pct / 100) * width))
    filled = max(0, min(width, filled))
    return "\u2588" * filled + "\u2591" * (width - filled)


def menu():
    while True:
        header("MONITORING")
        console.print("[01] CPU              [07] Ping Monitor")
        console.print("[02] RAM                [08] Server Monitor")
        console.print("[03] Disk                 [09] Printer Monitor")
        console.print("[04] Network                 [10] CCTV Monitor")
        console.print("[05] Processes                  [11] Full Dashboard")
        console.print("[06] Services                        [12] Internet Watchdog")
        console.print("                                     [13] Outage History Report")
        console.print("                                     [14] Configure Watchdog")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            pct = d.cpu_usage()
            console.print(f"CPU   {_bar(pct)} {pct}%")
            pause()
        elif c == "2":
            pct = d.ram_usage()
            console.print(f"RAM   {_bar(pct)} {pct}%")
            pause()
        elif c == "3":
            pct = d.disk_usage()
            console.print(f"DISK  {_bar(pct)} {pct}%")
            pause()
        elif c == "4":
            mbps = d.network_throughput_mbps()
            console.print(f"NETWORK  {mbps} MB total received")
            pause()
        elif c == "5":
            show_results([d.top_processes()]); pause()
        elif c == "6":
            show_results([d.services_not_running()]); pause()
        elif c == "7":
            live_ping_monitor()
        elif c == "8":
            for name, r in d.server_monitor_snapshot():
                console.print(render_line(f"{name}", r.state))
            pause()
        elif c == "9":
            for name, status in d.printer_monitor_snapshot():
                console.print(f"- {name}: {status}")
            pause()
        elif c == "10":
            for name, r in d.cctv_monitor_snapshot():
                console.print(render_line(f"{name}", r.state))
            pause()
        elif c == "11":
            full_dashboard()
        elif c == "12":
            internet_watchdog()
        elif c == "13":
            outage_history_report()
        elif c == "14":
            configure_watchdog()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def live_ping_monitor():
    header("MONITORING > PING MONITOR")
    targets = d.get_monitor_targets()
    if not targets:
        console.print("[dim]Belum ada target di config/servers.json / cctv.json[/dim]")
        pause(); return
    console.print("[dim]Live monitor - Ctrl+C untuk berhenti[/dim]\n")
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                table = Table(title="Ping Monitor")
                table.add_column("Target")
                table.add_column("Status")
                for name, r in d.ping_monitor_snapshot():
                    table.add_row(name, render_line(r.detail or r.label, r.state))
                live.update(table)
                time.sleep(3)
    except KeyboardInterrupt:
        pass
    pause()


def full_dashboard():
    header("MONITORING > FULL DASHBOARD")
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                snap = d.full_dashboard_snapshot()
                table = Table(title="SYSTEM MONITOR")
                table.add_column("Metric")
                table.add_column("Value")
                table.add_row("CPU", f"{_bar(snap['cpu'])} {snap['cpu']}%")
                table.add_row("RAM", f"{_bar(snap['ram'])} {snap['ram']}%")
                table.add_row("DISK", f"{_bar(snap['disk'])} {snap['disk']}%")
                table.add_row("NETWORK", f"{snap['network_mbps']} MB")
                table.add_row("UPTIME", snap["uptime"])
                table.add_row("PROCESSES", str(snap["processes"]))
                table.add_row("SERVICES", str(snap["services"]))
                live.update(table)
                time.sleep(3)
    except KeyboardInterrupt:
        pass
    pause()


def internet_watchdog():
    """Live monitor yang membedakan LAN mati vs Internet mati vs DNS rusak,
    mencatat tiap outage ke histori, dan (kalau diaktifkan) mencoba
    self-heal sisi client otomatis saat internet terdeteksi mati beberapa
    kali berturut-turut. Restart AP/router TETAP manual kecuali remote
    reboot sudah dikonfigurasi lewat [14] Configure Watchdog."""
    header("MONITORING > INTERNET WATCHDOG")
    cfg = w.get_watchdog_config()
    console.print(f"[dim]Interval cek: {cfg['check_interval_sec']}s  |  "
                   f"Self-heal: {'ON' if cfg['self_heal_enabled'] else 'OFF'}  |  "
                   f"Remote reboot: {'ON (' + cfg['remote_reboot_method'] + ')' if cfg['remote_reboot_enabled'] else 'OFF'}[/dim]")
    console.print("[dim]Ctrl+C untuk berhenti[/dim]\n")

    consecutive_fails = 0
    outage_start = None
    last_state = None

    try:
        while True:
            result = w.check_connectivity()
            state = result["state"]
            ts = datetime.now().strftime("%H:%M:%S")

            if state == "OK":
                color = "green"
                if last_state and last_state != "OK" and outage_start:
                    duration = (datetime.now() - outage_start).total_seconds()
                    console.print(f"[dim]{ts}[/dim] [green]\u25cf PULIH[/green] - "
                                   f"downtime {duration:.0f}s (sebelumnya: {last_state})")
                    w.log_outage_event(last_state, "Pulih kembali normal", duration_sec=duration)
                    log_action("MONITORING", "WATCHDOG RECOVERED", last_state, "PASS")
                    outage_start = None
                consecutive_fails = 0
            else:
                color = "red" if state in ("LAN_DOWN", "INTERNET_DOWN") else "yellow"
                if outage_start is None:
                    outage_start = datetime.now()
                consecutive_fails += 1
                console.print(f"[dim]{ts}[/dim] [{color}]\u25cf {state}[/{color}] - {result['detail']} "
                               f"(gagal ke-{consecutive_fails})")
                w.log_outage_event(state, result["detail"])
                log_action("MONITORING", "WATCHDOG DETECT", state, "FAIL", error=result["detail"])

                if (cfg["self_heal_enabled"] and state in ("INTERNET_DOWN", "DNS_DOWN")
                        and consecutive_fails == cfg["consecutive_fails_before_action"]):
                    console.print(f"[yellow]  -> Mencoba self-heal sisi client "
                                   f"(flush DNS, clear ARP, renew DHCP)...[/yellow]")
                    heal_results = w.run_self_heal_sequence()
                    for r in heal_results:
                        console.print("    " + render_line(r.label, r.state) + (f" - {r.detail}" if r.detail else ""))
                    log_action("MONITORING", "WATCHDOG SELF-HEAL", state, "SUCCESS")

                if (cfg["remote_reboot_enabled"] and state == "INTERNET_DOWN"
                        and consecutive_fails == cfg["consecutive_fails_before_action"] + 2):
                    console.print(f"[yellow]  -> Masih gagal, mencoba remote reboot AP...[/yellow]")
                    r = w.trigger_remote_reboot(cfg)
                    console.print("    " + render_line(r.label, r.state) + (f" - {r.detail}" if r.detail else ""))
                    log_action("MONITORING", "WATCHDOG REMOTE REBOOT", state, r.state)

            last_state = state
            time.sleep(cfg["check_interval_sec"])
    except KeyboardInterrupt:
        console.print()
    pause()


def outage_history_report():
    header("MONITORING > OUTAGE HISTORY REPORT")
    days_raw = console.input("Rentang berapa hari terakhir (mis. 7): ").strip() or "7"
    try:
        days = max(1, int(days_raw))
    except ValueError:
        console.print("[red]Input harus angka.[/red]")
        pause(); return

    history = w.get_outage_history(days)
    if not history:
        console.print(f"[dim]Tidak ada outage tercatat dalam {days} hari terakhir. "
                       f"(Data hanya terisi selama [12] Internet Watchdog pernah dijalankan / "
                       f"dijadwalkan di rentang waktu tsb.)[/dim]")
        pause(); return

    table = Table(title=f"Outage History - {days} Hari Terakhir")
    table.add_column("Time")
    table.add_column("State")
    table.add_column("Detail")
    table.add_column("Duration")
    for ev in history[-100:]:
        dur = f"{ev['duration_sec']:.0f}s" if ev.get("duration_sec") else "-"
        state_color = "red" if ev["state"] in ("LAN_DOWN", "INTERNET_DOWN") else "yellow"
        table.add_row(ev["time"], f"[{state_color}]{ev['state']}[/{state_color}]", ev["detail"][:50], dur)
    console.print(table)

    summary = w.outage_pattern_summary(history)
    console.print(f"\nTotal event  : {summary['total_events']}")
    for state, count in summary["by_state"].items():
        console.print(f"  {state:<16} : {count}")
    if summary["avg_hours_between_internet_down"]:
        console.print(f"\n[bold]Rata-rata jarak antar INTERNET_DOWN: "
                       f"{summary['avg_hours_between_internet_down']} jam[/bold]")
        console.print("[dim]Kalau jaraknya konsisten (mis. selalu ~6 jam), itu indikasi kuat "
                       "masalah firmware/uptime AP - solusi paling andal adalah aktifkan fitur "
                       "'Scheduled Reboot' bawaan router itu sendiri, bukan cuma restart manual "
                       "tiap kali komplain masuk.[/dim]")
    pause()


def configure_watchdog():
    header("MONITORING > CONFIGURE WATCHDOG")
    cfg = w.get_watchdog_config()
    console.print(f"Check interval        : {cfg['check_interval_sec']}s")
    console.print(f"Fails before action    : {cfg['consecutive_fails_before_action']}")
    console.print(f"Self-heal (client-side) : {'ON' if cfg['self_heal_enabled'] else 'OFF'}")
    console.print(f"Remote reboot AP        : {'ON' if cfg['remote_reboot_enabled'] else 'OFF'} "
                   f"({cfg['remote_reboot_method']})")
    console.print()
    console.print("[dim]Remote reboot 'http'/'ssh' HANYA berlaku untuk AP/router yang punya "
                   "fitur manajemen jaringan sendiri. Untuk HUB MURNI (tidak punya IP/manajemen "
                   "sama sekali), satu-satunya cara restart jarak jauh adalah lewat SMART PLUG "
                   "(colokan pintar) - pilih method 'smart_plug_http'. Kalau tidak yakin, biarkan "
                   "OFF - watchdog tetap mencatat & memberi tahu, restart tetap manual.[/dim]\n")

    if not confirm("Ubah pengaturan?"):
        pause(); return

    interval_raw = console.input(f"Check interval detik [{cfg['check_interval_sec']}]: ").strip()
    if interval_raw:
        try:
            cfg["check_interval_sec"] = max(5, int(interval_raw))
        except ValueError:
            console.print("[red]Diabaikan, input tidak valid.[/red]")

    fails_raw = console.input(f"Fails berturut-turut sebelum self-heal [{cfg['consecutive_fails_before_action']}]: ").strip()
    if fails_raw:
        try:
            cfg["consecutive_fails_before_action"] = max(1, int(fails_raw))
        except ValueError:
            console.print("[red]Diabaikan, input tidak valid.[/red]")

    cfg["self_heal_enabled"] = confirm("Aktifkan self-heal client-side (flush DNS/ARP/DHCP)?")
    cfg["remote_reboot_enabled"] = confirm("Aktifkan remote reboot/power-cycle?")

    if cfg["remote_reboot_enabled"]:
        console.print("[dim]Pilihan: http (router/AP dgn reboot URL) / ssh (router/AP dgn SSH) / "
                       "smart_plug_http (HUB atau perangkat apa pun tanpa manajemen, via colokan pintar)[/dim]")
        method = console.input("Metode (http/ssh/smart_plug_http): ").strip().lower()
        if method not in ("http", "ssh", "smart_plug_http"):
            console.print("[red]Metode tidak dikenal, remote reboot dinonaktifkan.[/red]")
            cfg["remote_reboot_enabled"] = False
        else:
            cfg["remote_reboot_method"] = method
            if method == "http":
                cfg["remote_reboot_http_url"] = console.input("URL reboot HTTP (mis. http://192.168.1.1/reboot.cgi): ").strip()
            elif method == "ssh":
                cfg["remote_reboot_ssh_host"] = console.input("SSH host/IP AP: ").strip()
                cfg["remote_reboot_ssh_user"] = console.input("SSH user: ").strip()
                cfg["remote_reboot_ssh_command"] = console.input("SSH command [reboot]: ").strip() or "reboot"
            else:  # smart_plug_http
                console.print("[dim]Isi URL lokal smart plug (Tasmota/Shelly/Kasa dst) untuk mematikan "
                               "dan menyalakan hub yang tercolok di situ.[/dim]")
                cfg["smart_plug_off_url"] = console.input("URL untuk MATIKAN colokan (mis. http://192.168.1.80/cm?cmnd=Power+Off): ").strip()
                cfg["smart_plug_on_url"] = console.input("URL untuk NYALAKAN colokan (mis. http://192.168.1.80/cm?cmnd=Power+On): ").strip()
                wait_raw = console.input("Jeda mati sebelum nyala lagi, detik [5]: ").strip()
                try:
                    cfg["smart_plug_off_wait_sec"] = max(2, int(wait_raw)) if wait_raw else 5
                except ValueError:
                    cfg["smart_plug_off_wait_sec"] = 5

    w.save_watchdog_config(cfg)
    console.print("[green]Pengaturan watchdog disimpan.[/green]")
    log_action("MONITORING", "CONFIGURE WATCHDOG", "-", "SUCCESS")
    pause()
