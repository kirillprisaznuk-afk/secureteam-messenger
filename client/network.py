import socket
from shared.protocol import Protocol, MessageType
import client.config as config


class NetworkClient:
    def __init__(self, host: str = config.SERVER_HOST, port: int = config.SERVER_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.user_info = None  

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)
            self.connected = True
            print(f"[CLIENT] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False

    def disconnect(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        print("[CLIENT] Disconnected")

    def send_message(self, msg_type: MessageType, data: dict) -> dict:
        if not self.connected:
            return {"success": False, "error": "Not connected"}
        try:
            message = Protocol.create_message(msg_type, data)
            self.socket.sendall(message)
            response_data = Protocol.read_message(self.socket)
            if response_data:
                _, response = Protocol.parse_message(response_data)
                return response
            return {"success": False, "error": "No response"}
        except Exception as e:
            print(f"[CLIENT] Send failed: {e}")
            self.connected = False
            return {"success": False, "error": str(e)}


    def login(self, username: str, password: str) -> dict:
        resp = self.send_message(MessageType.LOGIN, {
            "username": username,
            "password": password,
        })
        if resp.get("success"):
            self.user_info = {
                "user_id": resp.get("user_id"),
                "username": resp.get("username"),
                "role": resp.get("role"),
            }
        return resp

    def send_text_message(self, chat_id: int, content: str) -> dict:
        return self.send_message(MessageType.TEXT_MESSAGE, {
            "chat_id": chat_id,
            "content": content,
        })

    def get_chat_list(self) -> dict:
        return self.send_message(MessageType.GET_CHAT_LIST, {})

    def get_chat_history(self, chat_id: int) -> dict:
        return self.send_message(MessageType.GET_CHAT_HISTORY, {
            "chat_id": chat_id,
        })

    def create_chat(self, name: str) -> dict:
        return self.send_message(MessageType.CREATE_CHAT, {
            "name": name,
        })


    def create_user(self, username: str, password: str, role: str) -> dict:
        return self.send_message(MessageType.CREATE_USER, {
            "username": username,
            "password": password,
            "role": role,
        })

    def get_all_users(self) -> dict:
        return self.send_message(MessageType.GET_ALL_USERS, {})

    def update_user(self, user_id: int, role: str) -> dict:
        return self.send_message(MessageType.UPDATE_USER, {
            "user_id": user_id,
            "role": role,
        })

    def block_user(self, user_id: int) -> dict:
        return self.send_message(MessageType.BLOCK_USER, {
            "user_id": user_id,
        })

    def unblock_user(self, user_id: int) -> dict:
        return self.send_message(MessageType.UNBLOCK_USER, {
            "user_id": user_id,
        })

    def delete_user(self, user_id: int) -> dict:
        return self.send_message(MessageType.DELETE_USER, {
            "user_id": user_id,
        })


    def admin_get_all_chats(self) -> dict:
        return self.send_message(MessageType.ADMIN_GET_ALL_CHATS, {})

    def admin_get_chat_info(self, chat_id: int) -> dict:
        return self.send_message(MessageType.ADMIN_GET_CHAT_INFO, {
            "chat_id": chat_id,
        })

    def admin_create_chat(self, name: str, member_ids: list[int]) -> dict:
        return self.send_message(MessageType.ADMIN_CREATE_CHAT, {
            "name": name,
            "members": member_ids,
        })

    def admin_update_chat(self, chat_id: int, name: str, member_ids: list[int]) -> dict:
        return self.send_message(MessageType.ADMIN_UPDATE_CHAT, {
            "chat_id": chat_id,
            "name": name,
            "members": member_ids,
        })

    def admin_archive_chat(self, chat_id: int) -> dict:
        return self.send_message(MessageType.ADMIN_ARCHIVE_CHAT, {
            "chat_id": chat_id,
        })

    def admin_unarchive_chat(self, chat_id: int) -> dict:
        return self.send_message(MessageType.ADMIN_UNARCHIVE_CHAT, {
            "chat_id": chat_id,
        })

    def admin_delete_chat(self, chat_id: int) -> dict:
        return self.send_message(MessageType.ADMIN_DELETE_CHAT, {
            "chat_id": chat_id,
        })


    def get_audit_entries(self, limit: int = 200) -> dict:

        return self.send_message(
            MessageType.PING,
            {"audit": True, "limit": limit},
        )
