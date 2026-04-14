#!/bin/bash
# ============================================================
# POCSAG 2025 - Installationsskript for Raspberry Pi
# ============================================================

# 1. Kontrollera och fixa apt-kallor om paket saknas
DISTRO=$(lsb_release -cs 2>/dev/null || echo "trixie")

if ! apt-cache show git &>/dev/null; then
    echo "Fixar apt-kallor for $DISTRO..."
    sudo tee /etc/apt/sources.list.d/debian.sources > /dev/null << EOF
Types: deb
URIs: http://deb.debian.org/debian/
Suites: $DISTRO $DISTRO-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp

Types: deb
URIs: http://deb.debian.org/debian-security/
Suites: $DISTRO-security
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp
EOF
fi

if ! grep -q "raspberrypi.com" /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list 2>/dev/null; then
    echo "Lagg till Raspberry Pi-repo..."
    sudo tee /etc/apt/sources.list.d/raspi.sources > /dev/null << EOF
Types: deb
URIs: http://archive.raspberrypi.com/debian/
Suites: $DISTRO
Components: main
Signed-By: /usr/share/keyrings/raspberrypi-archive-keyring.gpg
EOF
fi

# 2. Uppdatera system och installera beroenden
sudo apt update && sudo apt upgrade -y
sudo apt install -y git rtl-sdr multimon-ng python3-pip

# 3. Klona repo
git clone https://github.com/sa7bnb/pocsag2025.git
cd /home/sa7bnb/pocsag2025

# 4. Installera Python-beroenden
python3 -m pip install flask pyproj werkzeug gunicorn --break-system-packages

# 5. Lagg till ~/.local/bin i PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

# 6. Blockera RTL-SDR kernel-drivrutin
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true

# 7. Skapa systemd-tjanst
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

# 8. Kontrollera status
sudo systemctl status pocsag
