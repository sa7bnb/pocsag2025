#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import subprocess
import threading
import smtplib
import time
import hashlib
from typing import Dict, Set, List, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, redirect, jsonify, send_file
from email.message import EmailMessage
from pyproj import Transformer


@dataclass
class EmailConfig:
    """Konfigurationsklass för e-post"""
    SMTP_SERVER: str = ""
    SMTP_PORT: str = ""
    SENDER: str = ""
    APP_PASSWORD: str = ""
    RECEIVER: str = ""
    ENABLED: bool = True


class FileManager:
    """Hanterar filsökvägar och operationer"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        os.chdir(self.base_dir)
        
        self.config_file = self.base_dir / "config.json"
        self.log_file_all = self.base_dir / "messages.txt"
        self.log_file_filtered = self.base_dir / "filtered.messages.txt"
        self.log_file_logging = self.base_dir / "loggning.txt"
        self.blacklist_file = self.base_dir / "blacklist.txt"
    
    def initialize_files(self):
        """Skapa standardfiler om de inte existerar"""
        # Skapa standardkonfiguration om den inte existerar
        if not self.config_file.exists():
            default_config = {
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
            self._write_json(self.config_file, default_config)
            Logger.log("Skapade config.json")
        
        # Skapa tomma filer om de inte existerar
        for file_path in [self.log_file_all, self.log_file_filtered, 
                         self.log_file_logging, self.blacklist_file]:
            if not file_path.exists():
                file_path.touch()
                Logger.log(f"Skapade fil: {file_path}")
    
    def load_config(self) -> Dict:
        """Ladda konfiguration från fil"""
        return self._read_json(self.config_file)
    
    def save_config(self, config: Dict):
        """Spara konfiguration till fil"""
        self._write_json(self.config_file, config)
        Logger.log("Konfiguration sparad.")
    
    def load_blacklist(self) -> Set[str]:
        """Ladda svartlistade adresser från fil"""
        try:
            content = self.blacklist_file.read_text(encoding="utf-8")
            addresses = {line.strip() for line in content.splitlines() 
                        if line.strip().isdigit()}
            Logger.log(f"Blacklist laddad med {len(addresses)} adresser.")
            return addresses
        except Exception as e:
            Logger.log(f"Fel vid laddning av blacklist: {e}")
            return set()
    
    def _read_json(self, file_path: Path) -> Dict:
        """Läs JSON från fil"""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _write_json(self, file_path: Path, data: Dict):
        """Skriv JSON till fil"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class Logger:
    """Centraliserat loggningsverktyg"""
    
    log_file = None
    
    @classmethod
    def set_log_file(cls, log_file_path: Path):
        cls.log_file = log_file_path
    
    @classmethod
    def log(cls, message: str):
        """Logga meddelande med tidsstämpel"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_message = f"{timestamp} {message}"
        
        # Skriv till konsol
        print(formatted_message)
        
        # Skriv till fil om tillgänglig
        if cls.log_file:
            try:
                with open(cls.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_message}\n")
            except Exception as e:
                print(f"Loggningsfel: {e}")


class MessageProcessor:
    """Hanterar meddelandetext-bearbetning och rensning"""
    
    # Kontrollsymbol-mappning
    CONTROL_CHARS = {
        '<LF>': ' ', '<NUL>': ' ', '<GS>': ' ', '<CR>': ' ',
        '<EM>': ' ', '<ETX>': ' ', '<ACK>': ' ', '<HT>': ' ',
        '<BS>': ' ', '<SOH>': ' ', '<STX>': ' ', '< EOT >': ' ',
        '<ENQ>': ' ', '<BEL>': ' ', '<VT>': ' ', '<FF>': ' ',
        '<SO>': ' ', '<SI>': ' ', '<DLE>': ' ', '<DC1>': ' ',
        '<DC2>': ' ', '<DC3>': ' ', '<DC4>': ' ', '<NAK>': ' ',
        '<SYN>': ' ', '<CAN>': ' ', '<SUB>': ' ', '<ESC>': ' ',
        '<FS>': ' ', '<RS>': ' ', '<US>': ' ', '<DEL>': ' ',
    }
    
    # Svensk teckenöversättning
    SWEDISH_TRANSLATION = str.maketrans({
        ']': 'Å', '[': 'Ä', '\\': 'Ö',
        '}': 'å', '{': 'ä', '|': 'ö'
    })
    
    @classmethod
    def process_message(cls, raw_message: str) -> Optional[str]:
        """Bearbeta råmeddelande genom alla rensningssteg"""
        if not raw_message or not raw_message.strip():
            return None
        
        # Steg 1: Fixa kodning
        processed = cls._fix_encoding(raw_message.strip())
        
        # Steg 2: Konvertera POCSAG specialtecken till svenska
        processed = processed.translate(cls.SWEDISH_TRANSLATION)
        
        # Steg 3: Rensa kontrollsymboler
        processed = cls._clean_control_characters(processed)
        
        return processed if processed else None
    
    @classmethod
    def _fix_encoding(cls, text: str) -> str:
        """Försök att fixa potentiella kodningsproblem"""
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeDecodeError:
            return text
    
    @classmethod
    def _clean_control_characters(cls, text: str) -> str:
        """Rensa oönskade kontrollsymboler"""
        # Ersätt kända kontrollsymbol-mönster
        cleaned = text
        for control_char, replacement in cls.CONTROL_CHARS.items():
            cleaned = cleaned.replace(control_char, replacement)
        
        # Ta bort återstående kontrollsymboler (ASCII 0-31 och 127)
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
        
        # Rensa upp multipla mellanslag
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()


class EmailDeduplicator:
    """Hanterar e-post-avduplicering för att förhindra spam"""
    
    def __init__(self, cooldown_seconds: int = 300, auto_cleanup_minutes: int = 10):
        self.cooldown = cooldown_seconds
        self.auto_cleanup_interval = auto_cleanup_minutes * 60  # Konvertera till sekunder
        self.cache: Dict[str, float] = {}
        self.last_cleanup = time.time()
        self._start_auto_cleanup()
    
    def should_send(self, message_text: str) -> bool:
        """Kontrollera om e-post ska skickas baserat på avdupliceringsregler"""
        current_time = time.time()
        
        # Kontrollera om det är dags för automatisk rensning
        self._check_auto_cleanup(current_time)
        
        message_hash = hashlib.md5(message_text.encode('utf-8')).hexdigest()
        
        # Rensa gamla poster
        self._clean_cache(current_time)
        
        # Kontrollera om meddelandet skickades nyligen
        if message_hash in self.cache:
            time_diff = current_time - self.cache[message_hash]
            if time_diff < self.cooldown:
                Logger.log(f"Email blockerad - dublett inom {self.cooldown/60:.1f} minuter (hash: {message_hash[:8]})")
                return False
        
        # Uppdatera cache
        self.cache[message_hash] = current_time
        Logger.log(f"Email tillåten - nytt meddelande (hash: {message_hash[:8]})")
        return True
    
    def clear_cache(self):
        """Rensa hela cachen"""
        self.cache.clear()
        self.last_cleanup = time.time()
        Logger.log("Email-cache rensad")
    
    def _start_auto_cleanup(self):
        """Starta automatisk rensnings-tråd"""
        def cleanup_thread():
            while True:
                time.sleep(60)  # Kontrollera varje minut
                current_time = time.time()
                self._check_auto_cleanup(current_time)
        
        cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
        cleanup_thread.start()
        Logger.log(f"Automatisk email-cache rensning startad (var {self.auto_cleanup_interval/60:.0f}:e minut)")
    
    def _check_auto_cleanup(self, current_time: float):
        """Kontrollera om automatisk rensning ska utföras"""
        if current_time - self.last_cleanup >= self.auto_cleanup_interval:
            self.clear_cache()
            Logger.log("Automatisk email-cache rensning utförd")
    
    def _clean_cache(self, current_time: float):
        """Ta bort utgångna poster från cache"""
        expired_keys = [key for key, timestamp in self.cache.items() 
                       if current_time - timestamp > self.cooldown]
        for key in expired_keys:
            del self.cache[key]


class CoordinateConverter:
    """Hanterar koordinatkonvertering från RT90 till WGS84"""
    
    def __init__(self):
        self.transformer = Transformer.from_crs("EPSG:3021", "EPSG:4326", always_xy=True)
    
    def rt90_to_wgs84(self, x: int, y: int) -> Tuple[float, float]:
        """Konvertera RT90-koordinater till WGS84"""
        lon, lat = self.transformer.transform(y, x)
        return round(lat, 6), round(lon, 6)


class EmailSender:
    """Hanterar e-post-sändningsfunktionalitet"""
    
    def __init__(self, email_config: EmailConfig, deduplicator: EmailDeduplicator, 
                 coordinate_converter: CoordinateConverter):
        self.config = email_config
        self.deduplicator = deduplicator
        self.coord_converter = coordinate_converter
    
    def send_message(self, subject: str, alpha_content: str):
        """Skicka e-post med avduplicering-kontroll"""
        try:
            if not self.config.ENABLED:
                Logger.log("E-post är avstängd.")
                return
            
            # Kontrollera avduplicering
            if not self.deduplicator.should_send(alpha_content):
                return
            
            # Skapa e-post
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.config.SENDER
            msg["To"] = self.config.RECEIVER
            
            # Lägg till kartlänk om koordinater hittades
            map_link = self._create_map_link(subject)
            content = f"Meddelande:\n\n{subject}{map_link}"
            msg.set_content(content)
            
            # Skicka e-post
            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, int(self.config.SMTP_PORT)) as smtp:
                smtp.login(self.config.SENDER, self.config.APP_PASSWORD)
                smtp.send_message(msg)
            
            Logger.log(f"E-post skickad för: '{alpha_content}'")
            
        except Exception as e:
            Logger.log(f"E-postfel: {e}")
    
    def send_test_email(self) -> str:
        """Skicka test-e-post och returnera resultatmeddelande"""
        try:
            msg = EmailMessage()
            msg["Subject"] = "Testmail från POCSAG-systemet"
            msg["From"] = self.config.SENDER
            msg["To"] = self.config.RECEIVER
            msg.set_content("Detta är ett testmeddelande.")
            
            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, int(self.config.SMTP_PORT)) as smtp:
                smtp.login(self.config.SENDER, self.config.APP_PASSWORD)
                smtp.send_message(msg)
            
            Logger.log("Testmail skickat.")
            return "Testmail skickades OK."
            
        except Exception as e:
            error_msg = f"Fel vid testmail: {e}"
            Logger.log(error_msg)
            return error_msg
    
    def _create_map_link(self, subject: str) -> str:
        """Skapa kartlänk från koordinater i ämne"""
        match = re.search(r'X=(\d+)\s+Y=(\d+)', subject)
        if not match:
            return ""
        
        x, y = int(match.group(1)), int(match.group(2))
        lat, lon = self.coord_converter.rt90_to_wgs84(x, y)
        return f"\nKarta: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"


class MessageHandler:
    """Hanterar meddelanderoutning och lagring"""
    
    def __init__(self, file_manager: FileManager, email_sender: EmailSender):
        self.file_manager = file_manager
        self.email_sender = email_sender
        self.all_messages: List[str] = []
        self.filtered_messages: List[str] = []
        self.message_counter = 0
        self.last_message_hash = ""
    
    def handle_message(self, processed_message: str, ric_address: str, filter_addresses: Set[str]):
        """Hantera ett bearbetat meddelande"""
        # Förhindra dubblettbearbetning
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        message_hash = f"{timestamp} {processed_message}"
        if message_hash == self.last_message_hash:
            return
        self.last_message_hash = message_hash
        
        timestamped_message = f"{timestamp} {processed_message}"
        
        # Lägg till i alla meddelanden
        self.all_messages.insert(0, timestamped_message)
        self._append_to_file(self.file_manager.log_file_all, timestamped_message)
        
        # Kontrollera om det ska filtreras
        if ric_address in filter_addresses:
            self.filtered_messages.insert(0, timestamped_message)
            self._append_to_file(self.file_manager.log_file_filtered, timestamped_message)
            
            # Skicka e-post om Alpha-innehåll
            self._handle_alpha_content(processed_message, timestamp)
        
        # Håll listorna hanterbara
        self.all_messages = self.all_messages[:50]
        self.filtered_messages = self.filtered_messages[:50]
        self.message_counter += 1
    
    def clear_logs(self):
        """Rensa alla meddelandeloggar"""
        self.file_manager.log_file_all.write_text("", encoding="utf-8")
        self.file_manager.log_file_filtered.write_text("", encoding="utf-8")
        self.all_messages.clear()
        self.filtered_messages.clear()
        Logger.log("Loggfiler rensades.")
    
    def _handle_alpha_content(self, processed_message: str, timestamp: str):
        """Hantera Alpha-innehåll för e-post-sändning"""
        if "Alpha:" in processed_message:
            alpha_content = processed_message.split("Alpha:", 1)[1].strip()
            email_subject = f"{timestamp} {alpha_content}"
            self.email_sender.send_message(email_subject, alpha_content)
    
    def _append_to_file(self, file_path: Path, content: str):
        """Lägg till innehåll i fil"""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{content}\n")
        except Exception as e:
            Logger.log(f"Fel vid skrivning till {file_path}: {e}")


class DecoderManager:
    """Hanterar RTL-SDR och multimon-ng-processer"""
    
    def __init__(self, message_handler: MessageHandler, blacklisted_addresses: Set[str]):
        self.message_handler = message_handler
        self.blacklisted_addresses = blacklisted_addresses
        self.rtl_proc: Optional[subprocess.Popen] = None
        self.decoder_proc: Optional[subprocess.Popen] = None
        self.filter_addresses: Set[str] = set()
    
    def start_decoder(self, frequency: str):
        """Starta RTL-SDR och avkodare-processer"""
        self.stop_decoder()
        Logger.log(f"Startar dekoder på frekvens: {frequency}")
        
        rtl_cmd = ["rtl_fm", "-f", frequency, "-M", "fm", "-s", "22050", "-g", "49", "-p", "0"]
        multimon_cmd = ["multimon-ng", "-t", "raw", "-a", "POCSAG512", "-a", "POCSAG1200", "-f", "alpha", "-"]
        
        try:
            self.rtl_proc = subprocess.Popen(rtl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.decoder_proc = subprocess.Popen(
                multimon_cmd, 
                stdin=self.rtl_proc.stdout, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Starta läsnings-tråd
            threading.Thread(target=self._read_loop, daemon=True).start()
            
        except Exception as e:
            Logger.log(f"Fel vid start av dekoder: {e}")
    
    def stop_decoder(self):
        """Stoppa alla avkodare-processer"""
        for proc in [self.decoder_proc, self.rtl_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    Logger.log(f"Fel vid stopning av process: {e}")
        
        self.decoder_proc = None
        self.rtl_proc = None
    
    def update_filter_addresses(self, filter_addresses: Set[str]):
        """Uppdatera filteradresser"""
        self.filter_addresses = filter_addresses
    
    def _read_loop(self):
        """Huvudloop för läsning av avkodare-utdata"""
        if not self.decoder_proc:
            return
        
        try:
            for raw_line in self.decoder_proc.stdout:
                processed_message = MessageProcessor.process_message(raw_line)
                if not processed_message:
                    continue
                
                # Extrahera RIC-adress
                match = re.search(r"Address:\s*(\d+)", processed_message)
                if not match:
                    continue
                
                ric_address = match.group(1)
                
                # Hoppa över svartlistade adresser
                if ric_address in self.blacklisted_addresses:
                    continue
                
                # Hantera meddelandet
                self.message_handler.handle_message(
                    processed_message, ric_address, self.filter_addresses
                )
                
        except Exception as e:
            Logger.log(f"Fel i läsloop: {e}")


class POCSAGApp:
    """Huvudapplikationsklass"""
    
    def __init__(self):
        # Initialisera komponenter
        self.file_manager = FileManager()
        self.file_manager.initialize_files()
        
        # Sätt upp loggning
        Logger.set_log_file(self.file_manager.log_file_logging)
        
        # Ladda konfiguration
        self.config = self.file_manager.load_config()
        self.current_freq = self.config.get("frequency", "161.4375M")
        self.filter_addresses = set(self.config.get("filters", []))
        
        # Initialisera e-post-komponenter
        email_config_dict = self.config.get("email", {})
        self.email_config = EmailConfig(**email_config_dict)
        self.email_deduplicator = EmailDeduplicator()
        self.coordinate_converter = CoordinateConverter()
        self.email_sender = EmailSender(
            self.email_config, self.email_deduplicator, self.coordinate_converter
        )
        
        # Initialisera meddelandehantering
        self.message_handler = MessageHandler(self.file_manager, self.email_sender)
        
        # Ladda svartlista och initialisera avkodare
        self.blacklisted_addresses = self.file_manager.load_blacklist()
        self.decoder_manager = DecoderManager(self.message_handler, self.blacklisted_addresses)
        self.decoder_manager.update_filter_addresses(self.filter_addresses)
        
        # Initialisera Flask-app
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Sätt upp Flask-rutter"""
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/setfreq", "setfreq", self.setfreq, methods=["POST"])
        self.app.add_url_rule("/setfilters", "setfilters", self.setfilters, methods=["POST"])
        self.app.add_url_rule("/messages", "messages", self.messages)
        self.app.add_url_rule("/clear_logs", "clear_logs", self.clear_logs, methods=["POST"])
        self.app.add_url_rule("/download_all", "download_all", self.download_all)
        self.app.add_url_rule("/download_filtered", "download_filtered", self.download_filtered)
        self.app.add_url_rule("/email", "email_settings", self.email_settings, methods=["GET", "POST"])
    
    def run(self):
        """Starta applikationen"""
        Logger.log(f"Startar POCSAG på {self.current_freq}")
        self.decoder_manager.start_decoder(self.current_freq)
        self.app.run(host="0.0.0.0", port=5000, debug=False)
    
    # Flask-rutthanterare
    def index(self):
        filters_display = "\n".join(self.filter_addresses)
        return render_template_string(
            MAIN_HTML_TEMPLATE,
            messages=self.message_handler.all_messages,
            filtered=self.message_handler.filtered_messages,
            freq=self.current_freq,
            filters=filters_display
        )
    
    def setfreq(self):
        freq = request.form.get("freq", "").strip()
        if freq:
            self.current_freq = freq + "M"
            self.config["frequency"] = self.current_freq
            self.file_manager.save_config(self.config)
            self.decoder_manager.start_decoder(self.current_freq)
        return redirect("/")
    
    def setfilters(self):
        filters = request.form.get("filters", "")
        self.filter_addresses = set(f.strip() for f in filters.splitlines() if f.strip())
        self.config["filters"] = list(self.filter_addresses)
        self.file_manager.save_config(self.config)
        self.decoder_manager.update_filter_addresses(self.filter_addresses)
        return redirect("/")
    
    def messages(self):
        return jsonify({
            "counter": self.message_handler.message_counter,
            "filtered": self.message_handler.filtered_messages,
            "all": self.message_handler.all_messages
        })
    
    def clear_logs(self):
        self.message_handler.clear_logs()
        return redirect("/")
    
    def download_all(self):
        return send_file(
            self.file_manager.log_file_all,
            as_attachment=True,
            download_name="messages.txt"
        )
    
    def download_filtered(self):
        return send_file(
            self.file_manager.log_file_filtered,
            as_attachment=True,
            download_name="filtered.messages.txt"
        )
    
    def email_settings(self):
        message = ""
        if request.method == "POST":
            action = request.form.get("action")
            
            # Uppdatera e-post-konfiguration
            self.email_config.SMTP_SERVER = request.form.get("smtp_server", "").strip()
            self.email_config.SMTP_PORT = request.form.get("smtp_port", "").strip()
            self.email_config.SENDER = request.form.get("sender", "").strip()
            self.email_config.APP_PASSWORD = request.form.get("app_password", "").strip()
            self.email_config.RECEIVER = request.form.get("receiver", "").strip()
            self.email_config.ENABLED = request.form.get("enabled") == "on"
            
            # Spara till konfiguration
            self.config["email"] = {
                "SMTP_SERVER": self.email_config.SMTP_SERVER,
                "SMTP_PORT": self.email_config.SMTP_PORT,
                "SENDER": self.email_config.SENDER,
                "APP_PASSWORD": self.email_config.APP_PASSWORD,
                "RECEIVER": self.email_config.RECEIVER,
                "ENABLED": self.email_config.ENABLED
            }
            self.file_manager.save_config(self.config)
            
            if action == "test":
                message = self.email_sender.send_test_email()
        
        return render_template_string(
            EMAIL_SETTINGS_TEMPLATE,
            cfg=self.email_config,
            msg=message
        )


