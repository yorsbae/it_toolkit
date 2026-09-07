"""
IT SUPPORT TOOLKIT
====================
Entry point. Jalankan dengan:  python main.py
Atau gunakan ITSupport.exe hasil build (lihat build.bat).

Diagnose first -> Fix second -> Verify third -> Report last.
"""

import sys

from modules.core.ui import console, render_main_menu_box, pause, read_choice
from modules.core.splash import show_splash

from modules.network import menu as network
from modules.windows import menu as windows
from modules.hardware import menu as hardware
from modules.printer import menu as printer
from modules.cctv import menu as cctv
from modules.server import menu as server
from modules.remote import menu as remote
from modules.sharing import menu as sharing
from modules.security import menu as security
from modules.monitoring import menu as monitoring
from modules.maintenance import menu as maintenance
from modules.tools import menu as tools
from modules.custom import menu as custom
from modules.report import menu as report
from modules.settings import menu as settings
from modules.printmgmt import menu as printmgmt
from modules.printbridge import menu as printbridge

MENU_ROWS = [
    ("[01] NETWORK", "[07] REMOTE", "[13] CUSTOM"),
    ("[02] WINDOWS", "[08] SHARING", "[14] REPORT"),
    ("[03] HARDWARE", "[09] SECURITY", "[15] SETTINGS"),
    ("[04] PRINTER", "[10] MONITORING", "[16] PRINT MGMT"),
    ("[05] CCTV", "[11] MAINTENANCE", "[17] PRINT BRIDGE"),
    ("[06] SERVER", "[12] TOOLS", ""),
]


def main_menu():
    while True:
        render_main_menu_box(MENU_ROWS)
        console.print()
        choice = read_choice()
        menus = {
            "1": network.menu, "2": windows.menu, "3": hardware.menu,
            "4": printer.menu, "5": cctv.menu, "6": server.menu,
            "7": remote.menu, "8": sharing.menu, "9": security.menu,
            "10": monitoring.menu, "11": maintenance.menu, "12": tools.menu,
            "13": custom.menu, "14": report.menu, "15": settings.menu,
            "16": printmgmt.menu, "17": printbridge.menu,
        }
        if choice == "0":
            console.print("[cyan]Goodbye.[/cyan]")
            sys.exit(0)
        elif choice in menus:
            menus[choice]()
        else:
            console.print("[red]Invalid option[/red]")
            pause()


if __name__ == "__main__":
    if "--watchdog-check" in sys.argv:
        # Mode headless untuk dijadwalkan (Task Scheduler), BUKAN untuk
        # dipakai interaktif. Satu kali cek + self-heal kalau perlu, lalu
        # keluar - tanpa splash, tanpa menu. Lihat modules/monitoring/watchdog.py
        # dan jawaban "dimana dijalankan" di dokumentasi/README.
        from modules.monitoring import watchdog as w
        from modules.core.logger import log_action

        cfg = w.get_watchdog_config()
        result = w.check_connectivity()
        state = result["state"]
        if state != "OK":
            w.log_outage_event(state, result["detail"])
            log_action("MONITORING", "WATCHDOG CHECK (SCHEDULED)", state, "FAIL", error=result["detail"])
            if cfg["self_heal_enabled"] and state in ("INTERNET_DOWN", "DNS_DOWN"):
                w.run_self_heal_sequence()
                log_action("MONITORING", "WATCHDOG SELF-HEAL (SCHEDULED)", state, "SUCCESS")
            if cfg["remote_reboot_enabled"] and state == "INTERNET_DOWN":
                r = w.trigger_remote_reboot(cfg)
                log_action("MONITORING", "WATCHDOG REMOTE REBOOT (SCHEDULED)", state, r.state)
            print(f"[WATCHDOG] {state}: {result['detail']}")
        else:
            print("[WATCHDOG] OK")
        sys.exit(0)

    try:
        show_splash()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[cyan]Interrupted. Goodbye.[/cyan]")

