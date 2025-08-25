POCSAG 2025 - Dokumentation
POCSAG 2025 är ett Python-baserat system för att avkoda och hantera POCSAG-meddelanden med hjälp av RTL-SDR. Systemet erbjuder en webbaserad användargränssnitt för övervakning, filtrering och e-postnotifieringar av mottagna meddelanden.
Utvecklad av: SA7BNB - Anders Isaksson

🆕 Ny modulär arkitektur
Systemet har omstrukturerats för bättre underhållbarhet och utveckling:
•	config_manager.py - Konfigurationshantering och dataklasser
•	utils.py - Hjälpfunktioner och verktyg
•	email_handler.py - E-postfunktionalitet
•	message_handler.py - Meddelandehantering och avkodning
•	server.py - Huvudserver och webbgränssnitt
Huvudfunktioner

📡 Radiomottagning
•	Använder RTL-SDR för att ta emot POCSAG-signaler
•	Stöder POCSAG512 och POCSAG1200
•	Konfigurerbar frekvens (standard: 161.4375 MHz)
•	Automatisk dekodning med multimon-ng

🔍 Meddelandehantering
•	Realtidsvisning av alla mottagna meddelanden
•	Filtrering baserat på RIC-adresser (Radio Identity Code)

•	🆕 Avancerad blacklist-funktion för oönskade adresser och innehåll
•	Automatisk textbehandling och rensning av kontrollsymboler
•	Stöd för svenska tecken (åäö)

•	🆕 Förbättrad meddelandebearbetning med robust felhantering
🚫 Blacklist-funktioner
•	RIC-adressfiltrering: Blockera alla meddelanden från specifika RIC-adresser
•	Ordfiltrering: Blockera meddelanden som innehåller specifika ord eller fraser
•	Skiftlägeskänslighet: Konfigurerbar case-sensitive/insensitive sökning
•	Webbaserad konfiguration: Enkelt att hantera via webbgränssnittet
•	Intelligent filtrering: Söker i hela meddelandetexten
•	Permanent blockering: Blockerade meddelanden visas inte i loggar eller gränssnitt

•	🆕 Realtidsuppdatering: Ändringar träder i kraft omedelbart
📧 E-postnotifieringar
•	Automatiska e-postnotifieringar för filtrerade Alpha-meddelanden

•	🆕 Stöd för flera mottagare (BCC för integritet)
•	Förbättrat dubblettskydd (samma Alpha-innehåll blockeras i 10 minuter)
•	Stöd för Gmail, Outlook och andra SMTP-servrar
•	Kartlänkar för meddelanden med RT90-koordinater

•	🆕 Konfigurerbar ämnesrad för e-postnotifieringar
•	🆕 Automatisk testfunktion för att verifiera konfiguration
🔐 Säkerhet och autentisering

•	🆕 Komplett autentiseringssystem med inloggning
•	Säkra sessioner med konfigurerbar timeout
•	Skydd mot brute force med IP-baserad låsning
•	Första-gången setup för säker konfiguration
•	Lösenordshantering med säker hashning
•	Sessionhantering med automatisk utloggning

🌐 Webbgränssnitt
•	🆕 Responsiv och modern design
•	Säker inloggning med användarkonto
•	Realtidsuppdatering av meddelanden (var 10:e sekund)

•	🆕 Dedikerade inställningssidor för olika funktioner
•	Nedladdning av meddelandeloggar
•	Komplett konfiguration av alla inställningar via webben

•	🆕 Användarhantering med sessionkontroll
Systemkrav
Hårdvara
•	RTL-SDR-dongel (kompatibel med RTL2832U)
•	Lämplig antenn för aktuell frekvens
•	Raspberry Pi 4 (rekommenderat)
Programvara
•	Python 3.7+
•	RTL-SDR-drivrutiner
•	multimon-ng
•	Flask och andra Python-beroenden

