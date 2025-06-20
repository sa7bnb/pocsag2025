#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import threading
import json
import os
import smtplib
import re
from flask import Flask, render_template_string, request, redirect, jsonify
from email.message import EmailMessage
from datetime import datetime
from pyproj import Transformer

# --- Konstanter ---
CONFIG_FILE = "config.json"
LOG_FILE_ALL = "messages.txt"
LOG_FILE_FILTERED = "filtered.messages.txt"

# --- Flask-init ---
app = Flask(__name__)
decoded_messages = []
filtered_messages = []
decoder_proc = None
rtl_proc = None
message_counter = 0
last_message_hash = ""
auto_update = True

# --- Transformer: RT90 -> WGS84 ---
transformer = Transformer.from_crs("EPSG:3021", "EPSG:4326", always_xy=True)

# --- Koordinatkonvertering ---
def rt90_to_wgs84(x: int, y: int):
    lon, lat = transformer.transform(y, x)
    return round(lat, 6), round(lon, 6)

# --- Skicka e-post ---
def send_email(subject):
    try:
        if not email_settings.get("ENABLED", True):
            print("E-post är avstängd.")
            return

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_settings.get("SENDER")
        msg['To'] = email_settings.get("RECEIVER")

        map_link = ""
        match = re.search(r'X=(\d+)\s+Y=(\d+)', subject)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            lat, lon = rt90_to_wgs84(x, y)
            print(f"RT90 → WGS84: X={x}, Y={y} → lat={lat}, lon={lon}")
            map_link = (
                f"\nKarta: https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}"
                f"#map=15/{lat:.6f}/{lon:.6f}"
            )
        else:
            print("Inga koordinater hittades i meddelandet.")

        msg.set_content(f"Nytt POCSAG-meddelande:\n\n{subject}{map_link}")

        with smtplib.SMTP_SSL(email_settings.get("SMTP_SERVER"), int(email_settings.get("SMTP_PORT"))) as smtp:
            smtp.login(email_settings.get("SENDER"), email_settings.get("APP_PASSWORD"))
            smtp.send_message(msg)
        print("E-post skickad.")

    except Exception as e:
        print(f"E-postfel: {e}")

