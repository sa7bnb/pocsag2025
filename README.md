# POCSAG 2025 - Dokumentation

POCSAG 2025 är ett Python-baserat system för att avkoda och hantera POCSAG-meddelanden (radio paging-meddelanden) med hjälp av RTL-SDR. Systemet erbjuder en webbaserad användargränssnitt för övervakning, filtrering och e-postnotifieringar av mottagna meddelanden.

**Utvecklad av:** SA7BNB - Anders Isaksson

## Huvudfunktioner

### 📡 Radiomottagning
- Använder RTL-SDR för att ta emot POCSAG-signaler
- Stöder POCSAG512 och POCSAG1200
- Konfigurerbar frekvens (standard: 161.4375 MHz)
- Automatisk dekodning med multimon-ng

### 🔍 Meddelandehantering
- Realtidsvisning av alla mottagna meddelanden
- Filtrering baserat på RIC-adresser (Radio Identity Code)
- **🆕 Avancerad blacklist-funktion** för oönskade adresser och innehåll
- Automatisk textbehandling och rensning av kontrollsymboler
- Stöd för svenska tecken (åäö)

### 🚫 Blacklist-funktioner
- **RIC-adressfiltrering:** Blockera alla meddelanden från specifika RIC-adresser
- **Ordfiltrering:** Blockera meddelanden som innehåller specifika ord eller fraser
- **Skiftlägeskänslighet:** Konfigurerbar case-sensitive/insensitive sökning
- **Webbaserad konfiguration:** Enkelt att hantera via webbgränssnittet
- **Intelligent filtrering:** Söker i hela meddelandetexten
- **Permanent blockering:** Blockerade meddelanden visas inte i loggar eller gränssnitt

### 📧 E-postnotifieringar
- Automatiska e-postnotifieringar för filtrerade Alpha-meddelanden
- **🆕 Stöd för flera mottagare** (BCC för integritet)
- Dubblettskydd (samma meddelande blockeras i 10 minuter)
- Stöd för Gmail, Outlook och andra SMTP-servrar
- Kartlänkar för meddelanden med RT90-koordinater

### 🌐 Webbgränssnitt
- Responsiv webbdesign
- Realtidsuppdatering av meddelanden (var 10:e sekund)
- **🆕 Dedikerad blacklist-hantering**
- Nedladdning av meddelandeloggar
- Konfiguration av alla inställningar via webben

## Systemkrav

### Hårdvara
- RTL-SDR-dongel (kompatibel med RTL2832U)
- Lämplig antenn för aktuell frekvens
- Linux-system med Raspberry Pi

## Installation

1. Installera din Raspberry Pi med Raspberry Pi Imager och välj det minimalistiska **Raspberry Pi OS Lite (32-bitars)**.

2. Under installationen är det viktigt att användaren du skapar heter `sa7bnb` och inget annat. Aktivera även SSH och konfigurera ditt WiFi om du planerar att använda det.

3. Koppla upp dig via SSH och kör detta kommando:
   ```bash
   sudo apt update && sudo apt install git -y && git clone https://github.com/sa7bnb/pocsag2025.git && sudo apt install rtl-sdr multimon-ng python3-pip python3-flask python3-pyproj -y && sudo raspi-config --expand-rootfs && sudo reboot
   ```

4. Kör `cd pocsag2025` och kör `chmod +x server.py`

5. Kör `sudo crontab -e` och lägg detta längst upp i listan (autostart av skript):
   ```
   @reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py
   ```

6. Starta om enheten via `sudo reboot`.

7. Vänta en liten stund och surfa in på websidan (`http://pi-ipadress:5000/`)

## Konfiguration

### Frekvens
- Ange frekvens i MHz (utan M-suffix)
- Exempel: `161.4375` för 161.4375 MHz
- Vanliga POCSAG-frekvenser i Sverige: 161.4375, 169.8000

### Filteradresser (RIC)
- Lägg till en RIC-adress per rad
- Endast numeriska adresser accepteras
- Exempel:
  ```
  123456
  789012
  555000
  ```

### 🆕 Blacklist-konfiguration
Blacklist-funktionen har två sätt att blockera meddelanden:

#### Via Webbgränssnittet (Rekommenderat)
1. Klicka på den röda **"🚫 Blacklist"**-knappen på startsidan
2. Lägg till RIC-adresser och/eller ord som ska blockeras
3. Välj om ordfiltrering ska vara skiftlägeskänslig
4. Klicka **"🆕 Uppdatera Blacklist"**

