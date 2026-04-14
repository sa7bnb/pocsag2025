#!/bin/bash
# ============================================================
# POCSAG 2025 - Installationsskript for Raspberry Pi
# ============================================================

# 1. Uppdatera system
sudo apt update && sudo apt upgrade -y
sudo apt install git rtl-sdr multimon-ng python3-pip -y

# 2. Klona repo
git clone https://github.com/sa7bnb/pocsag2025.git
cd /home/sa7bnb/pocsag2025

# 3. Installera Python-beroenden
python3 -m pip install flask pyproj werkzeug gunicorn --break-system-packages

# 4. Lagg till ~/.local/bin i PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

# 5. Blockera RTL-SDR kernel-drivrutin
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true

# 6. Skapa systemd-tjanst
sudo tee /etc/systemd/system/pocsag.service > /dev/null <<SERVICE
[Unit]
Description=POCSAG 2025 - By SA7BNB
After=network.target

[Service]
User=sa7bnb
WorkingDirectory=/home/sa7bnb/pocsag2025
Environment="PATH=/home/sa7bnb/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/sa7bnb/.local/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 pocsag2025:app
Restart=always
RestartSec=10
StandardOutput=append:/home/sa7bnb/pocsag2025/gunicorn.log
StandardError=append:/home/sa7bnb/pocsag2025/gunicorn.log

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable pocsag
sudo systemctl start pocsag

# 7. Kontrollera status
sudo systemctl status pocsag
