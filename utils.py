#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import hashlib
from typing import Optional, Tuple, Set
from datetime import datetime
from pathlib import Path
from pyproj import Transformer

from config_manager import BlacklistConfig


class Logger:
    """Centraliserat loggningsverktyg for hela systemet"""
    
    log_file = None
    
    @classmethod
    def set_log_file(cls, log_file_path: Path):
        """Satt vilken fil som ska anvandas for loggning"""
        cls.log_file = log_file_path
    
    @classmethod
    def log(cls, message: str):
        """Logga meddelande med tidsstampel bade till konsol och fil"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_message = f"{timestamp} {message}"
        
        print(formatted_message)
        
        if cls.log_file:
            try:
                with open(cls.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_message}\n")
            except Exception as e:
                print(f"Loggningsfel: {e}")


class MessageProcessor:
    """Hanterar bearbetning och rensning av rameddelanden fran POCSAG-dekodern"""
    
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
    
    SWEDISH_TRANSLATION = str.maketrans({
        ']': 'Å', '[': 'Ä', '\\': 'Ö',
        '}': 'å', '{': 'ä', '|': 'ö'
    })
    
    @classmethod
    def process_message(cls, raw_message: str) -> Optional[str]:
        """Bearbeta rameddelande genom alla rensningssteg"""
        if not raw_message or not raw_message.strip():
            return None
        
        processed = raw_message.strip()
        processed = cls._fix_encoding(processed)
        processed = processed.translate(cls.SWEDISH_TRANSLATION)
        processed = cls._clean_control_characters(processed)
        
        return processed if processed else None
    
    @classmethod
    def _fix_encoding(cls, text: str) -> str:
        """Forsok att fixa potentiella kodningsproblem genom re-encoding"""
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeDecodeError:
            return text
    
    @classmethod
    def _clean_control_characters(cls, text: str) -> str:
        """Rensa oonskade kontrollsymboler och normalisera whitespace"""
        cleaned = text
        for control_char, replacement in cls.CONTROL_CHARS.items():
            cleaned = cleaned.replace(control_char, replacement)
        
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()


class BlacklistFilter:
    """Hanterar blacklist-filtrering for bade RIC-adresser och ord/fraser"""
    
    def __init__(self, blacklist_config: BlacklistConfig):
        """Initialisera blacklist-filter med konfiguration"""
        self.config = blacklist_config
        Logger.log(f"Blacklist initierad: {len(self.config.addresses)} adresser, "
                  f"{len(self.config.words)} ord, "
                  f"skiftlageskanslig: {self.config.case_sensitive}")
    
    def should_block_message(self, ric_address: str, message_content: str) -> Tuple[bool, str]:
        """Kontrollera om ett meddelande ska blockeras enligt blacklist-regler"""
        if ric_address in self.config.addresses:
            return True, f"Blockerad RIC-adress: {ric_address}"
        
        if self.config.words:
            search_text = message_content if self.config.case_sensitive else message_content.lower()
            search_words = self.config.words if self.config.case_sensitive else {word.lower() for word in self.config.words}
            
            for blocked_word in search_words:
                if blocked_word in search_text:
                    return True, f"Blockerat ord: '{blocked_word}'"
        
        return False, ""
    
    def update_config(self, blacklist_config: BlacklistConfig):
        """Uppdatera blacklist-konfiguration under korning"""
        self.config = blacklist_config
        Logger.log(f"Blacklist uppdaterad: {len(self.config.addresses)} adresser, "
                  f"{len(self.config.words)} ord")


class CoordinateConverter:
    """Hanterar koordinatkonvertering fran RT90 (svensk standard) till WGS84 (GPS-standard)"""
    
    def __init__(self):
        """Initialisera koordinatkonverterare med korrekt projektion"""
        self.transformer = Transformer.from_crs("EPSG:3021", "EPSG:4326", always_xy=True)
    
    def rt90_to_wgs84(self, x: int, y: int) -> Tuple[float, float]:
        """Konvertera RT90-koordinater till WGS84 (GPS) koordinater"""
        lon, lat = self.transformer.transform(y, x)
        return round(lat, 6), round(lon, 6)
