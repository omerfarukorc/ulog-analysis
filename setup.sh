#!/bin/bash

echo "========================================"
echo "ULog Explorer - Kurulum"
echo "========================================"
echo

# Python kontrolu
if ! command -v python3 &> /dev/null; then
    echo "[HATA] Python3 bulunamadi!"
    echo "Yukleyin: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[OK] Python bulundu"
echo

# Bagimliliklar
echo "Gerekli paketler yukleniyor..."
pip3 install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo "[HATA] Paket yukleme basarisiz!"
    exit 1
fi

echo
echo "========================================"
echo "[OK] Kurulum tamamlandi!"
echo
echo "Calistirmak icin: ./run_explorer.sh"
echo "========================================"
