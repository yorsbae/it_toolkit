@echo off
setlocal
title GHOST IT TOOLBOX - Builder
color 0B
echo ============================================================
echo   GHOST IT TOOLBOX - BUILD SCRIPT
echo   Hasil akhir: dist\GhostITToolbox.exe
echo   Sekali di-build, file exe ini portable:
echo   copy ke PC mana pun / flashdisk, tinggal DOUBLE CLICK.
echo   PC target TIDAK perlu install Python atau app lain.
echo ============================================================
echo.

REM --- Cek python tersedia di mesin BUILDER ini (bukan target) ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di PC ini.
    echo Build HANYA perlu Python di PC yang mem-build ^(sekali saja^).
    echo Hasil exe-nya nanti TIDAK butuh Python di PC lain.
    echo Download Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

pip install -r requirements.txt

pyinstaller --onefile --console --clean --noconfirm ^
  --name GhostITToolbox ^
  --icon "assets\ghost_toolbox.ico" ^
  --uac-admin ^
  --add-data "config;config" ^
  --add-data "assets;assets" ^
  main.py

echo.
if exist "dist\GhostITToolbox.exe" (
    echo ============================================================
    echo   BUILD SELESAI
    echo   File   : dist\GhostITToolbox.exe
    echo   Cara pakai di PC lain: copy file exe ini + folder config
    echo   ke flashdisk / folder mana pun, lalu double click.
    echo   Klik "Yes" saat muncul UAC ^(agar bisa akses admin tools^).
    echo ============================================================
) else (
    echo [ERROR] Build gagal. Cek pesan error PyInstaller di atas.
)
pause
