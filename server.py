#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import re
import subprocess
import threading
import smtplib
from flask import Flask, render_template_string, request, redirect, jsonify
from email.message import EmailMessage
from datetime import datetime
from pyproj import Transformer

# === Arbetskatalog och filvägar ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE_ALL = os.path.join(BASE_DIR, "messages.txt")
LOG_FILE_FILTERED = os.path.join(BASE_DIR, "filtered.messages.txt")
LOG_FILE_LOGGING = os.path.join(BASE_DIR, "loggning.txt")

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE_LOGGING, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")
    print(f"{timestamp} {msg}")

def initialize_environment():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "frequency": "161.4375M",
            "filters": [],
            "email": {
                "SMTP_SERVER": "",
                "SMTP_PORT": "",
                "SENDER": "",
                "APP_PASSWORD": "",
                "RECEIVER": "",
                "ENABLED": True
            }
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=2)
        log("Skapade config.json")
    for file in [LOG_FILE_ALL, LOG_FILE_FILTERED, LOG_FILE_LOGGING]:
        if not os.path.exists(file):
            open(file, "w", encoding="utf-8").close()
            log(f"Skapade fil: {file}")

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    log("Konfiguration sparad.")

transformer = Transformer.from_crs("EPSG:3021", "EPSG:4326", always_xy=True)
def rt90_to_wgs84(x, y):
    lon, lat = transformer.transform(y, x)
    return round(lat, 6), round(lon, 6)

def send_email(subject):
    try:
        if not email_settings.get("ENABLED", True):
            log("E-post är avstängd.")
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = email_settings["SENDER"]
        msg["To"] = email_settings["RECEIVER"]
        match = re.search(r'X=(\d+)\s+Y=(\d+)', subject)
        map_link = ""
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            lat, lon = rt90_to_wgs84(x, y)
            map_link = f"\nKarta: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"
        msg.set_content(f"Meddelande:\n\n{subject}{map_link}")
        with smtplib.SMTP_SSL(email_settings["SMTP_SERVER"], int(email_settings["SMTP_PORT"])) as smtp:
            smtp.login(email_settings["SENDER"], email_settings["APP_PASSWORD"])
            smtp.send_message(msg)
        log("E-post skickad.")
    except Exception as e:
        log(f"E-postfel: {e}")

app = Flask(__name__)
decoded_messages = []
filtered_messages = []
decoder_proc = None
rtl_proc = None
message_counter = 0
last_message_hash = ""

def start_decoder(freq):
    global decoder_proc, rtl_proc
    stop_decoder()
    log(f"Startar dekoder på frekvens: {freq}")
    rtl_cmd = ["rtl_fm", "-f", freq, "-M", "fm", "-s", "22050", "-g", "49", "-p", "0"]
    multimon_cmd = ["multimon-ng", "-t", "raw", "-a", "POCSAG512", "-a", "POCSAG1200", "-f", "alpha", "-"]
    rtl_proc = subprocess.Popen(rtl_cmd, stdout=subprocess.PIPE)
    decoder_proc = subprocess.Popen(multimon_cmd, stdin=rtl_proc.stdout, stdout=subprocess.PIPE, text=True)

    def read_loop():
        global message_counter, last_message_hash
        for line in decoder_proc.stdout:
            line = line.strip()
            if not line:
                continue
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            tagged = f"{timestamp} {line}"
            if tagged == last_message_hash:
                continue
            last_message_hash = tagged
            decoded_messages.append(tagged)
            with open(LOG_FILE_ALL, "a", encoding="utf-8") as f:
                f.write(tagged + "\n")
            match = re.search(r"Address:\s*(\d+)", line)
            if match and match.group(1) in filter_addresses:
                filtered_messages.append(tagged)
                with open(LOG_FILE_FILTERED, "a", encoding="utf-8") as f:
                    f.write(tagged + "\n")
                if "Alpha:" in line:
                    alpha = line.split("Alpha:", 1)[1].strip()
                    send_email(f"{timestamp} {alpha}")
            decoded_messages[:] = decoded_messages[-50:]
            filtered_messages[:] = filtered_messages[-50:]
            message_counter += 1
    threading.Thread(target=read_loop, daemon=True).start()

def stop_decoder():
    global decoder_proc, rtl_proc
    if decoder_proc: decoder_proc.kill()
    if rtl_proc: rtl_proc.kill()

