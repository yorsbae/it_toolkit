"""
Report Engine
-------------
Men-generate report TXT + JSON dari list CheckResult.
Nama file otomatis: reports/YYYY-MM-DD-HOSTNAME-MODULE.txt
"""

import json
import socket
from datetime import datetime
from .config import REPORTS_DIR, load_config
from .status import symbol


def generate_report(module_name: str, results: list, technician: str = None):
    cfg = load_config()
    technician = technician or cfg.get("technician_name", "IT SUPPORT")
    hostname = socket.gethostname()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")       # untuk nama file (sortable)
    date_display = now.strftime("%d-%m-%Y")   # untuk isi laporan (PRD: format DD-MM-YYYY)
    time_str = now.strftime("%H:%M")

    base_name = f"{date_str}-{hostname}-{module_name.upper()}"
    txt_path = REPORTS_DIR / f"{base_name}.txt"
    json_path = REPORTS_DIR / f"{base_name}.json"

    fail_count = sum(1 for r in results if r.state == "FAIL")
    warn_count = sum(1 for r in results if r.state == "WARN")

    if fail_count:
        overall = "ISSUE DETECTED"
    elif warn_count:
        overall = "WARNING"
    else:
        overall = "HEALTHY"

    lines = [
        "IT SUPPORT DIAGNOSTIC REPORT",
        "\u2500" * 38,
        "",
        f"DATE       : {date_display} {time_str}",
        f"TECHNICIAN : {technician}",
        f"HOSTNAME   : {hostname}",
        f"MODULE     : {module_name}",
    ]
    for r in results:
        if r.label.startswith("---") and r.label.endswith("---") and r.state == "INFO":
            # Header kategori (mis. "--- NETWORK ---") -> tampil polos sesuai contoh PRD §31,
            # bukan "[*] --- NETWORK ---"
            category = r.label.strip("- ").strip()
            lines.append("")
            lines.append(category)
        else:
            lines.append(f"{symbol(r.state)} {r.label}" + (f" - {r.detail}" if r.detail else ""))

    lines += ["", "RESULT", overall, "", f"Report: {txt_path}"]

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": f"{date_display} {time_str}",
                "technician": technician,
                "hostname": hostname,
                "module": module_name,
                "results": [r.to_dict() for r in results],
                "overall": overall,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    html_path = None
    if "html" in [f.lower() for f in cfg.get("report_formats", ["txt", "json"])]:
        html_path = REPORTS_DIR / f"{base_name}.html"
        _write_html_report(html_path, module_name, technician, hostname, date_display, time_str, results, overall)

    return txt_path, json_path, overall


_HTML_STATE_COLOR = {
    "PASS": "#22c55e", "FAIL": "#ef4444", "WARN": "#eab308",
    "UNKNOWN": "#06b6d4", "SKIP": "#94a3b8", "INFO": "#06b6d4",
}


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def _write_html_report(path, module_name, technician, hostname, date_display, time_str, results, overall):
    """Format HTML sederhana, satu file self-contained (tanpa dependency eksternal),
    supaya bisa dibuka langsung di browser mana pun tanpa koneksi internet."""
    rows_html = []
    for r in results:
        if r.label.startswith("---") and r.label.endswith("---") and r.state == "INFO":
            category = _html_escape(r.label.strip("- ").strip())
            rows_html.append(f'<tr class="category"><td colspan="2">{category}</td></tr>')
            continue
        color = _HTML_STATE_COLOR.get(r.state, "#94a3b8")
        detail = f" - {_html_escape(r.detail)}" if r.detail else ""
        rec = f'<div class="rec">-&gt; {_html_escape(r.recommendation)}</div>' if r.recommendation else ""
        rows_html.append(
            f'<tr><td><span class="badge" style="background:{color}">{r.state}</span></td>'
            f'<td>{_html_escape(r.label)}{detail}{rec}</td></tr>'
        )

    overall_color = {"HEALTHY": "#22c55e", "WARNING": "#eab308", "ISSUE DETECTED": "#ef4444"}.get(overall, "#94a3b8")

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>IT Support Diagnostic Report - {_html_escape(module_name)}</title>
<style>
  body {{ font-family: 'Segoe UI', Consolas, monospace; background:#0f172a; color:#e2e8f0; padding:2rem; }}
  .container {{ max-width: 800px; margin: 0 auto; }}
  h1 {{ color:#06b6d4; border-bottom: 2px solid #06b6d4; padding-bottom: 0.5rem; }}
  .meta {{ color:#94a3b8; margin-bottom: 1.5rem; line-height: 1.8; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  tr.category td {{ font-weight: bold; color:#06b6d4; padding-top: 1.25rem; border-bottom: 1px solid #06b6d4; }}
  .badge {{ display:inline-block; padding: 0.15rem 0.6rem; border-radius: 4px; font-weight:bold; font-size:0.85rem; color:#0f172a; min-width: 3.5rem; text-align:center; }}
  .rec {{ color:#eab308; font-size:0.9rem; margin-top:0.25rem; }}
  .result-box {{ margin-top:2rem; padding:1rem; border-radius:8px; background:{overall_color}22; border:1px solid {overall_color}; }}
  .result-box strong {{ color:{overall_color}; font-size:1.2rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>IT SUPPORT DIAGNOSTIC REPORT</h1>
  <div class="meta">
    DATE&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {date_display} {time_str}<br>
    TECHNICIAN : {_html_escape(technician)}<br>
    HOSTNAME&nbsp;&nbsp;&nbsp;: {_html_escape(hostname)}<br>
    MODULE&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {_html_escape(module_name)}
  </div>
  <table>
    {"".join(rows_html)}
  </table>
  <div class="result-box">RESULT: <strong>{overall}</strong></div>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
