# 📡 POCSAG 2025 - Dokumentation

POCSAG 2025 är ett **Python-baserat system** för att avkoda och hantera **POCSAG-meddelanden** med hjälp av RTL-SDR.  
Systemet erbjuder ett **webbaserat användargränssnitt** för övervakning, filtrering och e-postnotifieringar av mottagna meddelanden.

**Utvecklad av:** [SA7BNB - Anders Isaksson](https://github.com/sa7bnb)  

---

## ✨ Nyheter
- 🆕 **Modulär arkitektur**
- 🆕 **Blacklist-funktion** med realtidsuppdatering
- 🆕 **Förbättrad e-posthantering** med stöd för flera mottagare och testfunktion
- 🆕 **Säkerhetssystem** med autentisering, sessioner och brute force-skydd
- 🆕 **Moderniserat webbgränssnitt**

---

## 📂 Arkitektur
Projektet är uppdelat i flera Python-moduler för bättre underhållbarhet:

- `config_manager.py` – Konfigurationshantering och dataklasser  
- `utils.py` – Hjälpfunktioner och verktyg  
- `email_handler.py` – E-postfunktionalitet  
- `message_handler.py` – Meddelandehantering och avkodning  
- `server.py` – Huvudserver och webbgränssnitt  

---

## 🚀 Huvudfunktioner

### 📡 Radiomottagning
- Använder RTL-SDR för att ta emot POCSAG-signaler  
- Stöder **POCSAG512** och **POCSAG1200**  
- Konfigurerbar frekvens *(standard: 161.4375 MHz)*  
- Automatisk dekodning med **multimon-ng**  

### 🔍 Meddelandehantering
- Realtidsvisning av mottagna meddelanden  
- Filtrering baserat på **RIC-adresser**  
- Blacklist för oönskade adresser och innehåll  
- Stöd för **svenska tecken (åäö)**  
- Robust felhantering  

### 🚫 Blacklist
- Filtrering baserat på **RIC-adresser** eller ord/fraser  
- Case-sensitive/insensitive alternativ  
- Realtidsuppdatering via webbgränssnitt  
- Blockerade meddelanden loggas inte  

### 📧 E-postnotifieringar
- Stöd för **Gmail, Outlook och andra SMTP-servrar**  
- Stöd för flera mottagare (BCC för integritet)  
- Automatisk testfunktion  
- Konfigurerbar ämnesrad  
- Kartlänkar för meddelanden med koordinater  

### 🔐 Säkerhet
- Autentisering med användarkonto  
- Sessioner med timeout och brute force-skydd  
- Obligatorisk första-gången-setup för admin-konto  
- BCrypt-hashning av lösenord  

### 🌐 Webbgränssnitt
- Responsiv design  
- Realtidsuppdatering av meddelanden  
- Fullständig konfiguration via webben  
- Nedladdning av loggar  
- Användarhantering med sessionkontroll  

---

## 💻 Systemkrav

### Hårdvara
- RTL-SDR-dongel (RTL2832U)  
- Antenn för vald frekvens  
- Raspberry Pi 4 (rekommenderat)  

### Programvara
- Python **3.7+**  
- RTL-SDR-drivrutiner  
- `multimon-ng`  
- Flask + övriga Python-beroenden  

---

## ⚙️ Installation

### Automatisk installation (Rekommenderat)
```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/sa7bnb/pocsag2025.git
sudo apt install rtl-sdr multimon-ng python3-pip python3-flask python3-pyproj python3-werkzeug -y
sudo raspi-config --expand-rootfs && sudo reboot
Efter omstart:

bash
Kopiera
Redigera
cd pocsag2025
chmod +x *.py
Autostart
bash
Kopiera
Redigera
sudo crontab -e
Lägg till:

bash
Kopiera
Redigera
@reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py
Starta om:

bash
Kopiera
Redigera
sudo reboot
🔑 Första inloggning
Surfa till http://pi-ipadress:5000/

Klicka på "Sätt upp ditt konto här"

Skapa ditt administratörskonto

⚡ Konfiguration
Frekvens: Ställ in i MHz (ex. 161.4375)

RIC-filter: Lägg till numeriska adresser

Blacklist: Blockera adresser/ord via webben eller config.json

E-post: Konfigurera SMTP, mottagare och ämnesrad

📬 Kontakt
Utvecklare: SA7BNB Anders Isaksson

E-post: sa7bnb(@)gmail.com

GitHub: https://github.com/sa7bnb/pocsag2025