# HTML-mallar
MAIN_HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>POCSAG 2025 - By SA7BNB</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #e9eef4; padding: 20px; }
h1 { color: #003366; }
form { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 0 8px rgba(0,0,0,0.1); }
input, textarea, select { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
button { background-color: #0078D7; color: white; padding: 10px 18px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
button:hover { background-color: #005a9e; }
.message { background: #fefefe; border-left: 5px solid #0078D7; padding: 10px; margin-bottom: 5px; font-family: monospace; word-break: break-word; }
.inline { display: inline-block; margin-right: 10px; }
.section { margin-bottom: 30px; }
h2 { color: #003366; border-bottom: 2px solid #0078D7; padding-bottom: 5px; }
</style></head><body>

<h1>POCSAG 2025 - By SA7BNB</h1>

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
  <textarea name="filters" rows="3" placeholder="En adress per rad, t.ex:&#10;123456&#10;789012">{{ filters }}</textarea>
  <button type="submit">Uppdatera Filter</button>
</form>
</div>

<div class="section">
<form method="GET" action="/email" class="inline">
  <button type="submit">E-postinställningar</button>
</form>
<form method="GET" action="/download_filtered" class="inline">
  <button type="submit">Ladda ner filtrerade</button>
</form>
<form method="GET" action="/download_all" class="inline">
  <button type="submit">Ladda ner alla</button>
</form>
<form method="POST" action="/clear_logs" class="inline" onsubmit="return confirmClear();">
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
function confirmClear() {
  return confirm("Är du säker på att du vill ta bort alla meddelanden?");
}

// Automatisk uppdatering av meddelanden var 10:e sekund
setInterval(() => {
  fetch("/messages")
    .then(r => r.json())
    .then(data => {
      const filteredDiv = document.getElementById("filtered-messages");
      const allDiv = document.getElementById("all-messages");
      
      if (data.filtered.length > 0) {
        filteredDiv.innerHTML = data.filtered.map(m => `<div class="message">${m}</div>`).join('');
      } else {
        filteredDiv.innerHTML = '<p><em>Inga filtrerade meddelanden ännu...</em></p>';
      }
      
      if (data.all.length > 0) {
        allDiv.innerHTML = data.all.map(m => `<div class="message">${m}</div>`).join('');
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
body { 
  font-family: 'Segoe UI', Tahoma, sans-serif; 
  background: #e9eef4; 
  padding: 20px; 
  line-height: 1.6;
}
.container { 
  max-width: 600px; 
  margin: 0 auto; 
}
h1 { 
  color: #003366; 
  text-align: center;
  margin-bottom: 30px;
}
.form-container { 
  background: #fff; 
  padding: 30px; 
  border-radius: 8px; 
  box-shadow: 0 0 15px rgba(0,0,0,0.1);
}
.form-group {
  margin-bottom: 20px;
}
label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #333;
}
input[type="text"], input[type="password"] { 
  width: 100%; 
  padding: 12px; 
  border: 1px solid #ddd; 
  border-radius: 4px; 
  font-size: 14px;
  box-sizing: border-box;
}
input[type="text"]:focus, input[type="password"]:focus {
  border-color: #0078D7;
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 120, 215, 0.2);
}
.checkbox-group {
  display: flex;
  align-items: center;
  margin-bottom: 25px;
}
.checkbox-group input[type="checkbox"] {
  margin-right: 10px;
  transform: scale(1.2);
}
.button-group {
  display: flex;
  gap: 15px;
}
button { 
  flex: 1;
  background-color: #0078D7; 
  color: white; 
  padding: 12px 20px; 
  border: none; 
  border-radius: 4px; 
  font-weight: bold; 
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}
button:hover { 
  background-color: #005a9e; 
}
button[name="action"][value="test"] {
  background-color: #28a745;
}
button[name="action"][value="test"]:hover {
  background-color: #218838;
}
.info-box { 
  background: #d1ecf1; 
  border: 1px solid #bee5eb; 
  padding: 15px; 
  margin-bottom: 25px; 
  border-radius: 4px; 
  border-left: 5px solid #17a2b8;
}
.message {
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  font-weight: bold;
}
.message.success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}
.message.error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}
.back-link {
  display: inline-block;
  margin-top: 20px;
  color: #0078D7;
  text-decoration: none;
  font-weight: bold;
}
.back-link:hover {
  text-decoration: underline;
}
.help-text {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
}
</style></head><body>

<div class="container">
  <h1>E-postinställningar</h1>
  
  <div class="info-box">
    <strong>📧 Dubblettskydd:</strong> E-post med samma innehåll blockeras i 5 minuter för att undvika spam.
    <br><strong>🔒 Säkerhet:</strong> Använd app-specifika lösenord för Gmail/Outlook.
  </div>
  
  {% if msg %}
    <div class="message {% if 'OK' in msg or 'skickades' in msg %}success{% else %}error{% endif %}">
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
        <label for="receiver">Mottagare (e-postadress):</label>
        <input type="text" id="receiver" name="receiver" value="{{ cfg.RECEIVER }}" placeholder="mottagare@email.com">
      </div>
      
      <div class="checkbox-group">
        <input type="checkbox" id="enabled" name="enabled" {% if cfg.ENABLED %}checked{% endif %}>
        <label for="enabled">Aktivera e-postnotifieringar</label>
      </div>
      
      <div class="button-group">
        <button type="submit" name="action" value="save">💾 Spara inställningar</button>
        <button type="submit" name="action" value="test">📧 Skicka testmail</button>
      </div>
    </form>
  </div>
  
  <a href="/" class="back-link">← Tillbaka till startsidan</a>
</div>

</body></html>
"""


if __name__ == "__main__":
    try:
        app = POCSAGApp()
        app.run()
    except KeyboardInterrupt:
        Logger.log("Applikation avslutad av användare")
    except Exception as e:
        Logger.log(f"Kritiskt fel: {e}")
        raise