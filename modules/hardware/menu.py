from ..core.ui import console, header, show_results, pause, read_choice
from . import info as d


def menu():
    while True:
        header("HARDWARE")
        console.print("[01] CPU Info          [08] USB Devices")
        console.print("[02] RAM Info            [09] Monitor")
        console.print("[03] Disk Info             [10] Network Adapter")
        console.print("[04] GPU Info                [11] Battery")
        console.print("[05] Motherboard Info          [12] SMART Disk")
        console.print("[06] BIOS Info                   [13] Full Hardware Report")
        console.print("[07] Serial Number")
        console.print("\n[00] BACK\n")
        c = read_choice()

        if c == "1":
            show_results([d.get_cpu_info()]); pause()
        elif c == "2":
            show_results([d.get_ram_info()]); pause()
        elif c == "3":
            show_results(d.get_disk_info()); pause()
        elif c == "4":
            show_results([d.get_gpu_info()]); pause()
        elif c == "5":
            show_results([d.get_motherboard_info()]); pause()
        elif c == "6":
            show_results([d.get_bios_info()]); pause()
        elif c == "7":
            show_results([d.get_serial_number()]); pause()
        elif c == "8":
            show_results([d.get_usb_devices()]); pause()
        elif c == "9":
            show_results([d.get_monitor_info()]); pause()
        elif c == "10":
            show_results(d.get_network_adapter_hardware()); pause()
        elif c == "11":
            show_results([d.get_battery_info()]); pause()
        elif c == "12":
            show_results(d.get_disk_smart_status()); pause()
        elif c == "13":
            results = [d.get_cpu_info(), d.get_ram_info(), d.get_gpu_info(),
                       d.get_motherboard_info(), d.get_bios_info(), d.get_serial_number(),
                       d.get_usb_devices(), d.get_monitor_info()]
            results += d.get_network_adapter_hardware()
            results.append(d.get_battery_info())
            results += d.get_disk_smart_status()
            results += d.get_disk_info()
            show_results(results, module_name="HARDWARE", save_report=True)
            pause()
        elif c == "0":
            return
        else:
            console.print("[red]Invalid option[/red]"); pause()
