@echo off
echo ==========================================
echo ULog Explorer Kurulum Sihirbazi
echo ==========================================
echo.
echo Gerekli kutuphaneler yukleniyor... Lutfen bekleyin.
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo HATA: Python bulunamadi!
    echo Lutfen once Python yukleyin (https://www.python.org/downloads/)
    echo Yuklerken "Add Python to PATH" secenegini isaretlemeyi unutmayin.
    pause
    exit /b
)

:: Kutuphaneleri yukle
pip install -r requirements_explorer.txt

echo.
echo ==========================================
echo Kurulum Tamamlandi!
echo Artik "run_explorer.bat" dosyasina tiklayarak programi acabilirsiniz.
echo ==========================================
pause
