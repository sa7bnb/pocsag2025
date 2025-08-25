#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import hashlib
import secrets
import threading
from typing import Dict, Set, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash


@dataclass
class AuthConfig:
    """Konfigurationsklass for autentisering och sakerhet"""
    username: str = "admin"
    password_hash: str = ""
    session_timeout_hours: int = 24
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    
    def set_password(self, password: str):
        """Satt nytt losenord med saker hashning"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Kontrollera losenord mot sparad hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


@dataclass
class EmailConfig:
    """Konfigurationsklass for e-postinstallningar"""
    SMTP_SERVER: str = ""
    SMTP_PORT: str = ""
    SENDER: str = ""
    APP_PASSWORD: str = ""
    RECEIVERS: List[str] = None
    ENABLED: bool = True
    SUBJECT: str = "Pocsag Larm - Rix"
    
    def __post_init__(self):
        """Initialisera standardvarden efter skapande"""
        if self.RECEIVERS is None:
            self.RECEIVERS = []


@dataclass
class BlacklistConfig:
    """Konfigurationsklass for blacklist-funktionalitet"""
    addresses: Set[str]
    words: Set[str]
    case_sensitive: bool = False


class SessionManager:
    """Hanterar anvandarsessioner och sakerhet for inloggningsforsok"""
    
    def __init__(self):
        self.login_attempts: Dict[str, List[datetime]] = {}
        self.cleanup_interval = 3600
        self._start_cleanup_thread()
    
    def is_locked_out(self, ip_address: str, max_attempts: int, lockout_minutes: int) -> bool:
        """Kontrollera om en IP-adress ar last pa grund av for manga misslyckade forsok"""
        if ip_address not in self.login_attempts:
            return False
        
        cutoff_time = datetime.now() - timedelta(minutes=lockout_minutes)
        recent_attempts = [
            attempt for attempt in self.login_attempts[ip_address]
            if attempt > cutoff_time
        ]
        
        self.login_attempts[ip_address] = recent_attempts
        return len(recent_attempts) >= max_attempts
    
    def record_failed_attempt(self, ip_address: str):
        """Registrera ett misslyckat inloggningsforsok for en IP-adress"""
        if ip_address not in self.login_attempts:
            self.login_attempts[ip_address] = []
        self.login_attempts[ip_address].append(datetime.now())
    
    def clear_attempts(self, ip_address: str):
        """Rensa alla inloggningsforsok for en IP-adress (vid lyckad inloggning)"""
        if ip_address in self.login_attempts:
            del self.login_attempts[ip_address]
    
    def _start_cleanup_thread(self):
        """Starta bakgrundstrad for att rensa gamla inloggningsforsok"""
        def cleanup():
            while True:
                time.sleep(self.cleanup_interval)
                current_time = datetime.now()
                
                for ip, attempts in list(self.login_attempts.items()):
                    cutoff = current_time - timedelta(hours=24)
                    self.login_attempts[ip] = [a for a in attempts if a > cutoff]
                    
                    if not self.login_attempts[ip]:
                        del self.login_attempts[ip]
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()


class FileManager:
    """Hanterar alla filoperationer och konfigurationshantering"""
    
    def __init__(self):
        """Initialisera filhanterare och satt upp grundlaggande sokvagar"""
        self.base_dir = Path(__file__).parent.absolute()
        os.chdir(self.base_dir)
        
        self.config_file = self.base_dir / "config.json"
        self.log_file_all = self.base_dir / "messages.txt"
        self.log_file_filtered = self.base_dir / "filtered.messages.txt"
        self.log_file_logging = self.base_dir / "loggning.txt"
        self.blacklist_file = self.base_dir / "blacklist.txt"
    
    def initialize_files(self):
        """Skapa alla nodvandiga filer med standardkonfiguration om de inte existerar"""
        from utils import Logger
        
        if not self.config_file.exists():
            default_config = {
                "frequency": "161.4375M",
                "filters": [],
                "blacklist": {
                    "addresses": [],
                    "words": [],
                    "case_sensitive": False
                },
                "email": {
                    "SMTP_SERVER": "",
                    "SMTP_PORT": "",
                    "SENDER": "",
                    "APP_PASSWORD": "",
                    "RECEIVERS": [],
                    "ENABLED": True,
                    "SUBJECT": "Pocsag Larm - Rix"
                },
                "auth": {
                    "username": "admin",
                    "password_hash": "",
                    "session_timeout_hours": 24,
                    "max_login_attempts": 5,
                    "lockout_minutes": 15
                }
            }
            self._write_json(self.config_file, default_config)
            Logger.log("Skapade config.json med standardkonfiguration")
        
        for file_path in [self.log_file_all, self.log_file_filtered, 
                         self.log_file_logging, self.blacklist_file]:
            if not file_path.exists():
                file_path.touch()
                Logger.log(f"Skapade fil: {file_path}")
    
    def load_config(self) -> Dict:
        """Ladda konfiguration fran fil och hantera eventuell migrering av gamla format"""
        from utils import Logger
        
        config = self._read_json(self.config_file)
        
        # Migrera gammal e-postkonfiguration (RECEIVER -> RECEIVERS)
        if "email" in config and "RECEIVER" in config["email"]:
            old_receiver = config["email"]["RECEIVER"]
            if old_receiver and old_receiver not in config["email"].get("RECEIVERS", []):
                config["email"]["RECEIVERS"] = config["email"].get("RECEIVERS", []) + [old_receiver]
            del config["email"]["RECEIVER"]
            self._write_json(self.config_file, config)
            Logger.log("Migrerade gammal e-postkonfiguration till flera mottagare")
        
        # Migrera gammal blacklist fran textfil till config.json
        if "blacklist" not in config:
            config["blacklist"] = {
                "addresses": [],
                "words": [],
                "case_sensitive": False
            }
            
            if self.blacklist_file.exists():
                try:
                    content = self.blacklist_file.read_text(encoding="utf-8")
                    old_addresses = [line.strip() for line in content.splitlines() 
                                   if line.strip().isdigit()]
                    config["blacklist"]["addresses"] = old_addresses
                    Logger.log(f"Migrerade {len(old_addresses)} adresser fran blacklist.txt")
                except Exception as e:
                    Logger.log(f"Fel vid migrering av blacklist: {e}")
            
            self._write_json(self.config_file, config)
        
        # Lagg till auth-konfiguration om den saknas
        if "auth" not in config:
            config["auth"] = {
                "username": "admin",
                "password_hash": "",
                "session_timeout_hours": 24,
                "max_login_attempts": 5,
                "lockout_minutes": 15
            }
            self._write_json(self.config_file, config)
            Logger.log("Lade till autentiseringskonfiguration")
        
        # Lagg till SUBJECT om det saknas
        if "email" in config and "SUBJECT" not in config["email"]:
            config["email"]["SUBJECT"] = "Pocsag Larm - Rix"
            self._write_json(self.config_file, config)
            Logger.log("Lade till standardamnesrad for e-post")
        
        return config
    
    def save_config(self, config: Dict):
        """Spara konfiguration till fil"""
        from utils import Logger
        
        self._write_json(self.config_file, config)
        Logger.log("Konfiguration sparad till fil")
    
    def load_blacklist(self) -> BlacklistConfig:
        """Ladda blacklist-konfiguration fran huvudkonfigurationen"""
        config = self.load_config()
        blacklist_config = config.get("blacklist", {})
        
        return BlacklistConfig(
            addresses=set(blacklist_config.get("addresses", [])),
            words=set(blacklist_config.get("words", [])),
            case_sensitive=blacklist_config.get("case_sensitive", False)
        )
    
    def load_auth_config(self) -> AuthConfig:
        """Ladda autentiseringskonfiguration fran huvudkonfigurationen"""
        config = self.load_config()
        auth_config = config.get("auth", {})
        
        return AuthConfig(
            username=auth_config.get("username", "admin"),
            password_hash=auth_config.get("password_hash", ""),
            session_timeout_hours=auth_config.get("session_timeout_hours", 24),
            max_login_attempts=auth_config.get("max_login_attempts", 5),
            lockout_minutes=auth_config.get("lockout_minutes", 15)
        )
    
    def _read_json(self, file_path: Path) -> Dict:
        """Las JSON-data fran fil med korrekt encoding"""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _write_json(self, file_path: Path, data: Dict):
        """Skriv JSON-data till fil med korrekt encoding och formatering"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class EmailDeduplicator:
    """Hanterar avduplicering av e-postmeddelanden for att forhindra spam"""
    
    def __init__(self, cooldown_seconds: int = 600, auto_cleanup_minutes: int = 10):
        """Initialisera avduplicerare"""
        self.cooldown = cooldown_seconds
        self.auto_cleanup_interval = auto_cleanup_minutes * 60
        self.cache: Dict[str, float] = {}
        self.last_cleanup = time.time()
        self._start_auto_cleanup()
    
    def should_send(self, message_text: str) -> bool:
        """Kontrollera om ett e-postmeddelande ska skickas baserat pa avdupliceringsregler"""
        from utils import Logger
        
        current_time = time.time()
        
        self._check_auto_cleanup(current_time)
        
        alpha_content = self._extract_alpha_content(message_text)
        if not alpha_content:
            alpha_content = message_text
        
        message_hash = hashlib.md5(alpha_content.encode('utf-8')).hexdigest()
        
        self._clean_cache(current_time)
        
        if message_hash in self.cache:
            time_diff = current_time - self.cache[message_hash]
            if time_diff < self.cooldown:
                Logger.log(f"Email blockerad - dublett inom {self.cooldown/60:.1f} minuter (Alpha: '{alpha_content[:50]}...')")
                return False
        
        self.cache[message_hash] = current_time
        Logger.log(f"Email tillaten - nytt Alpha-innehall (hash: {message_hash[:8]})")
        return True
    
    def _extract_alpha_content(self, message_text: str) -> str:
        """Extrahera Alpha-innehallet fran meddelandet for dubblettjamforelse"""
        import re
        
        cleaned_message = re.sub(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*', '', message_text)
        
        if "Alpha:" in cleaned_message:
            alpha_content = cleaned_message.split("Alpha:", 1)[1].strip()
            return alpha_content
        
        return cleaned_message
    
    def clear_cache(self):
        """Rensa hela cachen manuellt"""
        from utils import Logger
        
        self.cache.clear()
        self.last_cleanup = time.time()
        Logger.log("Email-cache rensad manuellt")
    
    def _start_auto_cleanup(self):
        """Starta automatisk rensnings-trad som kor i bakgrunden"""
        from utils import Logger
        
        def cleanup_thread():
            while True:
                time.sleep(60)
                current_time = time.time()
                self._check_auto_cleanup(current_time)
        
        cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
        cleanup_thread.start()
        Logger.log(f"Automatisk email-cache rensning startad (var {self.auto_cleanup_interval/60:.0f}:e minut)")
    
    def _check_auto_cleanup(self, current_time: float):
        """Kontrollera om automatisk rensning ska utforas"""
        if current_time - self.last_cleanup >= self.auto_cleanup_interval:
            self.clear_cache()
            from utils import Logger
            Logger.log("Automatisk email-cache rensning utford")
    
    def _clean_cache(self, current_time: float):
        """Ta bort utgangna poster fran cache"""
        expired_keys = [key for key, timestamp in self.cache.items() 
                       if current_time - timestamp > self.cooldown]
        for key in expired_keys:
            del self.cache[key]
