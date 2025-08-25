#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import secrets
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, jsonify, send_file, session, flash, url_for

from config_manager import FileManager, AuthConfig, EmailConfig, SessionManager, EmailDeduplicator
from utils import Logger, CoordinateConverter
from email_handler import EmailSender
from message_handler import MessageHandler, DecoderManager, BlacklistFilter


def require_auth(f):
    """Decorator for att krava autentisering pa skyddade rutter"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return redirect(url_for('login'))
        
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            timeout_hours = session.get('timeout_hours', 24)
            if datetime.now() - login_time > timedelta(hours=timeout_hours):
                session.clear()
                flash('Session har gatt ut. Logga in igen.', 'warning')
                return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


class POCSAGApp:
    """Huvudapplikationsklass som samordnar alla komponenter"""
    
    def __init__(self):
        """Initialisera alla komponenter i ratt ordning"""
        
        self.file_manager = FileManager()
        self.file_manager.initialize_files()
        
        Logger.set_log_file(self.file_manager.log_file_logging)
        Logger.log("POCSAG 2025-system startar...")
        
        self.config = self.file_manager.load_config()
        self.current_freq = self.config.get("frequency", "161.4375M")
        self.filter_addresses = set(self.config.get("filters", []))
        
        self.auth_config = self.file_manager.load_auth_config()
        self.session_manager = SessionManager()
        
        self.blacklist_config = self.file_manager.load_blacklist()
        self.blacklist_filter = BlacklistFilter(self.blacklist_config)
        
        email_config_dict = self.config.get("email", {})
        if "RECEIVERS" not in email_config_dict and "RECEIVER" in email_config_dict:
            email_config_dict["RECEIVERS"] = [email_config_dict["RECEIVER"]] if email_config_dict["RECEIVER"] else []
        
        if "SUBJECT" not in email_config_dict:
            email_config_dict["SUBJECT"] = "Pocsag Larm - Rix"
        
        self.email_config = EmailConfig(**email_config_dict)
        self.email_deduplicator = EmailDeduplicator()
        self.coordinate_converter = CoordinateConverter()
        self.email_sender = EmailSender(
            self.email_config, self.email_deduplicator, self.coordinate_converter
        )
        
        self.message_handler = MessageHandler(self.file_manager, self.email_sender)
        
        self.decoder_manager = DecoderManager(self.message_handler, self.blacklist_filter)
        self.decoder_manager.update_filter_addresses(self.filter_addresses)
        
        self.app = Flask(__name__)
        self.app.secret_key = secrets.token_hex(32)
        self._setup_routes()
        
        Logger.log("Alla komponenter initialiserade framgangsrikt")
    
    def _setup_routes(self):
        """Satt upp alla Flask-rutter"""
        self.app.add_url_rule("/login", "login", self.login, methods=["GET", "POST"])
        self.app.add_url_rule("/logout", "logout", self.logout, methods=["POST"])
        self.app.add_url_rule("/setup", "setup", self.setup, methods=["GET", "POST"])
        
        self.app.add_url_rule("/", "index", require_auth(self.index))
        self.app.add_url_rule("/setfreq", "setfreq", require_auth(self.setfreq), methods=["POST"])
        self.app.add_url_rule("/setfilters", "setfilters", require_auth(self.setfilters), methods=["POST"])
        self.app.add_url_rule("/messages", "messages", require_auth(self.messages))
        self.app.add_url_rule("/clear_logs", "clear_logs", require_auth(self.clear_logs), methods=["POST"])
        self.app.add_url_rule("/download_all", "download_all", require_auth(self.download_all))
        self.app.add_url_rule("/download_filtered", "download_filtered", require_auth(self.download_filtered))
        self.app.add_url_rule("/email", "email_settings", require_auth(self.email_settings), methods=["GET", "POST"])
        self.app.add_url_rule("/blacklist", "blacklist_settings", require_auth(self.blacklist_settings), methods=["GET", "POST"])
        self.app.add_url_rule("/auth_settings", "auth_settings", require_auth(self.auth_settings), methods=["GET", "POST"])
    
    def run(self):
        """Starta hela systemet"""
        if not self.auth_config.password_hash:
            Logger.log("VARNING: Inget losenord ar satt! Besok /setup for att satta upp autentisering.")
        
        Logger.log(f"Startar POCSAG-avkodning pa frekvens {self.current_freq}")
        self.decoder_manager.start_decoder(self.current_freq)
        
        Logger.log("Startar webbserver pa http://0.0.0.0:5000")
        self.app.run(host="0.0.0.0", port=5000, debug=False)
    
    def login(self):
        """Hantera inloggningssida och inloggningsforsok"""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
            
            if self.session_manager.is_locked_out(
                ip_address, 
                self.auth_config.max_login_attempts, 
                self.auth_config.lockout_minutes
            ):
                flash(f'For manga misslyckade forsok. Forsok igen om {self.auth_config.lockout_minutes} minuter.', 'error')
                Logger.log(f"Inloggning blockerad for IP {ip_address} - for manga forsok")
                return render_template_string(LOGIN_TEMPLATE)
            
            if (username == self.auth_config.username and 
                self.auth_config.check_password(password)):
                
                session['authenticated'] = True
                session['username'] = username
                session['login_time'] = datetime.now().isoformat()
                session['timeout_hours'] = self.auth_config.session_timeout_hours
                
                self.session_manager.clear_attempts(ip_address)
                Logger.log(f"Lyckad inloggning for anvandare '{username}' fran IP {ip_address}")
                
                return redirect(url_for('index'))
            else:
                self.session_manager.record_failed_attempt(ip_address)
                flash('Felaktigt anvandarnamn eller losenord.', 'error')
                Logger.log(f"Misslyckad inloggning for anvandare '{username}' fran IP {ip_address}")
        
        return render_template_string(LOGIN_TEMPLATE)
    
    def logout(self):
        """Logga ut anvandare och rensa session"""
        username = session.get('username', 'okand')
        session.clear()
        flash('Du har loggats ut.', 'info')
        Logger.log(f"Anvandare '{username}' loggade ut")
        return redirect(url_for('login'))
    
    def setup(self):
        """Forsta gangens-setup for att satta losenord"""
        if self.auth_config.password_hash:
            return redirect(url_for('login'))
        
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            
            if not username or len(username) < 3:
                flash('Anvandarnamn maste vara minst 3 tecken.', 'error')
            elif not password or len(password) < 6:
                flash('Losenord maste vara minst 6 tecken.', 'error')
            elif password != confirm_password:
                flash('Losenorden matchar inte.', 'error')
            else:
                self.auth_config.username = username
                self.auth_config.set_password(password)
                
                self.config["auth"] = {
                    "username": self.auth_config.username,
                    "password_hash": self.auth_config.password_hash,
                    "session_timeout_hours": self.auth_config.session_timeout_hours,
                    "max_login_attempts": self.auth_config.max_login_attempts,
                    "lockout_minutes": self.auth_config.lockout_minutes
                }
                self.file_manager.save_config(self.config)
                
                Logger.log(f"Forsta setup slutford for anvandare '{username}'")
                flash('Konto skapat! Du kan nu logga in.', 'success')
                return redirect(url_for('login'))
        
        return render_template_string(SETUP_TEMPLATE)
    
    def auth_settings(self):
        """Hantera autentiseringsinstallningar"""
        message = ""
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "change_password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                
                if not self.auth_config.check_password(current_password):
                    message = "Felaktigt nuvarande losenord."
                elif len(new_password) < 6:
                    message = "Nytt losenord maste vara minst 6 tecken."
                elif new_password != confirm_password:
                    message = "Losenorden matchar inte."
                else:
                    self.auth_config.set_password(new_password)
                    self.config["auth"]["password_hash"] = self.auth_config.password_hash
                    self.file_manager.save_config(self.config)
                    message = "Losenord andrat!"
                    Logger.log("Losenord andrat av anvandare")
            
            elif action == "update_settings":
                try:
                    new_username = request.form.get("username", "").strip()
                    timeout_hours = int(request.form.get("timeout_hours", 24))
                    max_attempts = int(request.form.get("max_attempts", 5))
                    lockout_minutes = int(request.form.get("lockout_minutes", 15))
                    
                    if len(new_username) < 3:
                        message = "Anvandarnamn maste vara minst 3 tecken."
                    elif timeout_hours < 1 or timeout_hours > 168:
                        message = "Session timeout maste vara mellan 1-168 timmar."
                    elif max_attempts < 3 or max_attempts > 20:
                        message = "Max inloggningsforsok maste vara mellan 3-20."
                    elif lockout_minutes < 5 or lockout_minutes > 1440:
                        message = "Lockout-tid maste vara mellan 5-1440 minuter."
                    else:
                        self.auth_config.username = new_username
                        self.auth_config.session_timeout_hours = timeout_hours
                        self.auth_config.max_login_attempts = max_attempts
                        self.auth_config.lockout_minutes = lockout_minutes
                        
                        self.config["auth"].update({
                            "username": new_username,
                            "session_timeout_hours": timeout_hours,
                            "max_login_attempts": max_attempts,
                            "lockout_minutes": lockout_minutes
                        })
                        self.file_manager.save_config(self.config)
                        
                        if session.get('username') != new_username:
                            session['username'] = new_username
                        
                        message = "Installningar uppdaterade!"
                        Logger.log("Autentiseringsinstallningar uppdaterade")
                
                except ValueError:
                    message = "Ogiltiga numeriska varden."
        
        return render_template_string(
            AUTH_SETTINGS_TEMPLATE,
            auth_config=self.auth_config,
            msg=message
        )
    
    def index(self):
        """Huvudsida med meddelanden och kontroller"""
        filters_display = "\n".join(self.filter_addresses)
        return render_template_string(
            MAIN_HTML_TEMPLATE,
            messages=self.message_handler.all_messages,
            filtered=self.message_handler.filtered_messages,
            freq=self.current_freq,
            filters=filters_display,
            username=session.get('username', 'Anvandare')
        )
    
    def setfreq(self):
        """Satt ny frekvens for POCSAG-mottagning"""
        freq = request.form.get("freq", "").strip()
        if freq:
            self.current_freq = freq + "M"
            self.config["frequency"] = self.current_freq
            self.file_manager.save_config(self.config)
            self.decoder_manager.start_decoder(self.current_freq)
            Logger.log(f"Frekvens andrad till {self.current_freq}")
        return redirect("/")
    
    def setfilters(self):
        """Uppdatera RIC-filteradresser"""
        filters = request.form.get("filters", "")
        self.filter_addresses = set(f.strip() for f in filters.splitlines() if f.strip())
        self.config["filters"] = list(self.filter_addresses)
        self.file_manager.save_config(self.config)
        self.decoder_manager.update_filter_addresses(self.filter_addresses)
        Logger.log(f"Filteradresser uppdaterade: {len(self.filter_addresses)} adresser")
        return redirect("/")
    
    def messages(self):
        """API-endpoint for att hamta meddelanden via AJAX"""
        return jsonify({
            "counter": self.message_handler.message_counter,
            "filtered": self.message_handler.filtered_messages,
            "all": self.message_handler.all_messages
        })
    
    def clear_logs(self):
        """Rensa alla meddelandeloggar"""
        self.message_handler.clear_logs()
        Logger.log("Meddelandeloggar rensade av anvandare")
        return redirect("/")
    
    def download_all(self):
        """Ladda ner alla meddelanden som fil"""
        return send_file(
            self.file_manager.log_file_all,
            as_attachment=True,
            download_name="messages.txt"
        )
    
    def download_filtered(self):
        """Ladda ner filtrerade meddelanden som fil"""
        return send_file(
            self.file_manager.log_file_filtered,
            as_attachment=True,
            download_name="filtered.messages.txt"
        )
    
    def email_settings(self):
        """Hantera e-postinstallningar"""
        message = ""
        if request.method == "POST":
            action = request.form.get("action")
            
            self.email_config.SMTP_SERVER = request.form.get("smtp_server", "").strip()
            self.email_config.SMTP_PORT = request.form.get("smtp_port", "").strip()
            self.email_config.SENDER = request.form.get("sender", "").strip()
            self.email_config.APP_PASSWORD = request.form.get("app_password", "").strip()
            self.email_config.SUBJECT = request.form.get("subject", "").strip() or "Pocsag Larm - Rix"
            
            receivers_input = request.form.get("receivers", "").strip()
            if receivers_input:
                receivers = []
                for line in receivers_input.splitlines():
                    for email in line.split(","):
                        email = email.strip()
                        if email and "@" in email:
                            receivers.append(email)
                self.email_config.RECEIVERS = receivers
            else:
                self.email_config.RECEIVERS = []
            
            self.email_config.ENABLED = request.form.get("enabled") == "on"
            
            self.config["email"] = {
                "SMTP_SERVER": self.email_config.SMTP_SERVER,
                "SMTP_PORT": self.email_config.SMTP_PORT,
                "SENDER": self.email_config.SENDER,
                "APP_PASSWORD": self.email_config.APP_PASSWORD,
                "RECEIVERS": self.email_config.RECEIVERS,
                "ENABLED": self.email_config.ENABLED,
                "SUBJECT": self.email_config.SUBJECT
            }
            self.file_manager.save_config(self.config)
            
            if action == "test":
                message = self.email_sender.send_test_email()
            elif action == "save":
                message = f"Installningar sparade med {len(self.email_config.RECEIVERS)} mottagare."
                Logger.log(f"E-postinstallningar uppdaterade: {len(self.email_config.RECEIVERS)} mottagare")
        
        return render_template_string(
            EMAIL_SETTINGS_TEMPLATE,
            cfg=self.email_config,
            msg=message
        )
    
    def blacklist_settings(self):
        """Hantera blacklist-installningar"""
        message = ""
        if request.method == "POST":
            addresses_input = request.form.get("addresses", "").strip()
            words_input = request.form.get("words", "").strip()
            case_sensitive = request.form.get("case_sensitive") == "on"
            
            addresses = set()
            if addresses_input:
                for line in addresses_input.splitlines():
                    addr = line.strip()
                    if addr.isdigit():
                        addresses.add(addr)
            
            words = set()
            if words_input:
                for line in words_input.splitlines():
                    word = line.strip()
                    if word:
                        words.add(word)
            
            self.blacklist_config = self.blacklist_config.__class__(
                addresses=addresses,
                words=words,
                case_sensitive=case_sensitive
            )
            
            self.config["blacklist"] = {
                "addresses": list(addresses),
                "words": list(words),
                "case_sensitive": case_sensitive
            }
            self.file_manager.save_config(self.config)
            
            self.blacklist_filter.update_config(self.blacklist_config)
            self.decoder_manager.update_blacklist(self.blacklist_filter)
            
            message = f"Blacklist uppdaterad: {len(addresses)} adresser, {len(words)} ord."
            Logger.log(message)
        
        return render_template_string(
            BLACKLIST_SETTINGS_TEMPLATE,
            addresses="\n".join(sorted(self.blacklist_config.addresses)),
            words="\n".join(sorted(self.blacklist_config.words)),
            case_sensitive=self.blacklist_config.case_sensitive,
            msg=message
        )


# HTML-mallar
LOGIN_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Logga in - POCSAG 2025</title>
<style>
body { 
  font-family: Arial, sans-serif; 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 20px;
}
.login-container {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  width: 100%;
  max-width: 400px;
}
h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 28px;
}
.form-group {
  margin-bottom: 20px;
}
label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}
input[type="text"], input[type="password"] {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
}
button {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 14px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}
.alert {
  padding: 12px;
  margin-bottom: 20px;
  border-radius: 6px;
  font-weight: 500;
}
.alert-error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
.setup-link {
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}
.setup-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}
</style></head><body>

<div class="login-container">
  <h1>POCSAG 2025</h1>
  
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for message in messages %}
        <div class="alert alert-error">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  
  <form method="POST">
    <div class="form-group">
      <label for="username">Användarnamn:</label>
      <input type="text" id="username" name="username" required>
    </div>
    
    <div class="form-group">
      <label for="password">Lösenord:</label>
      <input type="password" id="password" name="password" required>
    </div>
    
    <button type="submit">Logga in</button>
  </form>
  
  <div class="setup-link">
    <small>Första gången? <a href="/setup">Sätt upp ditt konto här</a></small>
  </div>
</div>

</body></html>
"""

