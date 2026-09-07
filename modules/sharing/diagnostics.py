"""
Sharing Diagnostics (PRD Phase 3 - prioritas tinggi)
------------------------------------------------------
Checks: Server service, Workstation service, RPC (RpcSs), Print Spooler,
Firewall rule File & Printer Sharing, Network Discovery.
Fix actions selalu lewat konfirmasi (PRD §35 Administrative).
"""

from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..core.config import load_json


def _load_services() -> dict:
    """Baca dari config/sharing/services.json - DoD PRD §41: 'Tidak ada
    hard-coded target yang tidak dapat dikonfigurasi'. Fallback ke default
    minimal kalau file belum ada/rusak, supaya app tetap jalan."""
    data = load_json("sharing/services.json", default=None)
    if data and data.get("services"):
        return {s["id"]: s["label"] for s in data["services"]}
    return {
        "LanmanServer": "Server (File/Printer Sharing)",
        "LanmanWorkstation": "Workstation",
        "RpcSs": "RPC",
        "Spooler": "Print Spooler",
    }


SERVICES = _load_services()


def check_service_state(service_id: str, label: str) -> CheckResult:
    result = run_command(f"sc query {service_id}", timeout=10)
    running = result["status"] == "success" and "RUNNING" in result["message"]
    state = "PASS" if running else "FAIL"
    rec = "" if running else f"Restart service '{label}' lewat menu Sharing > Fix Service."
    return CheckResult(label, state, detail="Running" if running else "Stopped", recommendation=rec)


def check_firewall_rule_group(group: str = "File and Printer Sharing") -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"(Get-NetFirewallRule -DisplayGroup \'{group}\' | Where-Object Enabled -eq True).Count"',
        timeout=10,
    )
    try:
        count = int(result["message"].strip() or "0")
    except ValueError:
        count = 0
    state = "PASS" if count > 0 else "WARN"
    rec = "" if state == "PASS" else "Aktifkan rule 'File and Printer Sharing' di Windows Defender Firewall."
    return CheckResult(f"Firewall Rule: {group}", state, detail=f"{count} rule enabled", recommendation=rec)


def check_network_discovery() -> CheckResult:
    result = run_command(
        'powershell -NoProfile -Command '
        '"(Get-NetFirewallRule -DisplayGroup \'Network Discovery\' | Where-Object Enabled -eq True).Count"',
        timeout=10,
    )
    try:
        count = int(result["message"].strip() or "0")
    except ValueError:
        count = 0
    state = "PASS" if count > 0 else "WARN"
    rec = "" if state == "PASS" else "Aktifkan Network Discovery di Advanced Sharing Settings."
    return CheckResult("Network Discovery", state, detail=f"{count} rule enabled", recommendation=rec)


def full_sharing_diagnostic() -> list:
    results = [check_service_state(sid, label) for sid, label in SERVICES.items()]
    results.append(check_firewall_rule_group())
    results.append(check_network_discovery())
    return results


