from server.rbac import RBAC

class MessageHandler:
    def __init__(self, database, auth_manager, encryptor):
        self.db = database
        self.auth = auth_manager
        self.encryptor = encryptor
    
    def handle_text_message(self, token: str, chat_id: int, content: str, ip: str) -> dict:
        user_id = self.auth.verify_session(token)
        if not user_id:
            return {"success": False, "error": "Invalid session"}
        
        if not RBAC.can_access_chat(self.db, user_id, chat_id):
            self.db.log_audit(user_id, "UNAUTHORIZED_ACCESS", f"Chat: {chat_id}", ip)
            return {"success": False, "error": "Access denied"}
        
        encrypted_content = self.encryptor.encrypt(content)
        message_id = self.db.save_message(chat_id, user_id, encrypted_content, True)
        self.db.log_audit(user_id, "SEND_MESSAGE", f"Chat: {chat_id}", ip)
        
        return {"success": True, "message_id": message_id}
    
    def handle_get_chat_history(self, token: str, chat_id: int) -> dict:
        user_id = self.auth.verify_session(token)
        if not user_id:
            return {"success": False, "error": "Invalid session"}
        
        if not RBAC.can_access_chat(self.db, user_id, chat_id):
            return {"success": False, "error": "Access denied"}
        
        messages = self.db.get_chat_messages(chat_id)
        decrypted_messages = []
        for msg in messages:
            try:
                content = self.encryptor.decrypt(msg.content) if msg.is_encrypted else msg.content
                decrypted_messages.append({
                    "id": msg.id,
                    "user_id": msg.user_id,
                    "username": msg.username,
                    "content": content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else ""
                })
            except Exception:
                pass
        
        return {"success": True, "messages": decrypted_messages}
    
    def handle_create_chat(self, token: str, chat_name: str, ip: str) -> dict:
        user_id = self.auth.verify_session(token)
        if not user_id:
            return {"success": False, "error": "Invalid session"}
        
        user = self.db.get_user_by_id(user_id)
        if not RBAC.has_permission(user.role, 'create_chat'):
            return {"success": False, "error": "Permission denied"}
        
        chat_id = self.db.create_chat(chat_name, user_id)
        self.db.log_audit(user_id, "CREATE_CHAT", f"Chat: {chat_name}", ip)
        return {"success": True, "chat_id": chat_id}
    
    def handle_get_chat_list(self, token: str) -> dict:
        user_id = self.auth.verify_session(token)
        if not user_id:
            return {"success": False, "error": "Invalid session"}
        
        chats = self.db.get_user_chats(user_id)
        chat_list = []
        for chat in chats:
            chat_list.append({
                "id": chat.id,
                "name": chat.name,
                "created_at": chat.created_at.isoformat() if chat.created_at else ""
            })
        
        return {"success": True, "chats": chat_list}
