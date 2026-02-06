# ULog Explorer

PX4/ArduPilot uçuş loglarını (ULog) analiz etmek için basit ve hızlı bir araç.

## Özellikler

- 📂 ULog dosyası yükleme
- 📊 Topic ve field seçimi
- 📈 İnteraktif Plotly grafikleri
- ⚡ Lazy loading ile hızlı performans
- 🎨 Modern dark tema

## Kurulum

### Windows
```bash
setup.bat
```

### Linux/Mac
```bash
chmod +x setup.sh run_explorer.sh
./setup.sh
```

## Çalıştırma

### Windows
```bash
run_explorer.bat
```

### Linux/Mac
```bash
./run_explorer.sh
```

Tarayıcıda açın: **http://localhost:8050**

## Gereksinimler

- Python 3.8+
- Dash
- Plotly
- pyulog

## Kullanım

1. Sol panelden ULog dosyası yükleyin veya seçin
2. Sağ panelde topic'lere tıklayarak field'ları görün
3. Field'lara tıklayarak grafiğe ekleyin
4. Ortadaki grafikte verileri analiz edin