SETUP_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Setup - POCSAG 2025</title>
<style>
body { 
  font-family: Arial, sans-serif; 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 20px;
}
.setup-container {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  width: 100%;
  max-width: 450px;
}
h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 28px;
}
.form-group {
  margin-bottom: 20px;
}
label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}
input[type="text"], input[type="password"] {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
}
button {
  width: 100%;
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  padding: 14px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}
.alert {
  padding: 12px;
  margin-bottom: 20px;
  border-radius: 6px;
  font-weight: 500;
}
.alert-error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
.alert-success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}
.help-text {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
}
</style></head><body>

<div class="setup-container">
  <h1>Första setup</h1>
  
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for message in messages %}
        <div class="alert {% if 'skapat' in message %}alert-success{% else %}alert-error{% endif %}">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  
  <form method="POST">
    <div class="form-group">
      <label for="username">Användarnamn:</label>
      <input type="text" id="username" name="username" required>
      <div class="help-text">Minst 3 tecken</div>
    </div>
    
    <div class="form-group">
      <label for="password">Lösenord:</label>
      <input type="password" id="password" name="password" required>
      <div class="help-text">Minst 6 tecken</div>
    </div>
    
    <div class="form-group">
      <label for="confirm_password">Bekräfta lösenord:</label>
      <input type="password" id="confirm_password" name="confirm_password" required>
    </div>
    
    <button type="submit">Skapa konto</button>
  </form>
