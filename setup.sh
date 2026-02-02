#!/bin/bash

echo "=========================================="
echo "ULog Explorer Kurulum Sihirbazi"
echo "=========================================="
echo
echo "Gerekli kutuphaneler yukleniyor... Lutfen bekleyin."
echo

# Python kontrolu
if ! command -v python3 &> /dev/null
then
    echo "HATA: Python3 bulunamadi!"
    echo "Lutfen once Python yukleyin."
    echo "Ubuntu/Debian icin:"
    echo "  sudo apt install python3 python3-pip"
    echo
    exit 1
fi

# Pip kontrolu
if ! command -v pip3 &> /dev/null
then
    echo "HATA: pip3 bulunamadi!"
    echo "Lutfen pip yukleyin:"
    echo "  sudo apt install python3-pip"
    echo
    exit 1
fi

# Kutuphaneleri yukle
pip3 install -r requirements_explorer.txt

echo
echo "=========================================="
echo "Kurulum Tamamlandi!"
echo "Artik './run_explorer.sh' calistirarak programi acabilirsiniz."
echo "=========================================="
