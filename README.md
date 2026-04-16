📡 POCSAG 2025

Ett system för att avkoda och hantera POCSAG-meddelanden via RTL-SDR, med webbaserat gränssnitt för övervakning, filtrering och e-postnotifieringar.
Utvecklad av: SA7BNB – Anders Isaksson


✨ Nyheter i version 2026

🆕 Blacklist-funktion med realtidsuppdatering
🆕 Förbättrad e-posthantering med stöd för flera mottagare och testfunktion
🆕 Säkerhetssystem med autentisering, sessioner och brute force-skydd
🆕 Moderniserat webbgränssnitt med responsiv design
🆕 Möjlighet att justera gain


🚀 Installation (Raspberry Pi 4)
🖼️ Alternativ 1 – Färdig image (rekommenderas)
En färdig SD-kortsimage för Raspberry Pi 4 med RTL-SDR v3/v4 finns tillgänglig för nedladdning:

📥 Ladda ner image från Google Drive

Skriv imagen till ett SD-kort med Raspberry Pi Imager eller Balena Etcher, sätt i kortet och starta Pi:n. Surfa sedan till http://<DIN-IP-ADRESS>:5000/ och logga.

🔧 Alternativ 2 – Manuell installation
1. Förbered operativsystemet
Använd Raspberry Pi Imager för att installera OS:
InställningVärdeEnhetRaspberry Pi 4OSRaspberry Pi OS Lite (64-bit)Via kugghjulet i Imager – aktivera SSH, ställ in användarnamn/lösenord och konfigurera Wi-Fi innan du skriver till SD-kortet.
2. Hårdvara & uppstart
Anslut din RTL-SDR v4 till en USB-port på Pi:n.
Starta Pi:n och hitta dess IP-adress via routern.
3. Installation via SSH
Anslut via terminalen:
bashssh användarnamn@DIN-IP-ADRESS
Kör installationsskriptet:
bashcurl -fsSL https://raw.githubusercontent.com/sa7bnb/pocsag2025/main/install.sh | bash

🔑 Kom igång
Första inloggning
När installationen är klar, surfa till systemet i din webbläsare:
http://<DIN-IP-ADRESS>:5000/
Klicka på "Sätt upp ditt konto här" och skapa ditt administratörskonto. Detta krävs vid första körningen för att låsa systemet.

⚡ Konfiguration
All konfiguration sköts via webbgränssnittet:
InställningBeskrivningFrekvensAnge önskad frekvens i MHz, t.ex. 161.4375Sätt GainAnge önskad gain på din SDR sticka 49,6dBRIC-filterLägg till numeriska adresser att bevakaBlacklistBlockera adresser eller ord – via webben eller direkt i config.jsonE-postSMTP-inställningar, mottagarlistor och anpassade ämnesrader

🛠 Huvudfunktioner
📡 Radiomottagning & meddelanden

Stöder POCSAG512 och POCSAG1200
Realtidsvisning med stöd för svenska tecken (åäö)
Automatisk generering av kartlänkar vid koordinater i meddelanden

🔐 Säkerhet

BCrypt-hashning av lösenord
Sessioner med timeout och brute force-skydd vid inloggning

💻 Systemkrav
KomponentKravHårdvaraRaspberry Pi 4, RTL-SDR v3/v4, AntennOSRaspberry Pi OS Lite (64-bit)ProgramvaraPython 3.7+, multimon-ng, rtl-sdr

Utvecklad av Anders Isaksson (SA7BNB)

Ändringarna jag gjorde:

Lade till ett "Alternativ 1 – Färdig image"-block högst upp i installationssektionen med länken och kort instruktion om hur man använder den
Döpte om den befintliga manuella installationen till "Alternativ 2 – Manuell installation" med tydligare rubriker
Uppdaterade systemkravstabellen från RTL-SDR v4 till RTL-SDR v3/v4 för att matcha image-beskrivningen
