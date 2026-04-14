#!/bin/bash
# ============================================================
# POCSAG 2025 - Installationsskript for Raspberry Pi
# ============================================================

CURRENT_USER=$(whoami)
INSTALL_DIR="/home/$CURRENT_USER/pocsag2025"

# 1. Installera beroenden
sudo apt update
sudo apt install -y git rtl-sdr multimon-ng python3-pip

# 2. Klona repo
git clone https://github.com/sa7bnb/pocsag2025.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 3. Installera Python-beroenden
python3 -m pip install flask pyproj werkzeug gunicorn --break-system-packages

# 4. Lagg till ~/.local/bin i PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "/home/$CURRENT_USER/.bashrc"

# 5. Blockera RTL-SDR kernel-drivrutin
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true

# 6. Skapa systemd-tjanst
sudo tee /etc/systemd/system/pocsag.service > /dev/null << EOF
[Unit]
Description=POCSAG 2025 - By SA7BNB
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/home/$CURRENT_USER/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/$CURRENT_USER/.local/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 pocsag2025:app
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/gunicorn.log
StandardError=append:$INSTALL_DIR/gunicorn.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pocsag
sudo systemctl start pocsag

# 7. Starta om
echo "Installation klar! Startar om om 10 sekunder..."
sleep 10
sudo reboot