</div>

</body></html>
"""

AUTH_SETTINGS_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Säkerhet - POCSAG 2025</title>
<style>
body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
.container { max-width: 800px; margin: 0 auto; }
h1 { color: #333; text-align: center; }
.form-container { background: #fff; padding: 30px; border-radius: 8px; margin-bottom: 20px; }
.form-group { margin-bottom: 20px; }
label { display: block; margin-bottom: 8px; font-weight: bold; }
input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
.message { padding: 15px; margin-bottom: 20px; border-radius: 4px; font-weight: bold; }
.message.success { background: #d4edda; color: #155724; }
.message.error { background: #f8d7da; color: #721c24; }
.back-link { color: #007bff; text-decoration: none; }
</style></head><body>

<div class="container">
  <h1>Säkerhetsinställningar</h1>
  
  {% if msg %}
    <div class="message {% if 'ändrat' in msg or 'uppdaterade' in msg %}success{% else %}error{% endif %}">
      {{ msg }}
    </div>
  {% endif %}
  
  <div class="form-container">
    <h3>Ändra lösenord</h3>
    <form method="POST">
      <input type="hidden" name="action" value="change_password">
      <div class="form-group">
        <label>Nuvarande lösenord:</label>
        <input type="password" name="current_password" required>
      </div>
      <div class="form-group">
        <label>Bekräfta lösenord:</label>
        <input type="password" name="confirm_password" required>
      </div>
      <button type="submit">Ändra lösenord</button>
    </form>
  </div>
  
  <div class="form-container">
    <h3>Allmänna inställningar</h3>
    <form method="POST">
      <input type="hidden" name="action" value="update_settings">
      <div class="form-group">
        <label>Användarnamn:</label>
        <input type="text" name="username" value="{{ auth_config.username }}" required>
      </div>
      <div class="form-group">
        <label>Session timeout (timmar):</label>
        <input type="number" name="timeout_hours" value="{{ auth_config.session_timeout_hours }}" min="1" max="168" required>
      </div>
      <div class="form-group">
        <label>Max inloggningsförsök:</label>
        <input type="number" name="max_attempts" value="{{ auth_config.max_login_attempts }}" min="3" max="20" required>
      </div>
      <div class="form-group">
        <label>Blockering (minuter):</label>
        <input type="number" name="lockout_minutes" value="{{ auth_config.lockout_minutes }}" min="5" max="1440" required>
      </div>
      <button type="submit">Spara inställningar</button>
    </form>
  </div>
  
  <a href="/" class="back-link">← Tillbaka till startsidan</a>
</div>

</body></html>
"""

