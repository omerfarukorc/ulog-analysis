#!/bin/bash

echo "ULog Explorer Baslatiliyor..."
echo "Lutfen bekleyin..."

# Persistent dizini olustur
if [ ! -d "uploaded_ulogs" ]; then
    mkdir "uploaded_ulogs"
fi

# Streamlit uygulamasini calistir
python3 -m streamlit run ulog_explorer.py

# Terminal hemen kapanmasin diye
read -p "Cikmak icin ENTER'a basin..."
