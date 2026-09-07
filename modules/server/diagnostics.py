"""
Server Connectivity Diagnostics
-----------------------------------
Daftar server diambil dari config/servers.json (bukan hardcode di source code,
sesuai Definition of Done PRD §41).
"""

from ..core.config import load_json
from ..core.status import CheckResult
from ..network.basic import ping_target
from ..network.advanced import check_port


def get_server_list() -> list:
    return load_json("servers.json", default={"servers": []}).get("servers", [])


def diagnose_server(server: dict) -> list:
    results = [ping_target(server["ip"])]
    for port in server.get("ports", []):
        results.append(check_port(server["ip"], port))
    return results


def diagnose_all_servers() -> list:
    results = []
    for server in get_server_list():
        results.append(CheckResult(f"--- {server['name']} ({server['ip']}) ---", "INFO"))
        results += diagnose_server(server)
    return results


# ---- Item tambahan PRD Server Module (16 item total) ----

from ..core.executor import run_command, is_admin
from ..core.ps import ps_info


def rpc_test(target: str) -> CheckResult:
    return check_port(target, 135)


def smb_test(target: str) -> CheckResult:
    return check_port(target, 445)


def wmi_test(target: str) -> CheckResult:
    result = run_command(f'powershell -NoProfile -Command "Test-WSMan -ComputerName {target} -ErrorAction SilentlyContinue"', timeout=10)
    state = "PASS" if result["status"] == "success" else "FAIL"
    rec = "" if state == "PASS" else "Pastikan WMI/RPC diizinkan di firewall target dan kredensial cukup."
    return CheckResult(f"WMI Test {target}", state, detail=result["message"][:200] or result["details"][:200], recommendation=rec)


def winrm_test(target: str) -> CheckResult:
    return check_port(target, 5985)


def rdp_test(target: str) -> CheckResult:
    return check_port(target, 3389)


def server_port_scan(target: str) -> list:
    return [check_port(target, p) for p in (135, 139, 445, 3389, 5985, 80, 443)]


def server_services(target: str) -> list:
    services = ["LanmanServer", "LanmanWorkstation", "RpcSs"]
    results = []
    for svc in services:
        result = run_command(f"sc \\\\{target} query {svc}", timeout=15)
        running = result["status"] == "success" and "RUNNING" in result["message"]
        state = "PASS" if running else "FAIL"
        results.append(CheckResult(f"{target}: {svc}", state, detail="Running" if running else "Stopped/Unreachable"))
    return results


def remote_services(target: str) -> CheckResult:
    return ps_info(f"Remote Services {target}",
                    f"Get-Service -ComputerName {target} -ErrorAction SilentlyContinue | "
                    f"Where-Object Status -ne 'Running' | Select-Object -First 10 Name,Status | Format-Table -HideTableHeaders")


def restart_server(target: str) -> CheckResult:
    if not is_admin():
        return CheckResult(f"Restart {target}", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(f"shutdown /r /m \\\\{target} /t 30 /c \"Restart by IT Support Toolkit\"", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Restart {target}", state, detail=result["message"] or "Restart scheduled in 30s")


def shutdown_server(target: str) -> CheckResult:
    if not is_admin():
        return CheckResult(f"Shutdown {target}", "WARN", detail="Butuh hak admin",
                            recommendation="Jalankan ulang aplikasi as Administrator.")
    result = run_command(f"shutdown /s /m \\\\{target} /t 30 /c \"Shutdown by IT Support Toolkit\"", timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Shutdown {target}", state, detail=result["message"] or "Shutdown scheduled in 30s")


def remote_cmd(target: str, command: str) -> CheckResult:
    result = run_command(f'winrs -r:{target} "{command}"', timeout=30)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remote CMD @ {target}", state, detail=result["message"][:400] or result["details"][:400])


def remote_powershell(target: str, command: str) -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command '
        f'"Invoke-Command -ComputerName {target} -ScriptBlock {{ {command} }}"',
        timeout=30,
    )
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Remote PowerShell @ {target}", state, detail=result["message"][:400] or result["details"][:400])


def server_information(target: str) -> CheckResult:
    result = run_command(f"systeminfo /s {target}", timeout=30)
    state = "PASS" if result["status"] == "success" else "FAIL"
    return CheckResult(f"Server Information {target}", state, detail=result["message"][:500] or result["details"][:300])


def server_diagnostics(target: str) -> list:
    results = [ping_target(target)]
    results.append(rpc_test(target))
    results.append(smb_test(target))
    results.append(wmi_test(target))
    results.append(winrm_test(target))
    results.append(rdp_test(target))
    results += server_services(target)
    return results
