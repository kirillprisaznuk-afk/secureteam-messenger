import os
import shutil
import threading
import time
from datetime import datetime, timedelta
import server.config as config

class BackupManager:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.backup_path = config.BACKUP_PATH
        self.running = False
        self.backup_thread = None
        
        if not os.path.exists(self.backup_path):
            os.makedirs(self.backup_path)
    
    def start_auto_backup(self):
        if not config.BACKUP_ENABLED:
            print("[BACKUP] Auto backup is disabled")
            return
        
        self.running = True
        self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self.backup_thread.start()
        print("[BACKUP] Auto backup started")
    
    def stop_auto_backup(self):
        self.running = False
        if self.backup_thread:
            self.backup_thread.join()
        print("[BACKUP] Auto backup stopped")
    
    def _backup_loop(self):
        while self.running:
            try:
                self.create_backup()
                self.cleanup_old_backups()
                time.sleep(config.BACKUP_INTERVAL)
            except Exception as e:
                print(f"[BACKUP] Error: {e}")
                time.sleep(60)
    
    def create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_filepath = os.path.join(self.backup_path, backup_filename)
        
        try:
            shutil.copy2(self.database_path, backup_filepath)
            print(f"[BACKUP] Created: {backup_filename}")
            return backup_filepath
        except Exception as e:
            print(f"[BACKUP] Failed to create backup: {e}")
            return None
    
    def cleanup_old_backups(self):
        try:
            cutoff_date = datetime.now() - timedelta(days=config.BACKUP_RETENTION_DAYS)
            for filename in os.listdir(self.backup_path):
                if filename.startswith("backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_path, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        print(f"[BACKUP] Deleted old backup: {filename}")
        except Exception as e:
            print(f"[BACKUP] Cleanup error: {e}")
