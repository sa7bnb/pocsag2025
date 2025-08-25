#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import List

from config_manager import EmailConfig, EmailDeduplicator
from utils import Logger, CoordinateConverter


class EmailSender:
    """Hanterar e-post-sandningsfunktionalitet med avduplicering och kartlankar"""
    
    def __init__(self, email_config: EmailConfig, deduplicator: EmailDeduplicator, 
                 coordinate_converter: CoordinateConverter):
        """Initialisera e-post-sandare med nodvandiga komponenter"""
        self.config = email_config
        self.deduplicator = deduplicator
        self.coord_converter = coordinate_converter
    
    def send_message(self, message_content: str):
        """Skicka e-post med avduplicering-kontroll till alla konfigurerade mottagare"""
        try:
            if not self.config.ENABLED:
                Logger.log("E-post ar avstangd i konfigurationen")
                return
            
            if not self.config.RECEIVERS:
                Logger.log("Inga e-postmottagare konfigurerade")
                return
            
            if not self.deduplicator.should_send(message_content):
                return
            
            msg = EmailMessage()
            msg["Subject"] = self.config.SUBJECT
            msg["From"] = self.config.SENDER
            msg["Bcc"] = ", ".join(self.config.RECEIVERS)
            
            map_link = self._create_map_link(message_content)
            content = f"Meddelande:\n\n{message_content}{map_link}"
            msg.set_content(content)
            
            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, int(self.config.SMTP_PORT)) as smtp:
                smtp.login(self.config.SENDER, self.config.APP_PASSWORD)
                smtp.send_message(msg)
            
            alpha_content = message_content.split(" Alpha:", 1)[-1].strip() if " Alpha:" in message_content else message_content
            Logger.log(f"E-post skickad till {len(self.config.RECEIVERS)} mottagare for: '{alpha_content[:50]}{'...' if len(alpha_content) > 50 else ''}'")
            
        except Exception as e:
            Logger.log(f"E-postfel: {e}")
    
    def send_test_email(self) -> str:
        """Skicka test-e-post till alla mottagare for att verifiera konfigurationen"""
        try:
            if not self.config.RECEIVERS:
                return "Inga e-postmottagare konfigurerade."
            
            msg = EmailMessage()
            msg["Subject"] = "Testmail fran POCSAG-systemet"
            msg["From"] = self.config.SENDER
            msg["Bcc"] = ", ".join(self.config.RECEIVERS)
            
            content = f"Detta ar ett testmeddelande fran POCSAG 2025-systemet.\n\n"
            content += f"Skickat till {len(self.config.RECEIVERS)} mottagare:\n"
            for i, receiver in enumerate(self.config.RECEIVERS, 1):
                content += f"{i}. {receiver}\n"
            content += f"\nTidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            msg.set_content(content)
            
            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, int(self.config.SMTP_PORT)) as smtp:
                smtp.login(self.config.SENDER, self.config.APP_PASSWORD)
                smtp.send_message(msg)
            
            success_msg = f"Testmail skickades OK till {len(self.config.RECEIVERS)} mottagare."
            Logger.log(success_msg)
            return success_msg
            
        except Exception as e:
            error_msg = f"Fel vid testmail: {e}"
            Logger.log(error_msg)
            return error_msg
    
    def _create_map_link(self, message_content: str) -> str:
        """Skapa kartlank fran RT90-koordinater som finns i meddelandet"""
        match = re.search(r'X=(\d+)\s+Y=(\d+)', message_content)
        if not match:
            return ""
        
        try:
            x, y = int(match.group(1)), int(match.group(2))
            lat, lon = self.coord_converter.rt90_to_wgs84(x, y)
            return f"\n\nKarta: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"
            
        except Exception as e:
            Logger.log(f"Fel vid koordinatkonvertering: {e}")
            return ""