main_html = """<!doctype html><html><head><meta charset="utf-8"><title>POCSAG 2025 - By SA7BNB</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #e9eef4; padding: 20px; }
h1 { color: #003366; }
form { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 0 8px rgba(0,0,0,0.1); }
input, textarea, select {
  width: 100%; padding: 10px; margin-bottom: 12px;
  border: 1px solid #ccc; border-radius: 4px; font-size: 14px;
}
button {
  background-color: #0078D7; color: white; padding: 10px 18px;
  border: none; border-radius: 4px; font-weight: bold;
}
button:hover { background-color: #005a9e; }
.message {
  background: #fefefe; border-left: 5px solid #0078D7;
  padding: 10px; margin-bottom: 5px; font-family: monospace;
}
</style></head><body>
<h1>POCSAG 2025 - By SA7BNB</h1>
<form method="POST" action="/setfreq">
  <label>Frekvens (MHz):</label>
  <input type="text" name="freq" value="{{ freq[:-1] }}">
  <button type="submit">Sätt Frekvens</button>
</form>
<form method="POST" action="/setfilters">
  <label>Filteradresser (RIC):</label>
  <textarea name="filters" rows="3" placeholder="Ex: 123456">{{ filters }}</textarea>
  <button type="submit">Uppdatera Filter</button>
</form>
<form method="GET" action="/email"><button type="submit">E-postinställningar</button></form>
<h2>Filtrerade Meddelanden</h2><div id="filtered-messages">{% for m in filtered %}<div class="message">{{ m }}</div>{% endfor %}</div>
<h2>Alla Meddelanden</h2><div id="all-messages">{% for m in messages %}<div class="message">{{ m }}</div>{% endfor %}</div>
<script>
setInterval(() => {
  fetch("/messages").then(r => r.json()).then(data => {
    document.getElementById("filtered-messages").innerHTML =
      data.filtered.map(m => `<div class="message">${m}</div>`).join('');
    document.getElementById("all-messages").innerHTML =
      data.all.map(m => `<div class="message">${m}</div>`).join('');
  });
}, 10000);
</script></body></html>"""

email_html = """<!doctype html><html><head><meta charset="utf-8"><title>E-postinställningar</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #e9eef4; padding: 20px; }
form { background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); max-width: 500px; }
input, select {
  width: 100%; padding: 10px; margin-bottom: 12px;
  border: 1px solid #ccc; border-radius: 4px; font-size: 14px;
}
button {
  background-color: #0078D7; color: white; padding: 10px 18px;
  border: none; border-radius: 4px; font-weight: bold;
}
button:hover { background-color: #005a9e; }
</style></head><body>
<h2>E-postinställningar</h2>
<form method="POST" action="/save_email">
  SMTP-server:<input name="SMTP_SERVER" value="{{ smtp }}">
  SMTP-port:<input name="SMTP_PORT" value="{{ port }}">
  Avsändaradress:<input name="SENDER" value="{{ sender }}">
  App-lösenord:<input name="APP_PASSWORD" value="{{ apppwd }}">
  Mottagare:<input name="RECEIVER" value="{{ receiver }}">
  <label>Aktiverad:</label>
  <select name="ENABLED">
    <option value="true" {% if enabled %}selected{% endif %}>Ja</option>
    <option value="false" {% if not enabled %}selected{% endif %}>Nej</option>
  </select>
  <button type="submit">Spara</button>
</form>
<form method="POST" action="/send_test_email" style="margin-top: 10px;">
  <button type="submit">Skicka testmeddelande</button>
</form>
<a href="/"><button style="margin-top: 10px;">Tillbaka</button></a>
</body></html>"""

@app.route("/")
def index():
    filters_display = "\n".join(filter_addresses)
    return render_template_string(main_html, messages=decoded_messages, filtered=filtered_messages, freq=current_freq, filters=filters_display)

@app.route("/setfreq", methods=["POST"])
def setfreq():
    global current_freq, config
    freq = request.form.get("freq", "").strip()
    if freq:
        current_freq = freq + "M"
        config["frequency"] = current_freq
        save_config(config)
        start_decoder(current_freq)
    return redirect("/")

@app.route("/setfilters", methods=["POST"])
def setfilters():
    global filter_addresses, config
    filters = request.form.get("filters", "")
    filter_addresses = set(f.strip() for f in filters.splitlines() if f.strip())
    config["filters"] = list(filter_addresses)
    save_config(config)
    return redirect("/")

@app.route("/messages")
def messages():
    return jsonify({"counter": message_counter, "filtered": filtered_messages, "all": decoded_messages})

@app.route("/email")
def email_page():
    return render_template_string(email_html,
        smtp=email_settings.get("SMTP_SERVER", ""),
        port=email_settings.get("SMTP_PORT", ""),
        sender=email_settings.get("SENDER", ""),
        apppwd=email_settings.get("APP_PASSWORD", ""),
        receiver=email_settings.get("RECEIVER", ""),
        enabled=email_settings.get("ENABLED", True)
    )

@app.route("/save_email", methods=["POST"])
def save_email():
    global email_settings
    email_settings = {
        "SMTP_SERVER": request.form.get("SMTP_SERVER", ""),
        "SMTP_PORT": request.form.get("SMTP_PORT", ""),
        "SENDER": request.form.get("SENDER", ""),
        "APP_PASSWORD": request.form.get("APP_PASSWORD", ""),
        "RECEIVER": request.form.get("RECEIVER", ""),
        "ENABLED": request.form.get("ENABLED", "true") == "true"
    }
    config["email"] = email_settings
    save_config(config)
    return redirect("/email")

@app.route("/send_test_email", methods=["POST"])
def send_test_email():
    send_email("TEST Vägen 11 Rosenfors H7300 X=6359960 Y=1502061")
    return redirect("/email")

if __name__ == "__main__":
    initialize_environment()
    config = load_config()
    current_freq = config.get("frequency", "148.5625M")
    filter_addresses = set(config.get("filters", []))
    email_settings = config.get("email", {})
    log(f"Startar POCSAG på {current_freq}")
    start_decoder(current_freq)
    app.run(host="0.0.0.0", port=5000)