MAIN_HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>POCSAG 2025 - By SA7BNB</title>
<style>
body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
h1 { color: #333; }
.header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 20px;
  background: #fff;
  padding: 15px 20px;
  border-radius: 8px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}
.logout-btn {
  background-color: #dc3545;
  color: white;
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.auth-link {
  background-color: #6c757d;
  color: white;
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  text-decoration: none;
  margin-right: 10px;
}
form { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
input, textarea { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 4px; }
button { background-color: #007bff; color: white; padding: 10px 18px; border: none; border-radius: 4px; cursor: pointer; }
.message { background: #fff; border-left: 5px solid #007bff; padding: 10px; margin-bottom: 5px; font-family: monospace; }
.inline { display: inline-block; margin-right: 10px; }
.section { margin-bottom: 30px; }
h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
</style></head><body>

<div class="header">
  <h1>POCSAG 2025 - By SA7BNB</h1>
  <div class="user-info">
    <span>👤 {{ username }}</span>
    <a href="/auth_settings" class="auth-link">🔐 Säkerhet</a>
    <form method="POST" action="/logout" style="margin:0;">
      <button type="submit" class="logout-btn" onclick="return confirm('Är du säker på att du vill logga ut?')">Logga ut</button>
    </form>
  </div>
</div>

<div class="section">
<form method="POST" action="/setfreq">
  <label><strong>Frekvens (MHz):</strong></label>
  <input type="text" name="freq" value="{{ freq[:-1] }}" placeholder="161.4375">
  <button type="submit">Sätt Frekvens</button>
</form>
</div>

<div class="section">
<form method="POST" action="/setfilters">
  <label><strong>Filteradresser (RIC):</strong></label>
  <textarea name="filters" rows="3" placeholder="En adress per rad">{{ filters }}</textarea>
  <button type="submit">Uppdatera Filter</button>
</form>
</div>

<div class="section">
<form method="GET" action="/email" class="inline">
  <button type="submit">E-postinställningar</button>
</form>
<form method="GET" action="/blacklist" class="inline">
  <button type="submit" style="background-color: #dc3545;">🚫 Blacklist</button>
</form>
<form method="GET" action="/download_filtered" class="inline">
  <button type="submit">Ladda ner filtrerade</button>
</form>
<form method="GET" action="/download_all" class="inline">
  <button type="submit">Ladda ner alla</button>
</form>
<form method="POST" action="/clear_logs" class="inline" onsubmit="return confirm('Är du säker?');">
  <button type="submit">Rensa Meddelanden</button>
</form>
</div>

<div class="section">
<h2>Filtrerade Meddelanden</h2>
<div id="filtered-messages">
  {% for m in filtered %}
    <div class="message">{{ m }}</div>
  {% endfor %}
  {% if not filtered %}
    <p><em>Inga filtrerade meddelanden ännu...</em></p>
  {% endif %}
</div>
</div>

<div class="section">
<h2>Alla Meddelanden</h2>
<div id="all-messages">
  {% for m in messages %}
    <div class="message">{{ m }}</div>
  {% endfor %}
  {% if not messages %}
    <p><em>Inga meddelanden ännu...</em></p>
  {% endif %}
</div>
</div>

<script>
setInterval(() => {
  fetch("/messages")
    .then(r => r.json())
    .then(data => {
      const filteredDiv = document.getElementById("filtered-messages");
      const allDiv = document.getElementById("all-messages");
      
      if (data.filtered.length > 0) {
        filteredDiv.innerHTML = data.filtered.map(m => '<div class="message">' + m + '</div>').join('');
      } else {
        filteredDiv.innerHTML = '<p><em>Inga filtrerade meddelanden ännu...</em></p>';
      }
      
      if (data.all.length > 0) {
        allDiv.innerHTML = data.all.map(m => '<div class="message">' + m + '</div>').join('');
      } else {
        allDiv.innerHTML = '<p><em>Inga meddelanden ännu...</em></p>';
      }
    })
    .catch(err => console.log('Fel vid uppdatering:', err));
}, 10000);
</script>
</body></html>
"""

EMAIL_SETTINGS_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>E-postinställningar - POCSAG 2025</title>
<style>
body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
.container { max-width: 600px; margin: 0 auto; }
h1 { color: #333; text-align: center; }
.form-container { background: #fff; padding: 30px; border-radius: 8px; }
.form-group { margin-bottom: 20px; }
label { display: block; margin-bottom: 8px; font-weight: bold; }
input, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
textarea { resize: vertical; min-height: 80px; }
.button-group { display: flex; gap: 15px; }
button { flex: 1; background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; }
button[name="action"][value="test"] { background-color: #28a745; }
.message { padding: 15px; margin-bottom: 20px; border-radius: 4px; font-weight: bold; }
.message.success { background: #d4edda; color: #155724; }
.message.error { background: #f8d7da; color: #721c24; }
.back-link { color: #007bff; text-decoration: none; }
.help-text { font-size: 12px; color: #666; margin-top: 5px; }
</style></head><body>

<div class="container">
  <h1>E-postinställningar</h1>
  
  {% if msg %}
    <div class="message {% if 'OK' in msg or 'sparade' in msg %}success{% else %}error{% endif %}">
      {{ msg }}
    </div>
  {% endif %}
  
  <div class="form-container">
    <form method="POST">
      <div class="form-group">
        <label for="smtp_server">SMTP-server:</label>
        <input type="text" id="smtp_server" name="smtp_server" value="{{ cfg.SMTP_SERVER }}" placeholder="smtp.gmail.com">
        <div class="help-text">Gmail: smtp.gmail.com | Outlook: smtp-mail.outlook.com</div>
      </div>
      
      <div class="form-group">
        <label for="smtp_port">SMTP-port:</label>
        <input type="text" id="smtp_port" name="smtp_port" value="{{ cfg.SMTP_PORT }}" placeholder="587">
        <div class="help-text">Vanligtvis 587 för TLS eller 465 för SSL</div>
      </div>
      
      <div class="form-group">
        <label for="sender">Avsändare (e-postadress):</label>
        <input type="text" id="sender" name="sender" value="{{ cfg.SENDER }}" placeholder="din@email.com">
      </div>
      
      <div class="form-group">
        <label for="app_password">App-lösenord:</label>
        <input type="password" id="app_password" name="app_password" value="{{ cfg.APP_PASSWORD }}" placeholder="Ditt app-specifika lösenord">
        <div class="help-text">Skapa app-lösenord i dina Gmail/Outlook säkerhetsinställningar</div>
      </div>
      
      <div class="form-group">
        <label for="subject">Ämnesrad för e-post:</label>
        <input type="text" id="subject" name="subject" value="{{ cfg.SUBJECT }}" placeholder="Pocsag Larm - Rix">
        <div class="help-text">Ämnesraden som används för alla e-postnotifieringar</div>
      </div>
      
      <div class="form-group">
        <label for="receivers">Mottagare (e-postadresser):</label>
        <textarea id="receivers" name="receivers" placeholder="En e-postadress per rad eller separera med komma">{{ '\n'.join(cfg.RECEIVERS) }}</textarea>
        <div class="help-text">Lägg till flera mottagare på separata rader eller separera med komma. Alla får e-post via BCC (dold kopia).</div>
      </div>
      
      <div class="form-group">
        <label>
          <input type="checkbox" name="enabled" {% if cfg.ENABLED %}checked{% endif %}> Aktivera e-postnotifieringar
        </label>
      </div>
      
      <div class="button-group">
        <button type="submit" name="action" value="save">💾 Spara inställningar</button>
        <button type="submit" name="action" value="test">📧 Skicka testmail</button>
      </div>
    </form>
  </div>
  
  <p><a href="/" class="back-link">← Tillbaka till startsidan</a></p>
</div>

</body></html>
"""

BLACKLIST_SETTINGS_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Blacklist - POCSAG 2025</title>
<style>
body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
.container { max-width: 700px; margin: 0 auto; }
h1 { color: #333; text-align: center; }
.form-container { background: #fff; padding: 30px; border-radius: 8px; }
.form-row { display: flex; gap: 20px; }
.form-group { margin-bottom: 20px; flex: 1; }
label { display: block; margin-bottom: 8px; font-weight: bold; }
textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; resize: vertical; min-height: 150px; font-family: monospace; }
button { background-color: #dc3545; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
.message { padding: 15px; margin-bottom: 20px; border-radius: 4px; font-weight: bold; background: #d4edda; color: #155724; }
.back-link { color: #007bff; text-decoration: none; }
.help-text { font-size: 12px; color: #666; margin-top: 5px; }
.warning-box { background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; margin-bottom: 25px; border-radius: 4px; color: #721c24; }
</style></head><body>

<div class="container">
  <h1>🚫 Blacklist-inställningar</h1>
  
  <div class="warning-box">
    <strong>⚠️ Varning:</strong> Meddelanden som matchar blacklist-reglerna kommer att blockeras permanent och visas inte i gränssnittet eller loggar.
  </div>
  
  {% if msg %}
    <div class="message">{{ msg }}</div>
  {% endif %}
  
  <div class="form-container">
    <form method="POST">
      <div class="form-row">
        <div class="form-group">
          <label for="addresses">Blockerade RIC-adresser:</label>
          <textarea id="addresses" name="addresses" placeholder="En RIC-adress per rad, endast siffror:&#10;123456&#10;789012">{{ addresses }}</textarea>
          <div class="help-text">Ange en RIC-adress per rad. Endast numeriska värden accepteras.</div>
        </div>
        
        <div class="form-group">
          <label for="words">Blockerade ord/fraser:</label>
          <textarea id="words" name="words" placeholder="Ett ord eller fras per rad:&#10;SPAM&#10;Test meddelande">{{ words }}</textarea>
          <div class="help-text">Ange ett ord eller en fras per rad. Meddelanden som innehåller dessa kommer att blockeras.</div>
        </div>
      </div>
      
      <div class="form-group">
        <label>
          <input type="checkbox" name="case_sensitive" {% if case_sensitive %}checked{% endif %}> Skiftlägeskänslig ordfiltrering
        </label>
        <div class="help-text">Om aktiverad: "TEST" och "test" behandlas som olika ord. Om inaktiverad: båda blockeras.</div>
      </div>
      
      <button type="submit">🚫 Uppdatera Blacklist</button>
    </form>
  </div>
  
  <p><a href="/" class="back-link">← Tillbaka till startsidan</a></p>
</div>

</body></html>
"""


if __name__ == "__main__":
    """Huvudingång för POCSAG 2025-systemet"""
    try:
        Logger.log("=== POCSAG 2025-system startar ===")
        app = POCSAGApp()
        app.run()
    except KeyboardInterrupt:
        Logger.log("Applikation avslutad av användare (Ctrl+C)")
    except Exception as e:
        Logger.log(f"Kritiskt fel i huvudprogrammet: {e}")
        raise
    finally:
        Logger.log("=== POCSAG 2025-system avslutat ===")
