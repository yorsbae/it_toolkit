"""
Print Management (terinspirasi PaperCut)
==========================================
Toolkit ini PORTABLE - dibawa dari flashdisk/laptop teknisi ke banyak PC,
BUKAN aplikasi terinstall permanen. Karena itu modul ini TIDAK bisa (dan
tidak berusaha) meniru PaperCut secara penuh, yang sebenarnya adalah print
server terpusat dengan database sendiri. Yang bisa ditiru dan tetap 100%
portable adalah bagian yang paling sering dibutuhkan teknisi lapangan:

  - Job history (siapa print apa, kapan, berapa halaman)
  - Live queue (job yang lagi antri, mirip "Jobs Pending Release" PaperCut)
  - Usage report per user & per printer (top users/printers)
  - Estimasi biaya per halaman (cost tracking sederhana)
  - Export ke CSV (ledger, bisa dibuka Excel)

Semua data diambil dari fitur BAWAAN Windows sendiri: Windows Print Service
sudah mencatat setiap job selesai print ke Event Log
"Microsoft-Windows-PrintService/Operational" (Event ID 307), lengkap dengan
nama dokumen, user, printer, ukuran file, dan jumlah halaman - PERSIS data
yang PaperCut pakai untuk accounting-nya, hanya saja di sini dibaca langsung
dari PC yang bersangkutan tanpa perlu install apa pun.

KETERBATASAN (harus jujur ke teknisi, bukan pura-pura setara PaperCut):
  - Log ini MATI secara default di Windows -> job history kosong sampai
    [Enable Print Job Logging] dijalankan sekali di PC tsb (butuh admin).
  - Data historis SEBELUM logging diaktifkan tidak bisa dipulihkan.
  - Windows tidak mencatat page dari sisi PC ini kalau job dikirim/di-render
    di print SERVER lain (redirect) - jalankan modul ini di PC/server yang
    benar-benar memproses job tsb.
  - Tidak ada pembedaan otomatis warna vs hitam-putih (itu perlu driver
    accounting khusus seperti PaperCut asli) -> biaya dihitung flat per
    halaman, bisa diubah lewat [Set Cost per Page].
"""

import re
import csv
import json as _json
from datetime import datetime, timedelta

from ..core.executor import run_command, is_admin
from ..core.status import CheckResult
from ..core.config import load_json, save_json, REPORTS_DIR

LOG_NAME = "Microsoft-Windows-PrintService/Operational"

# Event ID 307 message (Windows, English locale):
# "Document 3, Report.pdf owned by DOMAIN\user was printed on HP-LaserJet
#  through port 192.168.1.50.  Size in bytes: 245312.  Pages printed: 2.
#  No user action is required."
_JOB_RE = re.compile(
    r"Document\s+\d+,\s*(?P<doc>.+?)\s+owned by\s+(?P<user>\S+)\s+was printed on\s+"
    r"(?P<printer>.+?)\s+(?:through|via)\s+port\s+.+?\.\s*"
    r"Size in bytes:\s*(?P<size>\d+)\.\s*Pages printed:\s*(?P<pages>\d+)\.",
    re.IGNORECASE | re.DOTALL,
)


# ---------------------------------------------------------------- Logging --

def check_logging_enabled() -> CheckResult:
    result = run_command(
        f'powershell -NoProfile -Command "(Get-WinEvent -ListLog \'{LOG_NAME}\').IsEnabled"',
        timeout=10,
    )
    val = result["message"].strip().lower()
    if val == "true":
        return CheckResult("Print Job Logging", "PASS", detail="Aktif")
    if val == "false":
        return CheckResult(
            "Print Job Logging", "WARN", detail="Nonaktif (default Windows)",
            recommendation="Jalankan [Enable Print Job Logging] (butuh admin) supaya job history mulai tercatat.",
        )
    return CheckResult("Print Job Logging", "UNKNOWN", detail=result["details"] or "Tidak bisa membaca status log")


def enable_logging() -> CheckResult:
    if not is_admin():
        return CheckResult(
            "Enable Print Job Logging", "WARN", detail="Butuh hak admin",
            recommendation="Jalankan ulang aplikasi as Administrator, lalu ulangi.",
        )
    result = run_command(f'wevtutil set-log "{LOG_NAME}" /enabled:true', timeout=15)
    state = "PASS" if result["status"] == "success" else "FAIL"
    detail = "Logging diaktifkan - job print mulai sekarang akan tercatat" if state == "PASS" else result["details"]
    return CheckResult("Enable Print Job Logging", state, detail=detail)


# ------------------------------------------------------------- Job fetch --

