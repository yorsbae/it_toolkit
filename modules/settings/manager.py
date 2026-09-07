"""
Settings Module (PRD §32) - 11 item
------------------------------------------
Baca/tulis config/*.json langsung -> perubahan tersimpan tanpa ubah source code.
"""

from ..core.config import load_config, load_json, save_json, CONFIG_DIR
from ..core.status import CheckResult


def general_settings() -> dict:
    return load_config()


def update_general_setting(key: str, value) -> CheckResult:
    cfg = load_config()
    cfg[key] = value
    save_json("config.json", cfg)
    return CheckResult(f"Update {key}", "PASS", detail=f"{key} = {value}")


def network_targets() -> list:
    """Target ping default untuk Network Scan/Multiple Ping (opsional, terpisah dari servers.json)."""
    return load_json("network.json", default={"targets": []}).get("targets", [])


def add_network_target(name: str, ip: str) -> CheckResult:
    data = load_json("network.json", default={"targets": []})
    data["targets"].append({"name": name, "ip": ip})
    save_json("network.json", data)
    return CheckResult(f"Add Network Target {name}", "PASS", detail=ip)


def server_list() -> list:
    return load_json("servers.json", default={"servers": []}).get("servers", [])


def add_server(name: str, ip: str, ports: list) -> CheckResult:
    data = load_json("servers.json", default={"servers": []})
    data["servers"].append({"name": name, "ip": ip, "ports": ports})
    save_json("servers.json", data)
    return CheckResult(f"Add Server {name}", "PASS", detail=ip)


def remove_server(name: str) -> CheckResult:
    data = load_json("servers.json", default={"servers": []})
    before = len(data["servers"])
    data["servers"] = [s for s in data["servers"] if s["name"].lower() != name.lower()]
    save_json("servers.json", data)
    removed = before - len(data["servers"])
    state = "PASS" if removed else "FAIL"
    return CheckResult(f"Remove Server {name}", state, detail=f"{removed} removed")


def printer_list() -> list:
    return load_json("printers.json", default={"printers": []}).get("printers", [])


def add_printer_entry(name: str, ip: str) -> CheckResult:
    data = load_json("printers.json", default={"printers": []})
    data["printers"].append({"name": name, "ip": ip})
    save_json("printers.json", data)
    return CheckResult(f"Add Printer Entry {name}", "PASS", detail=ip)


def cctv_list() -> list:
    from ..cctv.diagnostics import get_camera_list
    return get_camera_list()


def custom_commands_settings() -> list:
    return load_json("custom_commands.json", default={"commands": []}).get("commands", [])


def report_settings() -> dict:
    cfg = load_config()
    return {"formats": cfg.get("report_formats", ["txt", "json"])}


def update_report_formats(formats: list) -> CheckResult:
    return update_general_setting("report_formats", formats)


def logging_settings() -> dict:
    cfg = load_config()
    return {"log_level": cfg.get("log_level", "INFO")}


def update_log_level(level: str) -> CheckResult:
    return update_general_setting("log_level", level)


def theme_settings() -> str:
    return load_config().get("theme", "cyan")


def update_theme(theme: str) -> CheckResult:
    from ..core.theme import available_themes
    valid = available_themes()
    theme = theme.strip().lower()
    if theme not in valid:
        return CheckResult(
            "Update Theme", "FAIL",
            detail=f"'{theme}' bukan pilihan valid",
            recommendation=f"Pilih salah satu: {', '.join(valid)}",
        )
    return update_general_setting("theme", theme)


def reset_configuration() -> CheckResult:
    """Reset config.json ke default. TIDAK menghapus servers/printers/cctv/custom_commands
    (destruktif untuk data operasional harus lewat konfirmasi terpisah)."""
    default = {
        "app_name": "IT SUPPORT TOOLKIT",
        "version": "1.0.0",
        "technician_name": "IT SUPPORT",
        "theme": "cyan",
        "log_level": "INFO",
        "report_formats": ["txt", "json"],
    }
    save_json("config.json", default)
    return CheckResult("Reset Configuration", "PASS", detail="config.json dikembalikan ke default")


def about() -> dict:
    cfg = load_config()
    return {
        "app_name": cfg.get("app_name"),
        "version": cfg.get("version"),
        "config_dir": str(CONFIG_DIR),
    }
