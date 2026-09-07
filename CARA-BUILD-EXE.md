# Cara Membuat GhostITToolbox.exe (Sekali Saja)

Target akhir: **1 file `.exe`** yang bisa di-double-click di PC mana pun,
tanpa install Python / app pihak ketiga apa pun di PC target.

Python **hanya** dibutuhkan di **PC untuk build** (satu kali). Setelah exe
jadi, exe itu portable dan tidak butuh Python lagi di PC lain.

## Opsi A - Build di PC Windows sendiri (paling cepat, offline setelah build)

1. Install Python 3.10+ di PC kamu (builder), centang "Add to PATH" saat install.
2. Extract folder `IT-SUPPORT-TOOLKIT`.
3. Double click **`build.bat`**.
4. Tunggu sampai selesai -> hasil ada di `dist\GhostITToolbox.exe`.
5. Copy `GhostITToolbox.exe` (+ folder `config`, opsional `assets`) ke
   flashdisk / PC mana pun. Tinggal double click untuk jalan.

## Opsi B - Build otomatis via GitHub Actions (tidak perlu install apa pun sendiri)

1. Push folder ini ke repo GitHub (bisa privat).
2. Buka tab **Actions** di repo -> workflow **"Build Ghost IT Toolbox EXE"**
   akan otomatis jalan (atau klik "Run workflow" manual).
3. GitHub akan build di Windows runner mereka, lalu upload hasil exe sebagai
   **Artifact** bernama `GhostITToolbox`.
4. Download artifact-nya (berupa .zip berisi GhostITToolbox.exe), extract,
   pakai di PC mana pun.

## Kenapa bukan langsung `.cmd`?

File `.cmd`/`.bat` cuma berisi teks perintah - dia butuh Python sudah
terpasang di PC yang menjalankannya supaya bisa membaca kode `main.py`.
Karena tujuan kamu adalah "tanpa install app pihak ketiga seperti Python"
di PC target, solusi yang benar adalah **compile ke `.exe`** (lewat
PyInstaller), bukan ubah ke `.cmd`. Hasil `.exe` sudah membungkus seluruh
Python + library di dalamnya, jadi PC target tidak perlu apa-apa lagi.

## Catatan

- Saat exe dijalankan, Windows akan memunculkan prompt UAC (karena tool ini
  butuh akses admin untuk diagnostik jaringan/hardware) - klik **Yes**.
- Antivirus kadang mem-flag exe hasil PyInstaller sebagai false positive
  (karena caranya packing mirip malware packer, walau isinya bersih).
  Kalau ini dipakai luas, pertimbangkan code-signing certificate supaya
  tidak kena SmartScreen/AV warning di PC lain.
