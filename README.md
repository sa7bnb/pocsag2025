# 📡 POCSAG 2025

> Ett system för att avkoda och hantera POCSAG-meddelanden via RTL-SDR, med webbaserat gränssnitt för övervakning, filtrering och e-postnotifieringar.

**Utvecklad av:** [SA7BNB – Anders Isaksson](https://github.com/sa7bnb)

---

## ✨ Nyheter i version 2026

- 🆕 Blacklist-funktion med realtidsuppdatering
- 🆕 Förbättrad e-posthantering med stöd för flera mottagare och testfunktion
- 🆕 Säkerhetssystem med autentisering, sessioner och brute force-skydd
- 🆕 Moderniserat webbgränssnitt med responsiv design
- 🆕 Möjlighet att justera gain

---

## 🚀 Installation (Raspberry Pi 4)

### 1. Förbered operativsystemet

Använd **Raspberry Pi Imager** för att installera OS:

| Inställning | Värde |
|---|---|
| Enhet | Raspberry Pi 4 |
| OS | Raspberry Pi OS Lite (64-bit) |

Via kugghjulet i Imager – aktivera SSH, ställ in användarnamn/lösenord och konfigurera Wi-Fi innan du skriver till SD-kortet.

### 2. Hårdvara & uppstart

Anslut din **RTL-SDR v4** till en USB-port på Pi:n.  
Starta Pi:n och hitta dess IP-adress via routern

### 3. Installation via SSH

Anslut via terminalen:

```bash
ssh användarnamn@DIN-IP-ADRESS
```

Kör installationsskriptet:

```bash
curl -fsSL https://raw.githubusercontent.com/sa7bnb/pocsag2025/main/install.sh | bash
```

---

## 🔑 Kom igång

### Första inloggning

När installationen är klar, surfa till systemet i din webbläsare:

```
http://<DIN-IP-ADRESS>:5000/
```

Klicka på **"Sätt upp ditt konto här"** och skapa ditt administratörskonto. Detta krävs vid första körningen för att låsa systemet.

---

## ⚡ Konfiguration

All konfiguration sköts via webbgränssnittet:

| Inställning | Beskrivning |
|---|---|
| **Frekvens** | Ange önskad frekvens i MHz, t.ex. `161.4375` |
| **RIC-filter** | Lägg till numeriska adresser att bevaka |
| **Blacklist** | Blockera adresser eller ord – via webben eller direkt i `config.json` |
| **E-post** | SMTP-inställningar, mottagarlistor och anpassade ämnesrader |

---

## 🛠 Huvudfunktioner

### 📡 Radiomottagning & meddelanden

- Stöder **POCSAG512** och **POCSAG1200**
- Realtidsvisning med stöd för svenska tecken (åäö)
- Automatisk generering av kartlänkar vid koordinater i meddelanden

### 🔐 Säkerhet

- BCrypt-hashning av lösenord
- Sessioner med timeout och brute force-skydd vid inloggning

## 💻 Systemkrav

| Komponent | Krav |
|---|---|
| Hårdvara | Raspberry Pi 4, RTL-SDR v4, Antenn |
| OS | Raspberry Pi OS Lite (64-bit) |
| Programvara | Python 3.7+, `multimon-ng`, `rtl-sdr` |

---

*Utvecklad av [Anders Isaksson (SA7BNB)](https://github.com/sa7bnb)*