def get_print_jobs(start: datetime, end: datetime = None, limit: int = 1000):
    """Ambil job history dari Windows Print Service log.
    Return (jobs: list[dict], error: str|None). error=None + jobs=[] artinya
    memang belum ada job tercatat pada rentang tsb (bukan error)."""
    end = end or datetime.now()
    start_s = start.strftime("%m/%d/%Y %H:%M:%S")
    end_s = end.strftime("%m/%d/%Y %H:%M:%S")
    ps = (
        f"$e = Get-WinEvent -FilterHashtable @{{LogName='{LOG_NAME}';Id=307;"
        f"StartTime='{start_s}';EndTime='{end_s}'}} -MaxEvents {limit} -ErrorAction SilentlyContinue; "
        f"$e | Select-Object TimeCreated,Message | ConvertTo-Json -Compress"
    )
    result = run_command(f'powershell -NoProfile -Command "{ps}"', timeout=30)
    raw = result["message"].strip()
    if result["status"] != "success" or not raw:
        return [], None  # belum ada job (wajar) atau log belum aktif

    try:
        data = _json.loads(raw)
    except Exception as e:
        return [], f"Gagal parse hasil event log: {e}"
    if isinstance(data, dict):
        data = [data]

    jobs = []
    for item in data:
        msg = item.get("Message", "") or ""
        m = _JOB_RE.search(msg)
        if not m:
            continue
        jobs.append({
            "time": (item.get("TimeCreated") or "")[:19].replace("T", " "),
            "user": m.group("user"),
            "document": m.group("doc").strip()[:60],
            "printer": m.group("printer").strip(),
            "pages": int(m.group("pages")),
            "size_kb": round(int(m.group("size")) / 1024, 1),
        })
    jobs.sort(key=lambda j: j["time"], reverse=True)
    return jobs, None


def jobs_today():
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return get_print_jobs(start)


def jobs_last_days(days: int):
    start = datetime.now() - timedelta(days=days)
    return get_print_jobs(start)


def search_jobs(jobs: list, keyword: str) -> list:
    kw = keyword.strip().lower()
    if not kw:
        return jobs
    return [
        j for j in jobs
        if kw in j["user"].lower() or kw in j["printer"].lower() or kw in j["document"].lower()
    ]


# ------------------------------------------------------------- Live queue --

def live_queue_all() -> list:
    """Snapshot job yang SEDANG di antrian printer lokal saat ini juga
    (mirip layar 'Jobs Pending Release' di PaperCut)."""
    result = run_command(
        'powershell -NoProfile -Command '
        '"Get-PrintJob -ErrorAction SilentlyContinue | '
        'Select-Object PrinterName,DocumentName,SubmittedBy,PagesPrinted,TotalPages,JobStatus | '
        'ConvertTo-Json -Compress"',
        timeout=15,
    )
    raw = result["message"].strip()
    if result["status"] != "success" or not raw:
        return []
    try:
        data = _json.loads(raw)
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    return data


# ------------------------------------------------------------ Aggregation --

def usage_by_user(jobs: list) -> list:
    agg = {}
    for j in jobs:
        row = agg.setdefault(j["user"], {"jobs": 0, "pages": 0})
        row["jobs"] += 1
        row["pages"] += j["pages"]
    return sorted(
        [{"user": u, **v} for u, v in agg.items()],
        key=lambda x: x["pages"], reverse=True,
    )


def usage_by_printer(jobs: list) -> list:
    agg = {}
    for j in jobs:
        row = agg.setdefault(j["printer"], {"jobs": 0, "pages": 0})
        row["jobs"] += 1
        row["pages"] += j["pages"]
    return sorted(
        [{"printer": p, **v} for p, v in agg.items()],
        key=lambda x: x["pages"], reverse=True,
    )


# ------------------------------------------------------------------ Cost --

def get_cost_config() -> dict:
    return load_json("print_management.json", default={"cost_per_page": 300, "currency": "Rp"})


def save_cost_config(cost_per_page: float, currency: str = "Rp") -> None:
    save_json("print_management.json", {"cost_per_page": cost_per_page, "currency": currency})


def cost_report_by_user(jobs: list) -> list:
    cfg = get_cost_config()
    rate = cfg.get("cost_per_page", 300)
    currency = cfg.get("currency", "Rp")
    rows = usage_by_user(jobs)
    for r in rows:
        r["cost"] = r["pages"] * rate
        r["currency"] = currency
    return rows


# ---------------------------------------------------------------- Export --

def export_csv(jobs: list, filename: str = None):
    filename = filename or f"{datetime.now():%Y-%m-%d}-print-job-history.csv"
    path = REPORTS_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Time", "User", "Document", "Printer", "Pages", "Size (KB)"])
        for j in jobs:
            w.writerow([j["time"], j["user"], j["document"], j["printer"], j["pages"], j["size_kb"]])
    return path
