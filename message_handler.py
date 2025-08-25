#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
import threading
from typing import Set, Optional, List
from datetime import datetime
from pathlib import Path

from config_manager import FileManager
from email_handler import EmailSender
from utils import Logger, MessageProcessor, BlacklistFilter


class MessageHandler:
    """Hanterar meddelanderoutning, lagring och e-post-sandning"""
    
    def __init__(self, file_manager: FileManager, email_sender: EmailSender):
        """Initialisera meddelandehanterare"""
        self.file_manager = file_manager
        self.email_sender = email_sender
        
        self.all_messages: List[str] = []
        self.filtered_messages: List[str] = []
        
        self.message_counter = 0
        self.last_message_hash = ""
    
    def handle_message(self, processed_message: str, ric_address: str, filter_addresses: Set[str]):
        """Hantera ett bearbetat meddelande fran dekodern"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        
        message_hash = f"{timestamp} {processed_message}"
        if message_hash == self.last_message_hash:
            return
        self.last_message_hash = message_hash
        
        timestamped_message = f"{timestamp} {processed_message}"
        
        self.all_messages.insert(0, timestamped_message)
        self._append_to_file(self.file_manager.log_file_all, timestamped_message)
        
        if ric_address in filter_addresses:
            self.filtered_messages.insert(0, timestamped_message)
            self._append_to_file(self.file_manager.log_file_filtered, timestamped_message)
            
            self._handle_alpha_content(processed_message, timestamp)
        
        self.all_messages = self.all_messages[:50]
        self.filtered_messages = self.filtered_messages[:50]
        self.message_counter += 1
    
    def clear_logs(self):
        """Rensa alla meddelandeloggar bade fran filer och minne"""
        self.file_manager.log_file_all.write_text("", encoding="utf-8")
        self.file_manager.log_file_filtered.write_text("", encoding="utf-8")
        
        self.all_messages.clear()
        self.filtered_messages.clear()
        
        Logger.log("Alla meddelandeloggar rensades")
    
    def _handle_alpha_content(self, processed_message: str, timestamp: str):
        """Hantera Alpha-innehall for e-post-sandning"""
        if "Alpha:" in processed_message:
            alpha_content = processed_message.split("Alpha:", 1)[1].strip()
            full_message = f"{timestamp} {alpha_content}"
            self.email_sender.send_message(full_message)
    
    def _append_to_file(self, file_path: Path, content: str):
        """Lagg till innehall i slutet av en loggfil"""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{content}\n")
        except Exception as e:
            Logger.log(f"Fel vid skrivning till {file_path}: {e}")


class DecoderManager:
    """Hanterar RTL-SDR och multimon-ng-processer for POCSAG-avkodning"""
    
    def __init__(self, message_handler: MessageHandler, blacklist_filter: BlacklistFilter):
        """Initialisera avkodningshanterare"""
        self.message_handler = message_handler
        self.blacklist_filter = blacklist_filter
        
        self.rtl_proc: Optional[subprocess.Popen] = None
        self.decoder_proc: Optional[subprocess.Popen] = None
        
        self.filter_addresses: Set[str] = set()
    
    def start_decoder(self, frequency: str):
        """Starta RTL-SDR och avkodare-processer for given frekvens"""
        self.stop_decoder()
        Logger.log(f"Startar POCSAG-dekoder pa frekvens: {frequency}")
        
        rtl_cmd = [
            "rtl_fm",
            "-f", frequency,
            "-M", "fm",
            "-s", "22050",
            "-g", "49",
            "-p", "0"
        ]
        
        multimon_cmd = [
            "multimon-ng",
            "-t", "raw",
            "-a", "POCSAG512",
            "-a", "POCSAG1200",
            "-f", "alpha",
            "-"
        ]
        
        try:
            self.rtl_proc = subprocess.Popen(
                rtl_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            self.decoder_proc = subprocess.Popen(
                multimon_cmd, 
                stdin=self.rtl_proc.stdout,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            threading.Thread(target=self._read_loop, daemon=True).start()
            
            Logger.log("POCSAG-dekoder startad framgangsrikt")
            
        except Exception as e:
            Logger.log(f"Fel vid start av dekoder: {e}")
            self.stop_decoder()
    
    def stop_decoder(self):
        """Stoppa alla avkodare-processer pa ett kontrollerat satt"""
        processes_stopped = 0
        
        for proc_name, proc in [("multimon-ng", self.decoder_proc), ("rtl_fm", self.rtl_proc)]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    processes_stopped += 1
                    Logger.log(f"{proc_name}-process stoppad")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    processes_stopped += 1
                    Logger.log(f"{proc_name}-process tvingades stoppas")
                except Exception as e:
                    Logger.log(f"Fel vid stopning av {proc_name}: {e}")
        
        self.decoder_proc = None
        self.rtl_proc = None
        
        if processes_stopped > 0:
            Logger.log(f"Dekoder stoppad ({processes_stopped} processer)")
    
    def update_filter_addresses(self, filter_addresses: Set[str]):
        """Uppdatera vilka RIC-adresser som ska fa specialbehandling"""
        self.filter_addresses = filter_addresses
        Logger.log(f"Filteradresser uppdaterade: {len(filter_addresses)} adresser")
    
    def update_blacklist(self, blacklist_filter: BlacklistFilter):
        """Uppdatera blacklist-filter under korning"""
        self.blacklist_filter = blacklist_filter
        Logger.log("Blacklist-filter uppdaterat")
    
    def _read_loop(self):
        """Huvudloop for lasning av avkodare-output"""
        if not self.decoder_proc:
            Logger.log("Ingen dekoder-process att lasa fran")
            return
        
        Logger.log("Startar lasloop for POCSAG-meddelanden")
        
        try:
            for raw_line in self.decoder_proc.stdout:
                processed_message = MessageProcessor.process_message(raw_line)
                if not processed_message:
                    continue
                
                match = re.search(r"Address:\s*(\d+)", processed_message)
                if not match:
                    continue
                
                ric_address = match.group(1)
                
                should_block, block_reason = self.blacklist_filter.should_block_message(
                    ric_address, processed_message
                )
                if should_block:
                    Logger.log(f"Meddelande blockerat: {block_reason}")
                    continue
                
                self.message_handler.handle_message(
                    processed_message, ric_address, self.filter_addresses
                )
                
        except Exception as e:
            Logger.log(f"Fel i meddelandelasloop: {e}")
        finally:
            Logger.log("Meddelandelasloop avslutad")