# --- HTML-mallar ---
main_html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>POCSAG 2025 - © A Isaksson 2025</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f0f0f0; padding: 20px; }
    h1, h2 { color: #333; }
    form { margin-bottom: 20px; background: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 0 5px rgba(0,0,0,0.1); }
    input[type=text], textarea, select {
      width: 100%; padding: 8px; margin-top: 6px; margin-bottom: 12px;
      border: 1px solid #ccc; border-radius: 4px;
    }
    button {
      background-color: #0078d7; color: white; padding: 10px 18px;
      border: none; border-radius: 4px; cursor: pointer; font-weight: bold;
    }
    button:hover { background-color: #005ea6; }
    .message {
      font-family: monospace; background: #fff; padding: 10px;
      border-radius: 4px; margin-bottom: 5px;
      box-shadow: 0 0 3px rgba(0,0,0,0.05);
    }
  </style>
</head>
<body>
<h1>POCSAG 2025</h1>

<form method="POST" action="/setfreq">
  <label>Frekvens (MHz):</label>
  <input type="text" name="freq" value="{{ freq[:-1] }}">
  <button type="submit">Sätt Frekvens</button>
</form>

<form method="GET" action="/email">
  <button type="submit">E-postinställningar</button>
</form>

<form method="POST" action="/setfilters">
  <label>Filteradresser (RIC):</label><br>
  <textarea name="filters" rows="3" placeholder="Ex: 123456">{{ filters }}</textarea><br>
  <button type="submit">Uppdatera Filter</button>
</form>

<h2>Filtrerade Meddelanden</h2>
<div id="filtered-messages">
{% for msg in filtered %}
  <div class="message">{{ msg }}</div>
{% endfor %}
</div>

<h2>Alla Meddelanden</h2>
<div id="all-messages">
{% for msg in messages %}
  <div class="message">{{ msg }}</div>
{% endfor %}
</div>

<script>
  function refreshMessages() {
    fetch("/messages")
      .then(response => response.json())
      .then(data => {
        const filteredContainer = document.getElementById("filtered-messages");
        const allContainer = document.getElementById("all-messages");

        filteredContainer.innerHTML = data.filtered.map(msg =>
          `<div class="message">${msg}</div>`).join('');

        allContainer.innerHTML = data.all.map(msg =>
          `<div class="message">${msg}</div>`).join('');
      })
      .catch(err => console.error("Kunde inte hämta meddelanden:", err));
  }
  setInterval(refreshMessages, 10000);
</script>
</body>
</html>
"""

email_html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Email Settings</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f0f0f0; padding: 20px; }
    form { background: #ffffff; padding: 15px; border-radius: 8px; max-width: 500px; box-shadow: 0 0 5px rgba(0,0,0,0.1); }
    input[type=text], select {
      width: 100%; padding: 8px; margin-top: 6px; margin-bottom: 12px;
      border: 1px solid #ccc; border-radius: 4px;
    }
    button {
      background-color: #0078d7; color: white; padding: 10px 18px;
      border: none; border-radius: 4px; cursor: pointer; font-weight: bold;
    }
    button:hover { background-color: #005ea6; }
  </style>
</head>
<body>
<h2>E-postinställningar</h2>
<form method="POST" action="/save_email">
  SMTP-server:<br><input type="text" name="SMTP_SERVER" value="{{ smtp }}"><br>
  SMTP-port:<br><input type="text" name="SMTP_PORT" value="{{ port }}"><br>
  Avsändaradress:<br><input type="text" name="SENDER" value="{{ sender }}"><br>
  App-lösenord:<br><input type="text" name="APP_PASSWORD" value="{{ apppwd }}"><br>
  Mottagaradress:<br><input type="text" name="RECEIVER" value="{{ receiver }}"><br>
  Aktiverad:<br>
  <select name="ENABLED">
    <option value="true" {% if enabled %}selected{% endif %}>Aktiverad</option>
    <option value="false" {% if not enabled %}selected{% endif %}>Av</option>
  </select><br>
  <button type="submit">Spara</button>
</form>

<form method="POST" action="/send_test_email" style="margin-top: 10px;">
  <button type="submit">Skicka Testmeddelande</button>
</form>

<a href="/"><button style="margin-top: 10px;">Tillbaka</button></a>
</body>
</html>
"""

# --- Konfig ---
def load_config():
    if not os.path.isfile(CONFIG_FILE):
        default = {
            "frequency": "148.5625M",
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
        save_config(default)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# --- Decoder ---
def start_decoder(freq):
    global decoder_proc, rtl_proc
    stop_decoder()

    cmd = ["rtl_fm", "-f", freq, "-M", "fm", "-s", "22050", "-g", "42"]
    multimon_cmd = ["multimon-ng", "-t", "raw", "-C", "SE", "-a", "POCSAG512", "-a", "POCSAG1200", "-f", "alpha", "-"]

    rtl_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    decoder_proc = subprocess.Popen(multimon_cmd, stdin=rtl_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    def read_loop():
        global decoded_messages, filtered_messages, message_counter, last_message_hash
        for line in decoder_proc.stdout:
            line = line.strip()
            if not line:
                continue
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            tagged_line = f"{timestamp} {line}"
            if tagged_line == last_message_hash:
                continue
            last_message_hash = tagged_line
            decoded_messages.append(tagged_line)
            with open(LOG_FILE_ALL, "a", encoding="utf-8") as f:
                f.write(tagged_line + "\n")
            match = re.search(r'Address:\s*(\d+)', line)
            if match:
                address = match.group(1)
                if address in filter_addresses:
                    filtered_messages.append(tagged_line)
                    with open(LOG_FILE_FILTERED, "a", encoding="utf-8") as f:
                        f.write(tagged_line + "\n")
                    if "Alpha:" in line and email_settings.get("ENABLED", False):
                        alpha_text = line.split("Alpha:", 1)[1].strip()
                        send_email(f"{timestamp} {alpha_text}")
            decoded_messages[:] = decoded_messages[-50:]
            filtered_messages[:] = filtered_messages[-50:]
            message_counter += 1
    threading.Thread(target=read_loop, daemon=True).start()

def stop_decoder():
    global decoder_proc, rtl_proc
    try:
        if decoder_proc: decoder_proc.kill()
        if rtl_proc: rtl_proc.kill()
    except: pass

# --- Flask Routes ---
@app.route("/")
def index():
    filters_display = "\n".join(filter_addresses)
    return render_template_string(main_html, messages=decoded_messages, filtered=filtered_messages, freq=current_freq, filters=filters_display)

@app.route("/setfreq", methods=["POST"])
def setfreq():
    global current_freq, config
    raw_freq = request.form.get("freq", "").strip()
    if raw_freq:
        current_freq = raw_freq + "M"
        config["frequency"] = current_freq
        save_config(config)
        start_decoder(current_freq)
    return redirect("/")

@app.route("/setfilters", methods=["POST"])
def setfilters():
    global filter_addresses, config, filtered_messages
    filter_str = request.form.get("filters", "")
    filter_list = [f.strip() for f in filter_str.replace(",", "\n").splitlines() if f.strip()]
    filter_addresses = set(filter_list)
    config["filters"] = list(filter_addresses)
    save_config(config)
    filtered_messages = []
    start_decoder(current_freq)
    return redirect("/")

@app.route("/messages", methods=["GET"])
def get_messages():
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
    enabled_str = request.form.get("ENABLED", "true").lower()
    email_settings = {
        "SMTP_SERVER": request.form.get("SMTP_SERVER", ""),
        "SMTP_PORT": request.form.get("SMTP_PORT", ""),
        "SENDER": request.form.get("SENDER", ""),
        "APP_PASSWORD": request.form.get("APP_PASSWORD", ""),
        "RECEIVER": request.form.get("RECEIVER", ""),
        "ENABLED": enabled_str == "true"
    }
    config["email"] = email_settings
    save_config(config)
    return redirect("/")

@app.route("/send_test_email", methods=["POST"])
def send_test_email():
    test_msg = "2025-01-01 12:00:00 TEST Vägen 11 Rosenfors H7300 X=6359960 Y=1502061"
    send_email(test_msg)
    return redirect("/email")

# --- Start ---
if __name__ == "__main__":
    config = load_config()
    current_freq = config.get("frequency", "161.4375M")
    filter_addresses = set(config.get("filters", []))
    email_settings = config.get("email", {})
    print(f"Startar POCSAG-avkodare på frekvens {current_freq}")
    start_decoder(current_freq)
    app.run(host="0.0.0.0", port=5000)
