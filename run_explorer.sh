#!/bin/bash

echo "========================================"
echo "ULog Explorer"
echo "========================================"
echo
echo "Tarayicida acin: http://localhost:8050"
echo "Kapatmak icin: Ctrl+C"
echo

# Tarayici ac (opsiyonel)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8050 &
elif command -v open &> /dev/null; then
    open http://localhost:8050 &
fi

python3 ulog_dash.py
