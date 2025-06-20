#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import threading
import subprocess
import smtplib
from flask import Flask, render_template_string, request, redirect, jsonify
from email.message import EmailMessage
from datetime import datetime
from pyproj import Transformer

# --- Filvägar ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE_ALL = os.path.join(BASE_DIR, "messages.txt")
LOG_FILE_FILTERED = os.path.join(BASE_DIR, "filtered.messages.txt")

# --- Flask app ---
app = Flask(__name__)
decoded_messages = []
filtered_messages = []
decoder_proc = None
rtl_proc = None
message_counter = 0
last_message_hash = ""

# --- RT90 till WGS84 ---
transformer = Transformer.from_crs("EPSG:3021", "EPSG:4326", always_xy=True)

# --- HTML-mallar (main_html + email_html) ---
main_html = """<!doctype html><html><head><meta charset="utf-8">
<title>POCSAG 2025 - © A Isaksson</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f0f0; padding: 20px; }
form { background: #fff; padding: 15px; margin-bottom: 20px; border-radius: 8px; }
input, textarea, select { width: 100%; padding: 8px; margin: 6px 0 12px; border-radius: 4px; border: 1px solid #ccc; }
button { background-color: #0078d7; color: white; padding: 10px 18px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
button:hover { background-color: #005ea6; }
.message { font-family: monospace; background: #fff; padding: 10px; border-radius: 4px; margin-bottom: 5px; }
</style></head><body>
<h1>POCSAG 2025</h1>
<form method="POST" action="/setfreq"><label>Frekvens (MHz):</label>
<input type="text" name="freq" value="{{ freq[:-1] }}"><button type="submit">Sätt Frekvens</button></form>
<form method="GET" action="/email"><button type="submit">E-postinställningar</button></form>
<form method="POST" action="/setfilters"><label>Filteradresser (RIC):</label><textarea name="filters" rows="3">{{ filters }}</textarea>
<button type="submit">Uppdatera Filter</button></form>
<h2>Filtrerade Meddelanden</h2><div id="filtered-messages">{% for msg in filtered %}<div class="message">{{ msg }}</div>{% endfor %}</div>
<h2>Alla Meddelanden</h2><div id="all-messages">{% for msg in messages %}<div class="message">{{ msg }}</div>{% endfor %}</div>
<script>
function refreshMessages() {
  fetch("/messages")
    .then(response => response.json())
    .then(data => {
      document.getElementById("filtered-messages").innerHTML = data.filtered.map(msg => `<div class="message">${msg}</div>`).join('');
      document.getElementById("all-messages").innerHTML = data.all.map(msg => `<div class="message">${msg}</div>`).join('');
    });
}
setInterval(refreshMessages, 10000);
</script></body></html>
"""

email_html = """<!doctype html><html><head><meta charset="utf-8"><title>E-postinställningar</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f0f0; padding: 20px; }
form { background: #fff; padding: 15px; max-width: 500px; border-radius: 8px; }
input, select { width: 100%; padding: 8px; margin: 6px 0 12px; border-radius: 4px; border: 1px solid #ccc; }
button { background-color: #0078d7; color: white; padding: 10px 18px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
button:hover { background-color: #005ea6; }
</style></head><body>
<h2>E-postinställningar</h2>
<form method="POST" action="/save_email">
SMTP-server:<input type="text" name="SMTP_SERVER" value="{{ smtp }}">
SMTP-port:<input type="text" name="SMTP_PORT" value="{{ port }}">
Avsändare:<input type="text" name="SENDER" value="{{ sender }}">
App-lösenord:<input type="text" name="APP_PASSWORD" value="{{ apppwd }}">
Mottagare:<input type="text" name="RECEIVER" value="{{ receiver }}">
Aktiverad:<select name="ENABLED">
<option value="true" {% if enabled %}selected{% endif %}>Aktiverad</option>
<option value="false" {% if not enabled %}selected{% endif %}>Av</option></select>
<button type="submit">Spara</button></form>
<form method="POST" action="/send_test_email" style="margin-top:10px;"><button type="submit">Skicka Testmeddelande</button></form>
<a href="/"><button style="margin-top:10px;">Tillbaka</button></a></body></html>
"""

