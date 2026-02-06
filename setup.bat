@echo off
title ULog Explorer Setup
echo ========================================
echo ULog Explorer - Kurulum
echo ========================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo Python'u yukleyin: https://python.org
    pause
    exit /b 1
)

echo [OK] Python bulundu
echo.

:: Bagimliliklar
echo Gerekli paketler yukleniyor...
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo [HATA] Paket yukleme basarisiz!
    pause
    exit /b 1
)

echo.
echo ========================================
echo [OK] Kurulum tamamlandi!
echo.
echo Calistirmak icin: run_explorer.bat
echo ========================================
pause