Installation
Automatisk installation (Rekommenderat)
1.	Installera Raspberry Pi OS Lite (32-bitars) med Raspberry Pi Imager
2.	Viktigt: Skapa användaren sa7bnb under installationen
3.	Aktivera SSH och konfigurera WiFi om nödvändigt
4.	Anslut via SSH och kör:
sudo apt update && sudo apt install git -y && git clone https://github.com/sa7bnb/pocsag2025.git && sudo apt install rtl-sdr multimon-ng python3-pip python3-flask python3-pyproj python3-werkzeug -y && sudo raspi-config --expand-rootfs && sudo reboot
5.	Efter omstart, kör:
cd pocsag2025
chmod +x *.py

7.	🆕 Konfigurera autostart:
sudo crontab -e
Lägg till längst upp:
@reboot sleep 30 && /usr/bin/python3 /home/sa7bnb/pocsag2025/server.py

9.	Starta om: sudo reboot
    
10.	🆕 Första inloggning:
o	Vänta 30 sekunder efter omstart
o	Surfa till http://pi-ipadress:5000/
o	Klicka på "Sätt upp ditt konto här"
o	Skapa ditt administratörskonto

🆕 Säkerhetskonfiguration
Första gången-setup
1.	Gå till http://pi-ipadress:5000/setup
2.	Skapa administratörskonto: 
o	Användarnamn (minst 3 tecken)
o	Lösenord (minst 6 tecken)
o	Bekräfta lösenord
3.	Klicka "Skapa konto"
4.	Logga in med dina nya uppgifter
Säkerhetsinställningar
Gå till 🔐 Säkerhet för att konfigurera:
•	Session timeout: 1-168 timmar (standard: 24h)
•	Max inloggningsförsök: 3-20 försök (standard: 5)
•	Blockering: 5-1440 minuter (standard: 15 min)
•	Lösenordsbyte: Ändra ditt lösenord säkert
Konfiguration
Frekvens
•	Ange frekvens i MHz (utan M-suffix)
•	Exempel: 161.4375 för 161.4375 MHz
•	Vanliga POCSAG-frekvenser i Sverige: 161.4375, 169.8000
•	Mer info om frekvenser
Filteradresser (RIC)
•	Lägg till en RIC-adress per rad
•	Endast numeriska adresser accepteras
•	Exempel: 
•	123456789012555000

🆕 Blacklist-konfiguration
Blacklist-funktionen har två sätt att blockera meddelanden:
Via Webbgränssnittet (Rekommenderat)
1.	Logga in på systemet
2.	Klicka på den röda "🚫 Blacklist"-knappen
3.	RIC-adresser: Lägg till numeriska adresser som ska blockeras
4.	Ord/fraser: Lägg till text som ska blockeras
5.	Skiftlägeskänslighet: Välj om stora/små bokstäver ska betyda något
6.	Klicka "🚫 Uppdatera Blacklist"
Manuell konfiguration
Redigera config.json och lägg till:
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
Exempel:
•	RIC-adresser: 1600000, 1234567 - Blockerar alla meddelanden från dessa adresser
•	Ord: Driftlarm, Testlarm, Övning - Blockerar meddelanden som innehåller dessa ord
•	Case-sensitive: false betyder att både "TESTLARM" och "testlarm" blockeras

🆕 E-postinställningar
Gå till "E-postinställningar" för att konfigurera:
Gmail-konfiguration:
•	SMTP-server: smtp.gmail.com
•	Port: 587
•	Säkerhet: Aktivera 2FA och använd app-lösenord
•	App-lösenord: Generera i Google-kontoinställningar
Outlook-konfiguration:
•	SMTP-server: smtp-mail.outlook.com
•	Port: 587
•	Säkerhet: Använd app-lösenord för Outlook

🆕 Konfigurerbar ämnesrad
•	Anpassad ämnesrad: Sätt egen ämnesrad för e-postnotifieringar
•	Standard: "Pocsag Larm - Rix"
•	Exempel: "🚨 Brandlarm", "📻 POCSAG Alert", etc.

🆕 Flera mottagare
•	Lägg till flera e-postadresser separerade med komma eller på separata rader
•	Alla mottagare får e-post via BCC (dold kopia) för integritet
•	Exempel: 
•	mottagare1@email.commottagare2@email.com, mottagare3@email.com