# --- Init konfig och logg ---
def initialize_environment():
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "frequency": "161.5375M",
                "filters": [],
                "email": {
                    "SMTP_SERVER": "",
                    "SMTP_PORT": "",
                    "SENDER": "",
                    "APP_PASSWORD": "",
                    "RECEIVER": "",
                    "ENABLED": True
                }
            }, f, indent=2)
        print("Skapade config.json med standardvärden.")
    for f in [LOG_FILE_ALL, LOG_FILE_FILTERED]:
        if not os.path.isfile(f):
            open(f, "w", encoding="utf-8").close()
            print(f"Skapade {f}.")

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def rt90_to_wgs84(x, y):
    lon, lat = transformer.transform(y, x)
    return round(lat, 6), round(lon, 6)

def clean_line(text):
    return re.sub(r"<(NUL|CR|LF|BEL|TAB|STX|ETX|EOT|SOH|ACK|VT)>", " ", text)

def send_email(subject):
    try:
        if not email_settings.get("ENABLED", True): return
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_settings["SENDER"]
        msg['To'] = email_settings["RECEIVER"]

        map_link = ""
        match = re.search(r'X=(\d+)\s+Y=(\d+)', subject)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            lat, lon = rt90_to_wgs84(x, y)
            map_link = f"\nKarta: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"

        msg.set_content(f"Nytt POCSAG-meddelande:\n\n{subject}{map_link}")
        with smtplib.SMTP_SSL(email_settings["SMTP_SERVER"], int(email_settings["SMTP_PORT"])) as smtp:
            smtp.login(email_settings["SENDER"], email_settings["APP_PASSWORD"])
            smtp.send_message(msg)
    except Exception as e:
        print(f"E-postfel: {e}")

def start_decoder(freq):
    global decoder_proc, rtl_proc
    stop_decoder()
    try:
        rtl_proc = subprocess.Popen(["rtl_fm", "-f", freq, "-M", "fm", "-s", "22050", "-g", "42", "p", "36"], stdout=subprocess.PIPE)
        decoder_proc = subprocess.Popen(["multimon-ng", "-t", "raw", "-C", "SE", "-a", "POCSAG512", "-a", "POCSAG1200", "-f", "alpha", "-"],
                                        stdin=rtl_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError as e:
        print(f"Fel: {e}")
        return

    def read_loop():
        global message_counter, last_message_hash
        for line in decoder_proc.stdout:
            try:
                line = line.strip()
                if not line:
                    continue
                line = line.encode("latin1").decode("utf-8", errors="replace")
                line = clean_line(line)
                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
                full_line = f"{timestamp} {line}"
                if full_line == last_message_hash:
                    continue
                last_message_hash = full_line
                decoded_messages.append(full_line)
                with open(LOG_FILE_ALL, "a", encoding="utf-8") as f:
                    f.write(full_line + "\n")

                match = re.search(r'Address:\s*(\d+)', line)
                if match and match.group(1) in filter_addresses:
                    filtered_messages.append(full_line)
                    with open(LOG_FILE_FILTERED, "a", encoding="utf-8") as f:
                        f.write(full_line + "\n")
                    if "Alpha:" in line:
                        alpha_text = line.split("Alpha:", 1)[1].strip()
                        send_email(f"{timestamp} {alpha_text}")

                decoded_messages[:] = decoded_messages[-50:]
                filtered_messages[:] = filtered_messages[-50:]
                message_counter += 1
            except Exception as e:
                print(f"Fel i avkodning: {e}")

    threading.Thread(target=read_loop, daemon=True).start()

def stop_decoder():
    global decoder_proc, rtl_proc
    if decoder_proc: decoder_proc.kill()
    if rtl_proc: rtl_proc.kill()

# --- Flask routes ---
@app.route("/")
def index():
    filters = "\n".join(filter_addresses)
    return render_template_string(main_html, messages=decoded_messages, filtered=filtered_messages, freq=current_freq, filters=filters)

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
    filters = [f.strip() for f in request.form.get("filters", "").replace(",", "\n").splitlines() if f.strip()]
    filter_addresses = set(filters)
    config["filters"] = list(filter_addresses)
    save_config(config)
    return redirect("/")

@app.route("/messages")
def messages():
    return jsonify({
        "counter": message_counter,
        "filtered": filtered_messages,
        "all": decoded_messages
    })

@app.route("/email", methods=["GET"])
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

# --- Starta ---
if __name__ == "__main__":
    initialize_environment()
    config = load_config()
    current_freq = config.get("frequency", "148.5625M")
    filter_addresses = set(config.get("filters", []))
    email_settings = config.get("email", {})
    print(f"Startar POCSAG på frekvens {current_freq}")
    start_decoder(current_freq)
    app.run(host="0.0.0.0", port=5000)
