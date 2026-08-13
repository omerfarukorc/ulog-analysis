# ULog Explorer
 
A simple and fast tool for analyzing PX4/ArduPilot flight logs (ULog).
 
## Features
 
- Upload ULog files
- Select topics and fields
- Interactive Plotly charts
- Fast performance with lazy loading
## Installation
 
### Windows
```bash
setup.bat
```
 
### Linux/Mac
```bash
chmod +x setup.sh run_explorer.sh
./setup.sh
```
 
## Running
 
### Windows
```bash
run_explorer.bat
```
 
### Linux/Mac
```bash
./run_explorer.sh
```
 
Open in your browser: **http://localhost:8050**
 
## Requirements
 
- Python 3.8+
- Dash
- Plotly
- pyulog
## Usage
 
1. Upload or select a ULog file from the left panel
2. Click on topics in the right panel to view their fields
3. Click on fields to add them to the chart
4. Analyze the data in the chart in the middle
 
