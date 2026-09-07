"""
Core Config Loader
-------------------
Semua path dihitung relatif terhadap lokasi executable/script,
BUKAN terhadap current working directory. Ini yang membuat toolkit
tetap portable walau dipindah-pindah ke PC lain atau dijalankan dari
folder mana pun / dari flashdisk.
"""

import json
import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """
    Mengembalikan folder tempat aplikasi berada.
    - Jika dijalankan sebagai .exe hasil PyInstaller (--onefile),
      sys.frozen bernilai True dan sys.executable menunjuk ke exe itu sendiri.
    - Jika dijalankan sebagai script .py biasa, gunakan lokasi file ini.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

for d in (CONFIG_DIR, CONFIG_DIR / "sharing", REPORTS_DIR, LOGS_DIR, BACKUPS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def load_json(filename: str, default=None):
    """filename bisa berisi subfolder, mis. 'sharing/errors.json'."""
    path = CONFIG_DIR / filename
    if not path.exists():
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data):
    path = CONFIG_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config():
    return load_json(
        "config.json",
        default={
            "app_name": "IT SUPPORT TOOLKIT",
            "version": "1.0.0",
            "technician_name": "IT SUPPORT",
        },
    )
