import os
import base64
from server.rbac import RBAC
import server.config as config

class FileHandler:
    def __init__(self, database, auth_manager, encryptor):
        self.db = database
        self.auth = auth_manager
        self.encryptor = encryptor
        
        if not os.path.exists(config.UPLOAD_DIRECTORY):
            os.makedirs(config.UPLOAD_DIRECTORY)
    
    def handle_file_upload(self, token: str, chat_id: int, filename: str,
                           file_data: str, ip_address: str) -> dict:
        user_id = self.auth.verify_session(token)
        if user_id is None:
            return {"success": False, "error": "Invalid session"}
        
        if not RBAC.can_access_chat(self.db, user_id, chat_id):
            return {"success": False, "error": "Access denied"}
        
        try:
            file_bytes = base64.b64decode(file_data)
            if len(file_bytes) > config.MAX_FILE_SIZE:
                return {"success": False, "error": "File too large"}
            
            encrypted_file = self.encryptor.encrypt_file(file_bytes)
            safe_filename = f"{chat_id}_{user_id}_{filename}"
            filepath = os.path.join(config.UPLOAD_DIRECTORY, safe_filename)
            
            with open(filepath, 'wb') as f:
                f.write(encrypted_file)
            
            self.db.save_message(chat_id, user_id, f"File: {filename}", is_encrypted=True)
            self.db.log_audit(user_id, "FILE_UPLOAD",
                              f"Chat: {chat_id}, File: {filename}", ip_address)
            
            return {"success": True, "filename": safe_filename}
        except Exception as e:
            return {"success": False, "error": str(e)}