🆕 Testfunktion
•	Klicka "📧 Skicka testmail" för att verifiera konfigurationen
•	Testmailet skickas till alla konfigurerade mottagare
Grundläggande användning
1. Starta och logga in
1.	Surfa till http://localhost:5000 eller http://pi-ipadress:5000
2.	Logga in med ditt administratörskonto
3.	Du kommer till huvudsidan med realtidsövervakning
2. Konfigurera systemet
1.	Frekvens: Sätt rätt frekvens för ditt område
2.	Filteradresser: Lägg till RIC-adresser att filtrera på
3.	Blacklist: Konfigurera oönskade adresser och ord
4.	E-post: Sätt upp notifieringar med anpassad ämnesrad
3. Övervaka meddelanden
•	Filtrerade meddelanden: Visar endast meddelanden från dina filteradresser
•	Alla meddelanden: Visar samtliga mottagna meddelanden (ej blockerade)
•	Automatisk uppdatering: Sidan uppdateras var 10:e sekund
•	Realtidsloggar: Alla meddelanden sparas även i filer

5. 🆕 Hantera säkerhet
•	Gå till "🔐 Säkerhet" för att: 
o	Ändra lösenord
o	Konfigurera sessionstimeout
o	Justera säkerhetsinställningar

🆕 Avancerade funktioner
Kartlänkar
Meddelanden med RT90-koordinater får automatiskt kartlänkar:
•	Format: X=1234567 Y=7654321
•	Resultat: Automatisk OpenStreetMap-länk
•	Konvertering: RT90 → WGS84/GPS-koordinater
Dubblettskydd för e-post
•	Alpha-innehåll: Samma textinnehåll blockeras i 10 minuter
•	Tidsstämplar ignoreras: Endast meddelandetext jämförs
•	Automatisk rensning: Cache rensas regelbundet
•	Loggning: Alla dubbletter loggas för felsökning
Filhantering
•	Automatisk skapande: Alla filer skapas vid första starten
•	Nedladdning: Hämta loggfiler via webbgränssnittet
•	Rensning: Manuell rensning av meddelanden via webben
Felsökning
RTL-SDR-problem
# Kontrollera att dongeln hittas
rtl_test

# Kolla USB-behörigheter
sudo usermod -a -G plugdev $USER

# Starta om efter behörighetsändring
sudo reboot
Multimon-ng-problem
# Testa manuellt
rtl_fm -f 161.4375M -M fm -s 22050 -g 49 | multimon-ng -t raw -a POCSAG512 -a POCSAG1200 -f alpha -

🆕 Autentiseringsproblem
•	Glömt lösenord: Stoppa systemet, ta bort config.json, starta om och gå till /setup
•	Låst konto: Vänta den konfigurerade tiden eller starta om systemet
•	Session timeout: Konfigurera längre sessionstid i säkerhetsinställningarna
E-postproblem
•	Kontrollera att 2FA är aktiverat
•	Använd app-specifika lösenord, inte vanligt lösenord
•	Verifiera SMTP-inställningar med testfunktionen
•	Kolla brandväggsinställningar

🆕 Blacklist-problem
•	Använd webbgränssnittet för att undvika syntaxfel
•	Kontrollera att RIC-adresser är numeriska
•	Ord kan innehålla mellanslag och specialtecken
•	Kontrollera loggarna för blockerade meddelanden
Vanliga felmeddelanden
•	"Fel vid start av dekoder" - Kontrollera RTL-SDR-anslutning
•	"E-postfel" - Verifiera SMTP-konfiguration med testmail
•	"Loggningsfel" - Kontrollera filbehörigheter
•	"Session har gått ut" - Logga in igen eller öka sessionstimeout
Prestanda och gränser
Minneskonsumption
•	Håller max 50 meddelanden i minnet per kategori
•	Automatisk rensning av e-post-cache var 10:e minut
•	Loggar växer kontinuerligt (rensa manuellt vid behov)

•	🆕 Effektiv blacklist-cache med minimal påverkan på prestanda
Nätverkstrafik
•	Minimal bandbredd för webbgränssnitt
•	E-post endast vid filtrerade Alpha-meddelanden
•	Dubblettskydd begränsar e-post-spam

