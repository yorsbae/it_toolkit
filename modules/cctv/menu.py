from ..core.ui import console, header, show_results, confirm, pause, read_choice
from ..core.status import render_line
from ..core.validate import validate_ip, validate_cidr, ValidationError
from . import diagnostics as d


def menu():
    while True:
        header("CCTV")
        console.print("[01] Camera IP Scan          [07] Camera Status")
        console.print("[02] Camera Ping                [08] Offline Camera Finder")
        console.print("[03] NVR Ping                       [09] Camera Report")
        console.print("[04] NVR Port Test                      [10] NVR Information")
        console.print("[05] RTSP Test                              [11] Assign Camera Label / Location")
        console.print("[06] ONVIF Discovery")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            camera_ip_scan_flow()
        elif c == "2":
            ip = console.input("Camera IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            _ping_single(ip)
            pause()
        elif c == "3":
            ip = console.input("NVR IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.nvr_ping(ip)]); pause()
        elif c == "4":
            ip = console.input("NVR IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            port_raw = console.input("Port (default 80): ").strip()
            try:
                port = int(port_raw) if port_raw else 80
                if not (1 <= port <= 65535):
                    raise ValueError()
            except ValueError:
                console.print(f"[red]Port tidak valid: '{port_raw}'[/red]")
                pause()
                continue
            show_results([d.nvr_port_test(ip, port)]); pause()
        elif c == "5":
            ip = console.input("Camera/NVR IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.rtsp_test(ip)]); pause()
        elif c == "6":
            ip = console.input("Camera IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.onvif_discovery(ip)]); pause()
        elif c == "7":
            camera_status_flow()
        elif c == "8":
            show_results(d.offline_camera_finder(), module_name="CCTV", save_report=True); pause()
        elif c == "9":
            from ..report.engine import cctv_report
            txt_path, _, overall = cctv_report()
            console.print(f"\n[bold]RESULT:[/bold] {overall}")
            console.print(f"[dim]Report saved: {txt_path}[/dim]")
            pause()
        elif c == "10":
            ip = console.input("NVR IP: ").strip()
            try:
                ip = validate_ip(ip)
            except ValidationError as e:
                console.print(f"[red]{e}[/red]"); pause(); continue
            show_results([d.nvr_information(ip)]); pause()
        elif c == "11":
            assign_label_flow()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()


def _ping_single(ip):
    from ..network.basic import ping_target
    r = ping_target(ip)
    r.label = f"Camera Ping {ip}"
    show_results([r])


def camera_ip_scan_flow():
    """PRD §17.1: scan -> [A] All / [S] Select / [N] Skip -> assign label -> save."""
    header("CAMERA IP SCAN")
    subnet = console.input("Range/Subnet CIDR (mis. 192.168.50.0/24): ").strip()
    try:
        subnet = validate_cidr(subnet)
    except ValidationError as e:
        console.print(f"[red]{e}[/red]")
        pause()
        return
    console.print("\nSCANNING...\n")
    found = d.camera_ip_scan(subnet)

    if not found:
        console.print("[dim]Tidak ada device online ditemukan.[/dim]")
        pause(); return

    console.print(f"FOUND : {len(found)} DEVICE(S)\n")
    for i, dev in enumerate(found, 1):
        console.print(f"[{i}] {dev['ip']}   ONLINE")

    console.print("\nAssign name/location? [A] All  [S] Select  [N] Skip")
    choice = console.input("> ").strip().upper()

    labels = {}
    if choice == "A":
        for dev in found:
            name = console.input(f"\n{dev['ip']}\nName/Location: ").strip()
            if name:
                labels[dev["ip"]] = name
    elif choice == "S":
        sel = console.input("\nSelect device number (comma-separated, e.g. 1,3): ").strip()
        try:
            indices = [int(x.strip()) for x in sel.split(",") if x.strip().isdigit()]
        except ValueError:
            indices = []
        for idx in indices:
            if 1 <= idx <= len(found):
                dev = found[idx - 1]
                name = console.input(f"\n{dev['ip']}\nName/Location: ").strip()
                if name:
                    labels[dev["ip"]] = name
    # [N] Skip -> labels tetap kosong, semua device tersimpan tanpa nama

    d.save_scan_results(found, labels)

    console.print(f"\n[green][\u2713] Saved to config/cctv.json[/green]")
    unlabeled = [dev["ip"] for dev in found if dev["ip"] not in labels]
    if unlabeled:
        console.print(f"[dim][-] {', '.join(unlabeled)} left unlabeled[/dim]")
    pause()


def camera_status_flow():
    """PRD §17 contoh tabel: NAMA/IP - IP - STATUS - LATENCY, + summary TOTAL/ONLINE/OFFLINE."""
    header("CAMERA STATUS")
    data = d.camera_status_table()
    if data["total"] == 0:
        console.print("[dim]Belum ada kamera terdaftar, jalankan Camera IP Scan dulu.[/dim]")
        pause(); return

    for row in data["rows"]:
        state = "PASS" if row["online"] else "FAIL"
        line = render_line(
            f"{row['display_name']:<28}{row['ip']:<18}{row['status']:<10}{row['latency']}",
            state,
        )
        console.print(line)

    console.print(f"\nTOTAL   : {data['total']}")
    console.print(f"ONLINE  : {data['online']}")
    console.print(f"OFFLINE : {data['offline']}")
    pause()


def assign_label_flow():
    """PRD §17 item [11] - rename/hapus label, cari by IP atau nama, bisa satu device spesifik."""
    header("ASSIGN CAMERA LABEL / LOCATION")
    cameras = d.get_camera_list()
    if not cameras:
        console.print("[dim]Belum ada kamera terdaftar. Jalankan Camera IP Scan dulu.[/dim]")
        pause(); return

    for cam in cameras:
        label = cam.get("name") or "(belum dilabeli)"
        console.print(f"- {label}: {cam['ip']}")

    query = console.input("\nCari device (IP atau nama): ").strip()
    match = d.find_camera(ip=query) or d.find_camera(name=query)
    if not match:
        console.print("[red]Device tidak ditemukan.[/red]")
        pause(); return

    console.print(f"\nDevice: {match['ip']} (label saat ini: {match.get('name') or '-'})")
    console.print("[1] Rename/Set label  [2] Hapus label  [0] Batal")
    action = console.input("> ").strip()
    if action == "1":
        name = console.input("Name/Location baru: ").strip()
        show_results([d.assign_label(match["ip"], name)])
    elif action == "2":
        if confirm(f"Hapus label untuk {match['ip']}?"):
            show_results([d.remove_label(match["ip"])])
    pause()
