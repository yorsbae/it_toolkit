"""
Custom Command Module (PRD §30) - 8 item
------------------------------------------
Command tersimpan di config/custom_commands.json, di luar source code.
"""

from ..core.config import load_json, save_json
from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..core.logger import log_action

FILE = "custom_commands.json"


def _load() -> list:
    return load_json(FILE, default={"commands": []}).get("commands", [])


def _save(commands: list):
    save_json(FILE, {"commands": commands})


def _next_id(commands: list) -> int:
    return max([c["id"] for c in commands], default=0) + 1


def list_custom_commands() -> list:
    return _load()


def run_custom_command(cmd_entry: dict) -> CheckResult:
    if cmd_entry.get("requires_admin") and not is_admin():
        return CheckResult(cmd_entry["name"], "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(cmd_entry["command"], timeout=60)
    state = "PASS" if result["status"] == "success" else "FAIL"
    log_action("CUSTOM", cmd_entry["name"], cmd_entry["command"], state, error=result.get("details", ""))
    return CheckResult(cmd_entry["name"], state, detail=result["message"][:300] or result["details"][:300])


def quick_run(command_type: str, command: str, requires_admin: bool = False) -> CheckResult:
    """PRD §30.2 - eksekusi langsung tanpa disimpan dulu."""
    if requires_admin and not is_admin():
        return CheckResult("Quick Run", "WARN", detail="Butuh hak admin")
    result = run_command(command, timeout=60)
    state = "PASS" if result["status"] == "success" else "FAIL"
    log_action("CUSTOM", f"Quick Run ({command_type})", command, state, error=result.get("details", ""))
    return CheckResult(f"Quick Run: {command}", state, detail=result["message"][:400] or result["details"][:400])


def add_command(name: str, command_type: str, command: str, requires_admin: bool = False,
                 category: str = "GENERAL", overwrite: bool = False) -> CheckResult:
    commands = _load()
    existing = next((c for c in commands if c["name"].lower() == name.lower()), None)
    if existing and not overwrite:
        return CheckResult(f"Add Command '{name}'", "WARN", detail="Nama sudah ada",
                            recommendation="Gunakan Edit Command, atau simpan ulang dengan overwrite=True.")
    if existing and overwrite:
        existing.update({"type": command_type, "command": command, "requires_admin": requires_admin, "category": category})
    else:
        commands.append({
            "id": _next_id(commands),
            "name": name,
            "type": command_type,
            "command": command,
            "requires_admin": requires_admin,
            "category": category,
        })
    _save(commands)
    return CheckResult(f"Save Command '{name}'", "PASS", detail="Saved to config/custom_commands.json")


def edit_command(cmd_id: int, **fields) -> CheckResult:
    commands = _load()
    match = next((c for c in commands if c["id"] == cmd_id), None)
    if not match:
        return CheckResult(f"Edit Command #{cmd_id}", "FAIL", detail="Command tidak ditemukan")
    match.update(fields)
    _save(commands)
    return CheckResult(f"Edit Command '{match['name']}'", "PASS", detail="Updated")


def delete_command(cmd_id: int) -> CheckResult:
    commands = _load()
    match = next((c for c in commands if c["id"] == cmd_id), None)
    if not match:
        return CheckResult(f"Delete Command #{cmd_id}", "FAIL", detail="Command tidak ditemukan")
    commands = [c for c in commands if c["id"] != cmd_id]
    _save(commands)
    return CheckResult(f"Delete Command '{match['name']}'", "PASS", detail="Deleted")


def import_commands(json_text: str, merge: bool = True) -> CheckResult:
    import json
    try:
        incoming = json.loads(json_text).get("commands", [])
    except (ValueError, AttributeError) as e:
        return CheckResult("Import Commands", "FAIL", detail=str(e))

    commands = _load() if merge else []
    existing_names = {c["name"].lower() for c in commands}
    added = 0
    for cmd in incoming:
        if cmd.get("name", "").lower() in existing_names:
            continue
        cmd["id"] = _next_id(commands)
        commands.append(cmd)
        existing_names.add(cmd["name"].lower())
        added += 1
    _save(commands)
    return CheckResult("Import Commands", "PASS", detail=f"{added} command(s) ditambahkan")


def export_commands() -> CheckResult:
    from ..core.config import CONFIG_DIR
    path = CONFIG_DIR / FILE
    return CheckResult("Export Commands", "PASS", detail=f"Sudah tersimpan di {path}")
