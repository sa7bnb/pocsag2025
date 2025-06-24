# POCSAG 2025 - Dokumentation

POCSAG 2025 är ett Python-baserat system för att avkoda och hantera POCSAG-meddelanden (radio paging-meddelanden) med hjälp av RTL-SDR. Systemet erbjuder en webbaserad användargränssnitt för övervakning, filtrering och e-postnotifieringar av mottagna meddelanden.

Utvecklad av: SA7BNB - Anders Isaksson

## Huvudfunktioner

### 📡 Radiomottagning
- Använder RTL-SDR för att ta emot POCSAG-signaler
- Stöder POCSAG512 och POCSAG1200
- Konfigurerbar frekvens (standard: 161.4375 MHz)
- Automatisk dekodning med multimon-ng

### 🔍 Meddelandehantering
- Realtidsvisning av alla mottagna meddelanden
- Filtrering baserat på RIC-adresser (Radio Identity Code)
- Svartlistefunktion för oönskade adresser
- Automatisk textbehandling och rensning av kontrollsymboler
- Stöd för svenska tecken (åäö)

### 📧 E-postnotifieringar
- Automatiska e-postnotifieringar för filtrerade Alpha-meddelanden
- Dubblettskydd (samma meddelande blockeras i 5 minuter)
- Stöd för Gmail, Outlook och andra SMTP-servrar
- Kartlänkar för meddelanden med RT90-koordinater

### 🌐 Webbgränssnitt
- Responsiv webbdesign
- Realtidsuppdatering av meddelanden (var 10:e sekund)
- Nedladdning av meddelandeloggar
- Konfiguration av alla inställningar via webben

## Systemkrav
### Hårdvara
- RTL-SDR-dongel (kompatibel med RTL2832U)
- Lämplig antenn för aktuell frekvens
- Linux-system (rekommenderat: Raspberry Pi eller Ubuntu)

## Installation
1. Installera din Raspberry Pi med Raspberry Pi Imager och välj det minimalistiska Raspberry Pi OS Lite (32-bitars).
2. Under installationen är det viktigt att användaren du skapar heter sa7bnb och inget annat. Aktivera även SSH och konfigurera ditt WiFi om du planerar att använda det.
3. Koppla upp dig via SSH och kör detta kommando sudo apt update && sudo apt install git -y && git clone https://github.com/sa7bnb/pocsag2025.git && sudo apt install rtl-sdr multimon-ng python3-pip python3-flask python3-pyproj -y && sudo raspi-config --expand-rootfs && sudo reboot
4. Kör cd pocsag2025 och kör chmod +x server.py
5. kör sudo crontab -e och lägg detta längst upp i listan
@reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py
0 0 * * 1 /sbin/shutdown -r now
6. Starta om enheten via sudo reboot.
7. Vänta en liten stund och surfa in på websidan (http://pi-ipadress:5000/)

### Frekvens
- Ange frekvens i MHz (utan M-suffix)
- Exempel: `161.4375` för 161.4375 MHz
- Vanliga POCSAG-frekvenser i Sverige: 161.4375, 169.8125

### Filteradresser (RIC)
- Lägg till en RIC-adress per rad
- Endast numeriska adresser accepteras
- Exempel:
```
123456
789012
555000
```

### Svartlista
- Skapa filen `blacklist.txt` i programmets katalog
- En RIC-adress per rad för att blockera oönskade meddelanden
- Jag jag brukar lägga in 1600000 här

### E-postinställningar

#### Gmail-konfiguration:
- **SMTP-server:** `smtp.gmail.com`
- **Port:** `587`
- **Säkerhet:** Aktivera 2FA och använd app-lösenord
- **App-lösenord:** Generera i Google-kontoinställningar

#### Outlook-konfiguration:
- **SMTP-server:** `smtp-mail.outlook.com`
- **Port:** `587`
- **Säkerhet:** Använd app-lösenord för Outlook

### Grundläggande användning
1. Starta programmet
2. Öppna webbläsaren på `http://localhost:5000`
3. Konfigurera frekvens för ditt område
4. Lägg till RIC-adresser att filtrera på
5. Övervaka meddelanden i realtid

### E-postnotifieringar
1. Gå till "E-postinställningar"
2. Konfigurera SMTP-server och autentisering
3. Aktivera notifieringar
4. Testa med "Skicka testmail"
5. Få automatiska e-post för Alpha-meddelanden

### Kartlänkar
Meddelanden med RT90-koordinater får automatiskt kartlänkar:
```
X=1234567 Y=7654321
→ Blir till OpenStreetMap-länk
```

## Felsökning

### RTL-SDR-problem
```bash
# Kontrollera att dongeln hittas
rtl_test

# Kolla USB-behörigheter
sudo usermod -a -G plugdev $USER
```

### Multimon-ng-problem
```bash
# Testa manuellt
rtl_fm -f 161.4375M -M fm -s 22050 -g 49 | multimon-ng -t raw -a POCSAG512 -a POCSAG1200 -f alpha -
```

### E-postproblem
- Kontrollera att 2FA är aktiverat
- Använd app-specifika lösenord, inte vanligt lösenord
- Verifiera SMTP-inställningar
- Kolla brandväggsinställningar

### Vanliga felmeddelanden
- `"Fel vid start av dekoder"` - Kontrollera RTL-SDR-anslutning
- `"E-postfel"` - Verifiera SMTP-konfiguration
- `"Loggningsfel"` - Kontrollera filbehörigheter

## Prestanda och gränser

### Minneskonsumption
- Håller max 50 meddelanden i minnet per kategori
- Automatisk rensning av e-post-cache var 10:e minut
- Loggar växer kontinuerligt (rensa manuellt vid behov)

### Nätverkstrafik
- Minimal bandbredd för webbgränssnitt
- E-post endast vid filtrerade Alpha-meddelanden
- Dubblettskydd begränsar e-post-spam

## Säkerhet

### Lösenordshantering
- App-lösenord lagras i `config.json`
- Använd aldrig huvudlösenord för e-postkonton
- Begränsa åtkomst till konfigurationsfiler

### Nätverkssäkerhet
- Standardport 5000 lyssnar på alla gränssnitt (0.0.0.0)
- Överväg brandväggsinställningar för produktionsmiljö
- Ingen autentisering för webbgränssnitt

## Bidrag och utveckling

### Kodstruktur
- Modulär design med separata klasser för olika funktioner
- Flask för webbgränssnitt
- Threading för parallell bearbetning
- Logging för felsökning

**Utvecklare:** SA7BNB
Anders Isaksson - hamradio(@)sa7bnb.se