def fix_restart_service(service_id: str) -> CheckResult:
    """Fix action - HARUS dipanggil setelah user confirm 'Y' di UI, dan butuh admin.
    PRD §41 DoD: 'Hasil diverifikasi setelah repair' - jadi setelah net start,
    kita cek ulang service state sungguhan (bukan cuma percaya exit code net start)."""
    if not is_admin():
        return CheckResult(f"Restart {service_id}", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(f"net stop {service_id} && net start {service_id}", timeout=30)
    command_ok = result["status"] == "success"

    verify = run_command(f"sc query {service_id}", timeout=10)
    actually_running = verify["status"] == "success" and "RUNNING" in verify["message"]

    if actually_running:
        state = "PASS"
        detail = "Restarted and verified running"
    elif command_ok:
        state = "WARN"
        detail = "Command reported success but service not verified running"
    else:
        state = "FAIL"
        detail = result["message"] or result["details"]

    return CheckResult(f"Restart {service_id}", state, detail=detail)


# ---- Item tambahan: WINDOWS CONFIGURATION (§19 baris 05-12) ----

from ..core.ps import ps_bool_check, ps_info


def check_network_profile() -> CheckResult:
    return ps_info("Network Profile", "(Get-NetConnectionProfile).NetworkCategory")


def check_smb_config() -> CheckResult:
    return ps_info("SMB Configuration", "Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol,EnableSMB2Protocol | Format-List")


def check_password_protected_sharing() -> CheckResult:
    return ps_bool_check(
        "Password Protected Sharing",
        "(Get-SmbServerConfiguration).RestrictNullSessAccess",
        recommendation_if_false="Password Protected Sharing OFF - pastikan client pakai kredensial yang benar untuk akses.",
    )


def check_smb_guest_access() -> CheckResult:
    return ps_bool_check(
        "SMB Insecure Guest Logons",
        "(Get-SmbClientConfiguration).EnableInsecureGuestLogons",
        true_state="WARN", false_state="PASS",
        recommendation_if_false="",
    )


def check_credential_manager() -> CheckResult:
    result = run_command("cmdkey /list", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    count = result["message"].count("Target:")
    return CheckResult("Credential Manager", state, detail=f"{count} saved credential(s)")


# ---- REGISTRY / POLICY (§19 baris 24-28) ----

def _registry_config() -> dict:
    return load_json("sharing/registry.json", default={
        "rpc_configuration": {
            "key_path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\Rpc",
            "value_name": "RestrictRemoteClients",
            "recommended_value": 0,
            "backup_filename": "rpc_backup.reg",
        },
        "point_and_print_policy": {
            "key_path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\Printers\\PointAndPrint",
            "value_name": "Restricted",
        },
        "anonymous_access": {
            "key_path": "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa",
            "value_name": "RestrictAnonymous",
        },
    })


def check_rpc_configuration() -> CheckResult:
    cfg = _registry_config()["rpc_configuration"]
    result = run_command(
        f'reg query "{cfg["key_path"]}" /v {cfg["value_name"]}',
        timeout=10,
    )
    exists = result["status"] == "success"
    state = "PASS" if exists else "WARN"
    rec = "" if exists else "Konfigurasi RPC restriction tidak ditemukan (biasanya default OK, tapi cek manual bila error 0x6BA/0x11B muncul)."
    return CheckResult("RPC Configuration", state, detail=result["message"] if exists else "Not configured (default)", recommendation=rec)


def rpc_registry_fix(confirm_backup: bool = True) -> list:
    """Tidak silent - selalu tampilkan langkah & tawarkan backup dulu (PRD §24).
    Path & value name diambil dari config/sharing/registry.json (bisa diubah tanpa ganti source code)."""
    from ..core.config import BACKUPS_DIR
    cfg = _registry_config()["rpc_configuration"]
    results = []
    if confirm_backup:
        backup_path = BACKUPS_DIR / cfg.get("backup_filename", "rpc_backup.reg")
        backup = run_command(f'reg export "{cfg["key_path"]}" "{backup_path}" /y', timeout=10)
        results.append(CheckResult("Registry Backup", "PASS" if backup["status"] == "success" else "WARN",
                                    detail=f"Saved to {backup_path}" if backup["status"] == "success" else backup["details"]))
    fix = run_command(
        f'reg add "{cfg["key_path"]}" /v {cfg["value_name"]} /t REG_DWORD /d {cfg.get("recommended_value", 0)} /f',
        timeout=10,
    )
    state = "PASS" if fix["status"] == "success" else "FAIL"
    results.append(CheckResult("Apply RPC Registry Fix", state, detail=fix["message"] or fix["details"]))
    return results


def check_point_and_print_policy() -> CheckResult:
    cfg = _registry_config()["point_and_print_policy"]
    result = run_command(
        f'reg query "{cfg["key_path"]}" /v {cfg["value_name"]}',
        timeout=10,
    )
    exists = result["status"] == "success"
    state = "PASS" if exists else "WARN"
    rec = "" if exists else "Point & Print Policy tidak dikonfigurasi eksplisit — kalau muncul error 'driver not allowed', konfigurasikan approved servers."
    return CheckResult("Point & Print Policy", state, detail=result["message"] if exists else "Not configured", recommendation=rec)


def check_anonymous_ipc_access() -> CheckResult:
    cfg = _registry_config()["anonymous_access"]
    return ps_bool_check(
        "Anonymous/IPC$ Access restricted",
        f"[bool](Get-ItemProperty '{cfg['key_path']}' -Name {cfg['value_name']} -ErrorAction SilentlyContinue).{cfg['value_name']}",
        true_state="WARN", false_state="PASS",
        recommendation_if_false="",
    )


def registry_backup(key_path: str, backup_name: str) -> CheckResult:
    from ..core.config import BACKUPS_DIR
    out_path = BACKUPS_DIR / f"{backup_name}.reg"
    result = run_command(f'reg export "{key_path}" "{out_path}" /y', timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Registry Backup", state, detail=str(out_path) if state == "PASS" else result["details"])


# ---- SPOOLER DEPENDENCIES ----

def check_spooler_dependencies() -> CheckResult:
    result = run_command('sc qc Spooler', timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Spooler Dependencies", state, detail=result["message"][:300] or result["details"])


# ---- REPAIR (§19 baris 19-23) ----

def restart_sharing_services() -> list:
    results = []
    for svc in SERVICES:
        results.append(fix_restart_service(svc))
    return results


def reset_sharing_configuration() -> CheckResult:
    if not is_admin():
        return CheckResult("Reset Sharing Configuration", "WARN", detail="Butuh hak admin")
    run_command("netsh advfirewall firewall set rule group=\"File and Printer Sharing\" new enable=Yes", timeout=15)
    result = run_command("netsh advfirewall firewall set rule group=\"Network Discovery\" new enable=Yes", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Reset Sharing Configuration", state, detail="Firewall rules sharing di-enable ulang")


def clear_saved_credentials(target: str = None) -> CheckResult:
    cmd = f'cmdkey /delete:{target}' if target else 'cmdkey /list'
    if not target:
        return CheckResult("Clear Saved Credentials", "WARN", detail="Perlu target spesifik untuk delete, gunakan cmdkey /list dulu.")
    result = run_command(cmd, timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Clear Credential {target}", state, detail=result["message"] or result["details"])


# ---- FULL DIAGNOSTIC (menggabungkan semua, PRD §20) ----

def full_diagnostic_extended() -> list:
    """Versi lengkap Full Sharing Diagnostic PRD §20, gabung Network+Sharing+Services+Auth+Registry."""
    from ..network.advanced import check_adapter
    from ..network.ip_config import verify_after_change

    results = []
    results.append(CheckResult("--- NETWORK ---", "INFO"))
    results += check_adapter()
    results += verify_after_change()

    results.append(CheckResult("--- WINDOWS SHARING ---", "INFO"))
    results.append(check_network_discovery())
    results.append(check_firewall_rule_group())
    results.append(check_network_profile())
    results.append(check_smb_guest_access())
    results.append(check_password_protected_sharing())

    results.append(CheckResult("--- SERVICES ---", "INFO"))
    for sid, label in SERVICES.items():
        results.append(check_service_state(sid, label))
    results.append(check_spooler_dependencies())

    results.append(CheckResult("--- AUTHENTICATION ---", "INFO"))
    results.append(check_credential_manager())
    results.append(check_access_token())
    results.append(check_anonymous_ipc_access())

    results.append(CheckResult("--- REGISTRY / POLICY ---", "INFO"))
    results.append(check_rpc_configuration())
    results.append(check_point_and_print_policy())

    return results


# ---- Item tambahan hasil review PRD lanjutan ----

def check_access_token() -> CheckResult:
    """PRD §Authentication - Access Token check."""
    result = run_command("whoami /groups", timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    admin_in_token = "S-1-5-32-544" in result["message"] or "Administrators" in result["message"]
    detail = "Administrators group present in token" if admin_in_token else "Standard user token"
    return CheckResult("Access Token", state, detail=detail)


# ---- Guided Remediation: "found issue -> offer fix -> confirm -> apply -> verify" ----
# PRD §24: "Registry fixes must never run silently" - prinsip ini berlaku untuk SEMUA
# fix di sini, bukan cuma registry. Tidak ada yang auto-enable tanpa konfirmasi user.

def enable_firewall_rule_group(group: str = "File and Printer Sharing") -> CheckResult:
    if not is_admin():
        return CheckResult(f"Enable Firewall Rule: {group}", "WARN", detail="Butuh hak admin")
    result = run_command(f'netsh advfirewall firewall set rule group="{group}" new enable=Yes', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Enable Firewall Rule: {group}", state, detail=result["message"] or "Enabled")


def enable_network_discovery() -> CheckResult:
    if not is_admin():
        return CheckResult("Enable Network Discovery", "WARN", detail="Butuh hak admin")
    result = run_command('netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Enable Network Discovery", state, detail=result["message"] or "Enabled")


def enable_password_protected_sharing() -> CheckResult:
    if not is_admin():
        return CheckResult("Enable Password Protected Sharing", "WARN", detail="Butuh hak admin")
    result = run_command(
        'powershell -NoProfile -Command "Set-SmbServerConfiguration -RestrictNullSessAccess $true -Confirm:$false"',
        timeout=15,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Enable Password Protected Sharing", state, detail=result["message"] or "Enabled")


def disable_smb_guest_access() -> CheckResult:
    if not is_admin():
        return CheckResult("Disable SMB Insecure Guest Logons", "WARN", detail="Butuh hak admin")
    result = run_command(
        'powershell -NoProfile -Command "Set-SmbClientConfiguration -EnableInsecureGuestLogons $false -Confirm:$false"',
        timeout=15,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult("Disable SMB Insecure Guest Logons", state, detail=result["message"] or "Disabled")


def _remediation_registry() -> dict:
    """Peta label CheckResult -> (fix_function, verify_function, needs_service_id).
    Dipakai oleh guided_remediation() untuk tahu item mana yang punya fix otomatis
    tersedia, dan item mana yang cuma bisa direkomendasikan manual."""
    registry = {
        "Network Discovery": (enable_network_discovery, check_network_discovery),
        f"Firewall Rule: File and Printer Sharing": (enable_firewall_rule_group, check_firewall_rule_group),
        "Password Protected Sharing": (enable_password_protected_sharing, check_password_protected_sharing),
        "SMB Insecure Guest Logons": (disable_smb_guest_access, check_smb_guest_access),
    }
    for sid, label in SERVICES.items():
        registry[label] = (
            lambda sid=sid: fix_restart_service(sid),
            lambda sid=sid, label=label: check_service_state(sid, label),
        )
    registry["RPC Configuration"] = (lambda: rpc_registry_fix(confirm_backup=True), check_rpc_configuration)
    return registry


def guided_remediation(results: list, confirm_fn, show_fn) -> list:
    """
    Iterasi hasil diagnostic, untuk tiap item FAIL/WARN yang punya fix terdaftar,
    TAWARKAN fix (tidak pernah otomatis tanpa tanya - sesuai PRD §24).

    confirm_fn: fungsi (prompt: str) -> bool, dari UI layer (modules.core.ui.confirm)
    show_fn: fungsi (results: list) -> None, dari UI layer (modules.core.ui.show_results)

    Return: list hasil fix yang dijalankan (untuk dimasukkan ke report).
    """
    registry = _remediation_registry()
    fix_results = []

    for r in results:
        if r.state not in ("FAIL", "WARN"):
            continue
        entry = registry.get(r.label)
        if not entry:
            continue
        fix_fn, verify_fn = entry
        if confirm_fn(f"'{r.label}' bermasalah ({r.detail}). Aktifkan/perbaiki sekarang?"):
            fix_result = fix_fn()
            show_fn([fix_result])
            fix_results.append(fix_result)
            from ..core.logger import log_action
            log_action("SHARING", f"GUIDED FIX: {r.label}", "LOCAL", fix_result.state)
            if fix_result.state == "PASS":
                verify_result = verify_fn()
                verify_result.label = f"Verify: {verify_result.label}"
                show_fn([verify_result])
                fix_results.append(verify_result)

    return fix_results


# ---- Item yang terlewat dari flat list persis PRD §19 (40 item) ----

def check_rpc_endpoint_mapper(target: str = "127.0.0.1") -> CheckResult:
    """Beda dari 'Check RPC' (service RpcSs) - ini cek port 135 (endpoint mapper)
    benar-benar merespon, termasuk untuk target remote."""
    from ..network.advanced import check_port
    r = check_port(target, 135)
    r.label = "RPC Endpoint Mapper" + (f" ({target})" if target != "127.0.0.1" else "")
    return r


def check_firewall_sharing_rules() -> CheckResult:
    """Alias eksplisit untuk item PRD [09] Firewall Sharing Rules -
    sama isinya dengan check_firewall_rule_group tapi nama fungsi mengikuti PRD persis."""
    return check_firewall_rule_group()
