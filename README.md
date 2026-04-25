# 📡 POCSAG 2025

> Ett komplett system för att avkoda och hantera POCSAG-meddelanden via RTL-SDR, med webbaserat gränssnitt för övervakning, filtrering, e-postnotifieringar och konfigurationshantering.

**Utvecklad av:** [SA7BNB – Anders Isaksson](https://github.com/sa7bnb)
**Aktuell version:** `v20260425`

---

## ✨ Nyheter – 20260425

| # | Nyhet |
|---|---|
| 🎨 | Moderniserat webbgränssnitt med responsiv design och mörk headerstil |
| 🎯 | **Alpha-läge** – valbart filter som skippar rena tonpagningar utan text |
| 📡 | **Kombinerat mottagarkort** – frekvens och gain appliceras tillsammans |
| 💾 | **Backup och återställning** – spara hela konfigurationen som JSON-fil med ett klick |
| 🚫 | **Blacklist** med realtidsuppdatering för RIC-adresser och ord |
| 📧 | **Förbättrad e-posthantering** med stöd för flera mottagare och testfunktion |
| 🔐 | **Säkerhetshärdning** – persistenta sessioner, HttpOnly + SameSite-cookies, starkare lösenordshashning |
| 🔄 | **Automatisk logg-rotation** vid 10 MB – inget mer fullt SD-kort |
| ⚙️ | **Ren avstängning** av subprocesser vid systemctl stop |
| 📄 | **PDF-manualer** – fullständig användarmanual (22 sidor) + snabbstartguide (11 sidor) |

---

## 🚀 Installation (Raspberry Pi 4)

### 🖼️ Alternativ 1 – Färdig image (rekommenderas)

En färdig SD-kortsimage för **Raspberry Pi 4** med **RTL-SDR v3/v4** finns tillgänglig för nedladdning. Imagen är förberedd med:

- ✅ POCSAG 2025 förinstallerat och redo att köra
- 🛡️ **UFW** (brandvägg) – släpper bara in SSH + webbgränssnittet
- 🛡️ **Fail2ban** – blockerar automatiskt SSH-attackförsök
- 🔄 **Unattended-upgrades** – automatiska säkerhetsuppdateringar
- 🔁 **Automatisk omstart** om tjänsten hänger sig eller kraschar

> 📥 **[Ladda ner image från Google Drive](https://drive.google.com/file/d/1sJNj3YNUdfs96sRj4yPe_aglEM8JLeJd/view?usp=sharing)**

Skriv imagen till ett SD-kort med **Raspberry Pi Imager** eller **Balena Etcher**, sätt i kortet och starta Pi:n. Surfa sedan till `http://<DIN-IP-ADRESS>:5000/` och logga in.

#### Förinställda inloggningsuppgifter (IMG-version)

| Användarnamn | Lösenord |
|---|---|
| `pocsag` | `pocsag2025` |

Samma uppgifter gäller för **både SSH och webbgränssnittet**.

> ⚠️ **Byt lösenorden direkt efter första inloggningen!** De är offentligt kända. Webb-lösenordet byts i Säkerhetsinställningar; SSH-lösenordet byts med kommandot `passwd`.

IMG-filen är förkonfigurerad för **trådbundet Ethernet (LAN)**. Om du behöver använda Wi-Fi, konfigurera det via SSH med `sudo raspi-config`.

---

### 🔧 Alternativ 2 – Manuell installation

#### 1. Förbered operativsystemet

Använd **Raspberry Pi Imager** för att installera OS:

| Inställning | Värde |
|---|---|
| Enhet | Raspberry Pi 4 |
| OS | Raspberry Pi OS Lite (64-bit) |

> Via kugghjulet i Imager – aktivera SSH, ställ in användarnamn/lösenord och konfigurera Wi-Fi innan du skriver till SD-kortet.

#### 2. Hårdvara & uppstart

Anslut din **RTL-SDR v3/v4** till en USB-port på Pi:n och starta. Hitta Pi:ns IP-adress via din router.

#### 3. Installation via SSH

```bash
ssh användarnamn@DIN-IP-ADRESS
```

```bash
curl -fsSL https://raw.githubusercontent.com/sa7bnb/pocsag2025/main/install.sh | bash
```

---

## 🔑 Kom igång

När installationen är klar, öppna webbläsaren och surfa till:

```
http://<DIN-IP-ADRESS>:5000/
```

Klicka på **"Sätt upp ditt konto här"** och skapa ditt administratörskonto. Detta krävs vid första körningen för att låsa systemet.

> 💡 Använder du den färdiga IMG-filen? Hoppa över detta steg — kontot finns redan (se inloggningsuppgifterna ovan).

---

## ⚡ Konfiguration

All konfiguration sköts via webbgränssnittet:

| Inställning | Beskrivning |
|---|---|
| **Mottagare** | Frekvens och gain i samma kort — ange t.ex. `161.4375` MHz och gain `49.6` |
| **RIC-filter** | Lägg till numeriska adresser att bevaka |
| **Alpha-läge** | Kryssa i för att bara hantera meddelanden med texttext (skippar tonpagningar) |
| **Blacklist** | Blockera RIC-adresser eller ord permanent |
| **E-post** | SMTP-inställningar, mottagarlistor och anpassade ämnesrader |
| **Backup** | Ladda ner eller återställ hela konfigurationen via Säkerhetsinställningar |

---

## 🛠️ Huvudfunktioner

### 📡 Radiomottagning & meddelanden

- Stöder **POCSAG512** och **POCSAG1200**
- Realtidsvisning med stöd för svenska tecken (åäö)
- Alpha-läge för att filtrera bort rena tonpagningar
- Automatisk generering av **OpenStreetMap-länkar** vid koordinater i meddelanden (RT90 → WGS84)
- Spam-skydd som deduplicerar identiska meddelanden inom 10 minuter

### 🔐 Säkerhet

- Lösenord lagras som PBKDF2-SHA256-hash (600 000 iterationer)
- Persistenta sessioner som överlever omstart
- HttpOnly + SameSite=Strict cookies
- Brute force-skydd vid inloggning
- Strikta filrättigheter (`chmod 0600` på `config.json`)

### 🌐 Webbgränssnitt

- Responsiv design – fungerar på dator, surfplatta och mobil
- Mörkt header-tema med personsökar-logotyp
- Realtidsuppdatering av meddelandelistor var 10:e sekund
- Färgkodade meddelandelistor (filtrerade vs alla) med antalsräknare
- Scrollbara listor med plats för de 50 senaste meddelandena

### 💾 Backup och återställning

- Ladda ner hela konfigurationen som JSON-fil med ett klick
- Återställ alla inställningar på en ny installation — perfekt vid hårdvarubyte
- Inkluderar frekvens, filter, blacklist, e-post, användaruppgifter och sessionspolicy

---

## 💻 Systemkrav

| Komponent | Krav |
|---|---|
| Hårdvara | Raspberry Pi 4 (eller 3B+/5), RTL-SDR v3/v4, VHF-antenn för 161 MHz |
| OS | Raspberry Pi OS Lite (64-bit) eller Debian-baserat Linux |
| Programvara | Python 3.11+, Flask, pyproj, `multimon-ng`, `rtl-sdr`, gunicorn |

---

## 📚 Dokumentation

PDF-manualer finns tillgängliga i repot:

- 📖 **Användarmanual** (22 sidor) – komplett genomgång för egen installation, alla funktioner och felsökning
- 🚀 **Snabbstartguide** (11 sidor) – för dig som använder den färdiga IMG-filen och vill komma igång snabbt

---

## 🔄 Uppdateringar

Nya versioner av POCSAG 2025 och uppdaterade IMG-filer publiceras här på GitHub. Ta alltid en **backup av din konfiguration** innan du uppdaterar — så kan du återställa alla inställningar direkt efteråt.

---

*Utvecklad av [Anders Isaksson (SA7BNB)](https://github.com/sa7bnb)*
*Copyright © 2026 – SA7BNB · v20260425*
