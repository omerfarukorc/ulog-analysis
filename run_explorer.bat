@echo off
echo ULog Explorer Baslatiliyor...
echo Lutfen bekleyin...

:: Persistent dizini olustur
if not exist "uploaded_ulogs" mkdir "uploaded_ulogs"

:: Streamlit uygulamasini çalıştir
python -m streamlit run ulog_explorer.py

pause
