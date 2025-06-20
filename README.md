📡 POCSAG 2025 – Webbaserad personsökardekoder med e-postavisering
POCSAG 2025 är ett Python-baserat program för Raspberry Pi (eller annan Linux-dator med RTL-SDR), som i realtid avkodar POCSAG-meddelanden, filtrerar dem på specifika RIC-adresser och skickar notifieringar via e-post. Allt detta via en modern och enkel webbaserad kontrollpanel i Flask.

🔧 Funktioner

✅ Stöd för flera POCSAG-hastigheter: 512 och 1200 baud.

📬 Filtrering av meddelanden via RIC-adresser.  

✉️ Automatisk e-postavisering vid nya filtrerade meddelanden, inklusive kartlänk om RT90-koordinater finns.

🌍 Konverterar RT90-koordinater till WGS84 med pyproj och skapar klickbara kartlänkar till OpenStreetMap.

💻 Modern webgränssnitt med inställningsformulär för frekvens, filter och e-post.

🔄 Auto-uppdatering av meddelandelistor var 10:e sekund via JavaScript.

🛠️ Enkel konfiguration via config.json – ändras automatiskt via webbgränssnittet.

🧰 Förutsättningar

Ladda ner och installera git

sudo apt update

sudo apt install git -y

git clone https://github.com/sa7bnb/pocsag2025.git

Installera följande verktyg på din Raspberry Pi på ny PI-OS installation: (jag använder Pi4 med Raspberry PI OS Lite 32bit)
sudo apt update && sudo apt install rtl-sdr multimon-ng python3-pip python3-flask python3-pyproj -y && sudo raspi-config --expand-rootfs && sudo reboot

Cd pocsag2025

Kör chmod +x server.py på din fil, 

sudo crontab -e

@reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py

🖥️ Användning
Starta programmet med:
python3 server.py, editera frekvens och ric
Eller kör chmod +x server.py på din fil, sudo crontab -e
@reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py

Öppna sedan webbläsaren och navigera till:
http://<din-Raspberry-IP>:5000

📂 Filbeskrivning
server.py – Huvudprogrammet. Startar RTL-SDR-lyssning, avkodning, filtrering, e-post och Flask-webbservern.
config.json – Sparar valda frekvenser, filter och e-postinställningar.
messages.txt – Loggfil för alla avkodade POCSAG-meddelanden.
filtered.messages.txt – Loggfil för meddelanden som matchar angivna filteradresser (RICs).

📡 Hur det fungerar
rtl_fm används för att ta in radiosignaler från ett SDR-stick.
multimon-ng dekodar inkommande FM-data till POCSAG-meddelanden.
Meddelanden loggas och visas i realtid i webbläsaren.
Om ett meddelande matchar en angiven adress i filtret:
visas det separat,och e-post skickas automatiskt (om aktiverat).
RT90-koordinater i meddelanden omvandlas till WGS84 och länkas till OpenStreetMap.

✉️ E-postfunktion
E-postinställningar görs direkt via webbgränssnittet.
Stöd för Gmail (via SMTP med app-lösenord).
E-post innehåller kartlänk om koordinater finns i meddelandet (t.ex. X=6359960 Y=1502061).

// Anders Isaksson - SA7BNB - hamradio@sa7bnb.se
