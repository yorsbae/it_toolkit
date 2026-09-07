"""
Input Validation (PRD §41 DoD: "Input tervalidasi")
--------------------------------------------------------
Semua target yang berasal dari console.input() dan akan dipakai membangun
command shell (run_command dengan shell=True) HARUS lewat sini dulu.
Mencegah command injection sekaligus memberi pesan error yang jelas
ke teknisi kalau input salah format (bukan silently gagal di command Windows).
"""

import re
import ipaddress

# Karakter yang berbahaya kalau masuk ke string command shell=True tanpa quoting benar.
# Termasuk kutip ganda/tunggal karena banyak command kita bangun dengan f'"{value}"'
# - kalau value sendiri mengandung " bisa keluar dari konteks quoting itu.
_SHELL_METACHARACTERS = re.compile(r'[;&|`$(){}<>\n\r"\']')


class ValidationError(Exception):
    pass


def is_safe_shell_token(value: str) -> bool:
    """True kalau value TIDAK mengandung shell metacharacter berbahaya."""
    return not _SHELL_METACHARACTERS.search(value)


def validate_ip(value: str) -> str:
    value = value.strip()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValidationError(f"'{value}' bukan alamat IP yang valid.")
    return value


def validate_cidr(value: str) -> str:
    value = value.strip()
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise ValidationError(f"'{value}' bukan format subnet CIDR yang valid (contoh: 192.168.1.0/24).")
    return value


def validate_port(value) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{value}' bukan nomor port yang valid.")
    if not (1 <= port <= 65535):
        raise ValidationError(f"Port harus antara 1-65535, dapat: {port}.")
    return port


def validate_hostname_or_ip(value: str) -> str:
    """Target ping/traceroute/dsb bisa berupa IP ATAU hostname. Validasi longgar tapi
    tetap menolak shell metacharacter."""
    value = value.strip()
    if not value:
        raise ValidationError("Target tidak boleh kosong.")
    if not is_safe_shell_token(value):
        raise ValidationError(f"'{value}' mengandung karakter yang tidak diizinkan.")
    # Hostname/IP valid: huruf, angka, titik, dash, underscore, colon (IPv6)
    if not re.match(r"^[a-zA-Z0-9.\-_:]+$", value):
        raise ValidationError(f"'{value}' bukan format hostname/IP yang valid.")
    return value


def validate_adapter_name(value: str) -> str:
    """Nama adapter Windows (mis. 'Ethernet', 'Wi-Fi 2') - bebas spasi tapi tanpa
    shell metacharacter berbahaya."""
    value = value.strip()
    if not value:
        raise ValidationError("Nama adapter tidak boleh kosong.")
    if not is_safe_shell_token(value):
        raise ValidationError(f"'{value}' mengandung karakter yang tidak diizinkan.")
    return value


def validate_unc_path(value: str) -> str:
    value = value.strip()
    if not re.match(r"^\\\\[^\\]+\\.+", value):
        raise ValidationError(r"Format harus \\SERVER\ShareName atau \\SERVER\PrinterName.")
    if not is_safe_shell_token(value):
        raise ValidationError(f"'{value}' mengandung karakter yang tidak diizinkan.")
    return value


def validate_drive_letter(value: str) -> str:
    value = value.strip().rstrip(":").upper()
    if not re.match(r"^[A-Z]$", value):
        raise ValidationError(f"'{value}' bukan drive letter yang valid (harus satu huruf A-Z).")
    return value


def validate_service_name(value: str) -> str:
    """Nama service Windows: huruf/angka/underscore/dash, tanpa spasi atau shell metachar."""
    value = value.strip()
    if not value:
        raise ValidationError("Nama service tidak boleh kosong.")
    if not re.match(r"^[a-zA-Z0-9_\-.]+$", value):
        raise ValidationError(f"'{value}' bukan format nama service Windows yang valid (mis. 'Spooler', 'RpcSs').")
    return value


# Metacharacter yang HARUS diblokir di mana pun (command chaining/substitution/quote-escape),
# dipakai untuk field bebas seperti nama driver/deskripsi yang boleh mengandung tanda kurung dll.
_DANGEROUS_ONLY = re.compile(r'[;&|`$<>\n\r"\']')


def validate_free_text_for_shell(value: str, field_label: str = "Input") -> str:
    """Untuk field bebas (nama driver printer, deskripsi restore point, dll) yang boleh
    mengandung tanda kurung/spasi/titik, tapi TETAP menolak karakter shell paling berbahaya
    (; & | ` $ < > kutip, newline) supaya tidak bisa dipakai command chaining/injection."""
    value = value.strip()
    if not value:
        raise ValidationError(f"{field_label} tidak boleh kosong.")
    if _DANGEROUS_ONLY.search(value):
        raise ValidationError(f"{field_label} mengandung karakter yang tidak diizinkan (; & | ` $ < > kutip).")
    return value


def validate_mac_address(value: str) -> str:
    value = value.strip()
    cleaned = value.replace(":", "").replace("-", "")
    if not re.match(r"^[0-9A-Fa-f]{12}$", cleaned):
        raise ValidationError(f"'{value}' bukan format MAC address yang valid (12 hex digit).")
    return value
