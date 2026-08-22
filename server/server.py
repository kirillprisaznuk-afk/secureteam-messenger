import socket
import threading
import sys
import hashlib

from shared.protocol import Protocol, MessageType
from server.database import Database
import server.config as config


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MessengerServer:
    def __init__(self, host: str = config.HOST, port: int = config.PORT):
        self.host = host
        self.port = port
        self.server_socket: socket.socket | None = None
        self.running = False

        print("=" * 60)
        print("CORPORATE MESSENGER SERVER")
        print("=" * 60)
        print("[SERVER] Initializing database...")

        self.db = Database(config.DATABASE_PATH)

        self._ensure_default_admin()

        self.clients: dict[socket.socket, int] = {}

        print("[SERVER] Server initialized!")
        print("=" * 60)


    def _ensure_default_admin(self):

        with self.db.lock, self.db._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            cnt = c.fetchone()[0]
            if cnt == 0:
                print("[SERVER] Creating default admin user: admin/admin123")
                self.db.create_user("admin", hash_password("admin123"), "owner")

    def _get_online_user_ids(self) -> set[int]:

        return set(self.clients.values())


    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(config.MAX_CONNECTIONS)

            self.running = True

            print(f"[SERVER] Server started on {self.host}:{self.port}")
            print("[SERVER] Waiting for connections...")
            print("=" * 60)

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"[SERVER] New connection from {address}")

                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True,
                    )
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[SERVER] Accept error: {e}")
        except Exception as e:
            print(f"[SERVER] Failed to start: {e}")
            sys.exit(1)

    def stop(self):
        print("\n[SERVER] Shutting down...")
        self.running = False

        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except Exception:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        print("[SERVER] Server stopped")


    def handle_client(self, client_socket: socket.socket, address):
        ip_address = address[0]
        user_id: int | None = None

        try:
            while self.running:
                data = Protocol.read_message(client_socket)
                if not data:
                    break

                msg_type, msg_data = Protocol.parse_message(data)
                response = self.process_message(msg_type, msg_data, user_id, ip_address)

                if msg_type == MessageType.LOGIN and response.get("success"):
                    user_id = response.get("user_id")
                    self.clients[client_socket] = user_id

                response_data = Protocol.create_message(MessageType.ACK, response)
                client_socket.sendall(response_data)

        except Exception as e:
            print(f"[SERVER] Error handling client {address}: {e}")
        finally:
            if client_socket in self.clients:
                del self.clients[client_socket]
            try:
                client_socket.close()
            except Exception:
                pass
            print(f"[SERVER] Client {address} disconnected")


    def process_message(
        self,
        msg_type: MessageType,
        msg_data: dict,
        user_id: int | None,
        ip_address: str,
    ) -> dict:

        if msg_type == MessageType.LOGIN:
            username = msg_data.get("username")
            password = msg_data.get("password")

            row = self.db.verify_user(username, hash_password(password))
            if not row:
                return {"success": False, "error": "Invalid credentials"}

            return {
                "success": True,
                "user_id": row["id"],
                "username": row["username"],
                "role": row["role"],
            }

        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        user = self.db.get_user_by_id(user_id)
        role = user["role"] if user else "guest"
        actor_username = user["username"] if user else "unknown"

        is_super_admin = role in ("owner", "org_admin")
        is_dept_manager = role == "department_manager"

        if msg_type == MessageType.GET_CHAT_LIST:
            chats = self.db.get_chat_list_for_user(user_id)
            return {"success": True, "chats": chats}

        elif msg_type == MessageType.GET_CHAT_HISTORY:
            chat_id = msg_data.get("chat_id")
            if not chat_id:
                return {"success": False, "error": "Bad request"}
            messages = self.db.get_chat_messages(chat_id)
            return {"success": True, "messages": messages}

        elif msg_type == MessageType.CREATE_CHAT:
            name = msg_data.get("name")
            if not name:
                return {"success": False, "error": "Bad request"}
            chat_id = self.db.create_chat(name, user_id)
            return {"success": True, "chat_id": chat_id}

        elif msg_type == MessageType.TEXT_MESSAGE:
            chat_id = msg_data.get("chat_id")
            content = msg_data.get("content", "").strip()
            if not chat_id or not content:
                return {"success": False, "error": "Bad request"}
            msg_id = self.db.add_message(chat_id, user_id, content)
            return {"success": True, "message_id": msg_id}

        if msg_type == MessageType.GET_ALL_USERS:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}
            users = self.db.get_all_users()
            online_ids = self._get_online_user_ids()
            for u in users:
                u["is_online"] = u["id"] in online_ids
            return {"success": True, "users": users}

        elif msg_type == MessageType.CREATE_USER:
            if not is_super_admin:
                return {"success": False, "error": "Permission denied"}

            username = msg_data.get("username")
            password = msg_data.get("password")
            new_role = msg_data.get("role", "employee")

            if not username or not password:
                return {"success": False, "error": "Bad request"}

            try:
                new_id = self.db.create_user(
                    username, hash_password(password), new_role
                )
                self.db.add_audit_entry(
                    actor_id=user_id,
                    actor_username=actor_username,
                    action="user.create",
                    target_type="user",
                    target_id=new_id,
                    details=f"username={username}, role={new_role}",
                )
                return {"success": True, "user_id": new_id}
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif msg_type == MessageType.UPDATE_USER:
            if not is_super_admin:
                return {"success": False, "error": "Permission denied"}

            target_id = msg_data.get("user_id")
            new_role = msg_data.get("role")
            if not target_id or not new_role:
                return {"success": False, "error": "Bad request"}

            self.db.update_user_role(target_id, new_role)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="user.change_role",
                target_type="user",
                target_id=target_id,
                details=f"new_role={new_role}",
            )
            return {"success": True}

        elif msg_type == MessageType.BLOCK_USER:
            if not is_super_admin:
                return {"success": False, "error": "Permission denied"}

            target_id = msg_data.get("user_id")
            if not target_id:
                return {"success": False, "error": "Bad request"}

            self.db.block_user(target_id)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="user.block",
                target_type="user",
                target_id=target_id,
                details="",
            )
            return {"success": True}

        elif msg_type == MessageType.UNBLOCK_USER:
            if not is_super_admin:
                return {"success": False, "error": "Permission denied"}

            target_id = msg_data.get("user_id")
            if not target_id:
                return {"success": False, "error": "Bad request"}

            self.db.unblock_user(target_id)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="user.unblock",
                target_type="user",
                target_id=target_id,
                details="",
            )
            return {"success": True}

        elif msg_type == MessageType.DELETE_USER:
            if not is_super_admin:
                return {"success": False, "error": "Permission denied"}

            target_id = msg_data.get("user_id")
            if not target_id:
                return {"success": False, "error": "Bad request"}

            self.db.delete_user(target_id)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="user.delete",
                target_type="user",
                target_id=target_id,
                details="",
            )
            return {"success": True}

        if msg_type == MessageType.ADMIN_GET_ALL_CHATS:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}
            chats = self.db.admin_get_all_chats()
            return {"success": True, "chats": chats}

        elif msg_type == MessageType.ADMIN_GET_CHAT_INFO:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            chat_id = msg_data.get("chat_id")
            if not chat_id:
                return {"success": False, "error": "Bad request"}

            chat = self.db.admin_get_chat_info(chat_id)
            if not chat:
                return {"success": False, "error": "Chat not found"}

            return {"success": True, "chat": chat}

        elif msg_type == MessageType.ADMIN_CREATE_CHAT:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            name = msg_data.get("name")
            members = msg_data.get("members", [])
            if not name:
                return {"success": False, "error": "Bad request"}

            chat_id = self.db.admin_create_chat(name, user_id, members)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="chat.create",
                target_type="chat",
                target_id=chat_id,
                details=f"name={name}, members={members}",
            )
            return {"success": True, "chat_id": chat_id}

        elif msg_type == MessageType.ADMIN_UPDATE_CHAT:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            chat_id = msg_data.get("chat_id")
            name = msg_data.get("name")
            members = msg_data.get("members", [])
            if not chat_id or not name:
                return {"success": False, "error": "Bad request"}

            self.db.admin_update_chat(chat_id, name, members)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="chat.update",
                target_type="chat",
                target_id=chat_id,
                details=f"name={name}, members={members}",
            )
            return {"success": True}

        elif msg_type == MessageType.ADMIN_ARCHIVE_CHAT:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            chat_id = msg_data.get("chat_id")
            if not chat_id:
                return {"success": False, "error": "Bad request"}

            self.db.admin_set_chat_archived(chat_id, True)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="chat.archive",
                target_type="chat",
                target_id=chat_id,
                details="",
            )
            return {"success": True}

        elif msg_type == MessageType.ADMIN_UNARCHIVE_CHAT:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            chat_id = msg_data.get("chat_id")
            if not chat_id:
                return {"success": False, "error": "Bad request"}

            self.db.admin_set_chat_archived(chat_id, False)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="chat.unarchive",
                target_type="chat",
                target_id=chat_id,
                details="",
            )
            return {"success": True}

        elif msg_type == MessageType.ADMIN_DELETE_CHAT:
            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            chat_id = msg_data.get("chat_id")
            if not chat_id:
                return {"success": False, "error": "Bad request"}

            self.db.admin_delete_chat(chat_id)
            self.db.add_audit_entry(
                actor_id=user_id,
                actor_username=actor_username,
                action="chat.delete",
                target_type="chat",
                target_id=chat_id,
                details="",
            )
            return {"success": True}

        if msg_type == MessageType.PING:

            if not msg_data.get("audit"):
                return {"success": True, "message": "pong"}

            if not (is_super_admin or is_dept_manager):
                return {"success": False, "error": "Permission denied"}

            limit = msg_data.get("limit", 200)
            entries = self.db.get_audit_entries(limit=limit)
            return {"success": True, "entries": entries}

        return {"success": False, "error": "Unknown message type"}


if __name__ == "__main__":
    server = MessengerServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
