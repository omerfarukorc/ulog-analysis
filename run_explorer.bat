@echo off
title ULog Explorer
echo ========================================
echo ULog Explorer
echo ========================================
echo.
echo Tarayicida aciliyor: http://localhost:8050
echo Kapatmak icin: Ctrl+C
echo.
start http://localhost:8050
python ulog_dash.py