•	🆕 Säkra sessioner med krypterad kommunikation
🆕 Systemresurser
•	CPU: Låg belastning under normal drift
•	Minne: ~50-100MB beroende på meddelandevolym
•	Disk: Loggar växer över tid, övervaka diskutrymme
•	Nätverk: Minimal trafik, endast vid e-post och webbåtkomst

Säkerhet
🆕 Autentisering och auktorisering
•	Säkra lösenord: BCrypt-hashning av lösenord
•	Sessionhantering: Krypterade sessioner med timeout
•	Brute force-skydd: IP-baserad låsning efter misslyckade försök
•	Automatisk utloggning: Sessioner går ut automatiskt
Lösenordshantering

•	🆕 Säker lagring: Lösenord hashas med Werkzeug Security
•	App-lösenord för e-post lagras i config.json
•	Använd aldrig huvudlösenord för e-postkonton

•	🆕 Lösenordspolicy: Minimum 6 tecken, rekommenderar starkt lösenord
Nätverkssäkerhet
•	Standardport 5000 lyssnar på alla gränssnitt (0.0.0.0)

•	🆕 Sessionkryptering: Alla sessioner är krypterade
•	Överväg brandväggsinställningar för produktionsmiljö

•	🆕 Säker autentisering: Obligatorisk inloggning för alla funktioner
🆕 Dataintegritet
•	Konfigurationsvalidering: Automatisk kontroll vid start
•	Automatisk migrering: Från äldre konfigurationsformat
•	Säker e-posthantering: BCC för att skydda mottagares integritet
•	Backup-rutiner: Rekommenderas för viktiga konfigurationer

🆕 Nyheter i version 2025
🔐 Komplett säkerhetssystem
•	Autentisering: Obligatorisk inloggning för alla användare
•	Sessionhantering: Säkra sessioner med konfigurerbar timeout
•	Brute force-skydd: Automatisk låsning vid misslyckade försök
•	Första gången-setup: Säker konfiguration av administratörskonto

🆕 Förbättrad arkitektur
•	Modulär design: Uppdelad i fem logiska komponenter
•	Bättre underhållbarhet: Enklare att utveckla och debugga
•	Förbättrade kommentarer: Detaljerad dokumentation i koden
•	Robustare felhantering: Bättre återhämtning från fel

🆕 Avancerad Blacklist
•	Dubbel filtrering: Både RIC-adresser och ordinnehåll
•	Intelligent sökning: Case-sensitive/insensitive alternativ
•	Webbaserad hantering: Ingen manuell JSON-redigering
•	Realtidsuppdatering: Ändringar träder i kraft omedelbart

🆕 Förbättrade E-postfunktioner
•	Flera mottagare: Stöd för obegränsat antal e-postadresser
•	BCC-skydd: Mottagare ser inte varandras adresser
•	Konfigurerbar ämnesrad: Anpassa ämnesraden för dina behov
•	Förbättrad validering: Automatisk kontroll av e-postformat
•	Testfunktion: Enkelt att verifiera konfiguration

🆕 Moderniserat användargränssnitt
•	Responsiv design: Fungerar på alla enheter
•	Dedikerade sidor: Separata sidor för olika funktioner
•	Förbättrad feedback: Tydligare statusmeddelanden och hjälptexter
•	Säkerhetsintegration: Inloggning och sessionhantering
Bidrag och utveckling
Kodstruktur
•	Modulär design: Fem separata Python-filer med specifika ansvarsområden
•	Flask-baserat: Modernt webbramverk för användargränssnitt
•	Threading: Parallell bearbetning för optimal prestanda

•	🆕 Dataklasser: Strukturerad konfigurationshantering
•	🆕 Avancerad filtrering: Effektiv blacklist-implementation
•	Omfattande loggning: Detaljerad loggning för felsökning
Support och kontakt
Utvecklare: SA7BNB Anders Isaksson
E-post: hamradio(@)sa7bnb.se
GitHub: https://github.com/sa7bnb/pocsag2025
________________________________________
POCSAG 2025 - Ett modernt, säkert och användarvänligt system för POCSAG-mottagning och hantering.