#### Via Konfigurationsfil
Redigera `config.json` och lägg till:
```json
"blacklist": {
  "addresses": [
    "1600000",
    "1234567"
  ],
  "words": [
    "Driftlarm",
    "Summalarm", 
    "Samverkan",
    "Provlarm"
  ],
  "case_sensitive": false
}
```

**Exempel på användning:**
- **RIC-adresser:** `1600000`, `1234567` - Blockerar alla meddelanden från dessa adresser
- **Ord:** `Driftlarm`, `Testlarm`, `Övning` - Blockerar meddelanden som innehåller dessa ord
- **Case-sensitive:** `false` betyder att både "TESTLARM" och "testlarm" blockeras

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

#### 🆕 Flera mottagare
- Lägg till flera e-postadresser separerade med komma eller på separata rader
- Alla mottagare får e-post via BCC (dold kopia) för integritet
- Exempel:
  ```
  mottagare1@email.com
  mottagare2@email.com, mottagare3@email.com
  ```

## Grundläggande användning

1. **Starta programmet**
   - Öppna webbläsaren på `http://localhost:5000`
   - Konfigurera frekvens för ditt område
   - Lägg till RIC-adresser att filtrera på
   - Övervaka meddelanden i realtid

2. **🆕 Konfigurera Blacklist**
   - Klicka på **"🚫 Blacklist"**
   - Lägg till oönskade RIC-adresser
   - Lägg till ord som ska blockeras (t.ex. "testlarm", "övning")
   - Spara inställningarna

3. **E-postnotifieringar**
   - Gå till "E-postinställningar"
   - Konfigurera SMTP-server och autentisering  
   - Lägg till flera mottagare
   - Aktivera notifieringar
   - Testa med "Skicka testmail"
   - Få automatiska e-post för Alpha-meddelanden

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

### 🆕 Blacklist-problem
- Kontrollera JSON-syntax i `config.json`
- Använd webbgränssnittet för att undvika syntaxfel
- Kontrollera att RIC-adresser är numeriska strängar
- Ord kan innehålla mellanslag och specialtecken

### Vanliga felmeddelanden
- **"Fel vid start av dekoder"** - Kontrollera RTL-SDR-anslutning
- **"E-postfel"** - Verifiera SMTP-konfiguration  
- **"Loggningsfel"** - Kontrollera filbehörigheter
- **"JSON-fel"** - Kontrollera syntax i config.json

## Prestanda och gränser

### Minneskonsumption
- Håller max 50 meddelanden i minnet per kategori
- Automatisk rensning av e-post-cache var 10:e minut
- Loggar växer kontinuerligt (rensa manuellt vid behov)
- **🆕 Blacklist-cache:** Effektiv filtrering med minimal påverkan på prestanda

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

### 🆕 Dataintegritet
- Blacklist-konfiguration valideras vid start
- Automatisk migrering från äldre konfigurationsformat
- Säker hantering av flera e-postmottagare via BCC

## Nyheter i version 2025

### 🆕 Avancerad Blacklist
- **Dubbel filtrering:** Både RIC-adresser och ordinnehåll
- **Intelligent sökning:** Case-sensitive/insensitive alternativ
- **Webbaserad hantering:** Ingen manuell JSON-redigering
- **Realtidsuppdatering:** Ändringar träder i kraft omedelbart

### 🆕 Förbättrade E-postfunktioner  
- **Flera mottagare:** Stöd för obegränsat antal e-postadresser
- **BCC-skydd:** Mottagare ser inte varandras adresser
- **Förbättrad validering:** Automatisk kontroll av e-postformat

### 🆕 Användargränssnitt
- **Moderniserad design:** Responsiv och användarvänlig
- **Dedikerade inställningssidor:** Separata sidor för olika funktioner
- **Förbättrad feedback:** Tydligare statusmeddelanden och hjälptexter

## Bidrag och utveckling

### Kodstruktur
- Modulär design med separata klasser för olika funktioner
- Flask för webbgränssnitt
- Threading för parallell bearbetning
- **🆕 Dataklasser:** Strukturerad konfigurationshantering
- **🆕 Avancerad filtrering:** Effektiv blacklist-implementation
- Logging för felsökning

---

**Utvecklare:** SA7BNB Anders Isaksson - hamradio(@)sa7bnb.se

**GitHub:** https://github.com/sa7bnb/pocsag2025
