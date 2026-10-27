"""Synchronous transport API, executed by the Qt controller outside the GUI thread."""

import logging
import socket
import ssl
import threading

import client.config as config
from shared.constants import REQUEST_TIMEOUT
from shared.protocol import MessageType, Protocol, ProtocolError

log = logging.getLogger(__name__)


class NetworkClient:
    def __init__(
        self,
        host: str = config.SERVER_HOST,
        port: int = config.SERVER_PORT,
        ssl_context: ssl.SSLContext | None = None,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.host, self.port = host, port
        self.ssl_context, self.timeout = ssl_context, timeout
        self.socket = None
        self.connected = False
        self.user_info = None
        self.lock = threading.RLock()
        self.state_lock = threading.Lock()
        self.generation = 0
        self.last_error = ""

    def connect(self) -> bool:
        with self.lock:
            self.disconnect()
            with self.state_lock:
                generation = self.generation
            raw = None
            try:
                raw = socket.create_connection((self.host, self.port), timeout=self.timeout)
                if self.ssl_context:
                    raw = self.ssl_context.wrap_socket(raw, server_hostname=self.host)
                with self.state_lock:
                    if generation != self.generation:
                        raw.close()
                        return False
                    self.socket = raw
                    self.connected = True
                self.last_error = ""
                return True
            except OSError:
                if raw:
                    raw.close()
                self.last_error = "Cannot connect. Check the server address and TLS certificate."
                log.debug("Connection failed", exc_info=True)
                return False

    def disconnect(self):
        # Closing may interrupt an in-flight worker; do not wait for its request lock.
        with self.state_lock:
            self.generation += 1
            conn, self.socket = self.socket, None
            self.connected = False
            self.user_info = None
        if conn:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()

    def send_message(self, msg_type: MessageType, data: dict) -> dict:
        with self.lock:
            conn = self.socket
            if not self.connected or conn is None:
                return {
                    "success": False,
                    "code": "DISCONNECTED",
                    "error": "Disconnected; sign in again",
                }
            try:
                conn.sendall(Protocol.create_message(msg_type, data))
                raw = Protocol.read_message(conn)
                if raw is None:
                    raise ConnectionError("Server closed the connection")
                kind, response = Protocol.parse_message(raw)
                if kind != MessageType.ACK or type(response.get("success")) is not bool:
                    raise ProtocolError("Invalid server response")
                if response.get("code") == "SESSION_EXPIRED" or (
                    response.get("code") == "NOT_AUTHENTICATED" and self.user_info
                ):
                    self.disconnect()
                return response
            except (OSError, ProtocolError):
                self.disconnect()
                # A send may have committed before the response was lost. Never retry it automatically.
                return {
                    "success": False,
                    "code": "DISCONNECTED",
                    "error": "Connection lost. A pending send may have been saved; check history after signing in.",
                }

    def logout(self) -> dict:
        response = self.send_message(MessageType.LOGOUT, {})
        self.user_info = None
        return response

    def login(self, username: str, password: str) -> dict:
        resp = self.send_message(
            MessageType.LOGIN,
            {
                "username": username,
                "password": password,
            },
        )
        if resp.get("success"):
            self.user_info = {
                "user_id": resp.get("user_id"),
                "username": resp.get("username"),
                "role": resp.get("role"),
            }
        return resp

    def send_text_message(self, chat_id: int, content: str) -> dict:
        return self.send_message(
            MessageType.TEXT_MESSAGE,
            {
                "chat_id": chat_id,
                "content": content,
            },
        )

    def get_chat_list(self) -> dict:
        return self.send_message(MessageType.GET_CHAT_LIST, {})

    def get_chat_history(self, chat_id: int, before_id: int | None = None) -> dict:
        return self.send_message(
            MessageType.GET_CHAT_HISTORY,
            {
                "chat_id": chat_id,
                **({"before_id": before_id} if before_id else {}),
            },
        )

    def create_chat(self, name: str) -> dict:
        return self.send_message(
            MessageType.CREATE_CHAT,
            {
                "name": name,
            },
        )

    def create_user(self, username: str, password: str, role: str) -> dict:
        return self.send_message(
            MessageType.CREATE_USER,
            {
                "username": username,
                "password": password,
                "role": role,
            },
        )

    def get_all_users(self) -> dict:
        return self.send_message(MessageType.GET_ALL_USERS, {})

    def update_user(self, user_id: int, role: str) -> dict:
        return self.send_message(
            MessageType.UPDATE_USER,
            {
                "user_id": user_id,
                "role": role,
            },
        )

    def block_user(self, user_id: int) -> dict:
        return self.send_message(
            MessageType.BLOCK_USER,
            {
                "user_id": user_id,
            },
        )

    def unblock_user(self, user_id: int) -> dict:
        return self.send_message(
            MessageType.UNBLOCK_USER,
            {
                "user_id": user_id,
            },
        )

    def delete_user(self, user_id: int) -> dict:
        return self.send_message(
            MessageType.DELETE_USER,
            {
                "user_id": user_id,
            },
        )

    def admin_get_all_chats(self) -> dict:
        return self.send_message(MessageType.ADMIN_GET_ALL_CHATS, {})

    def admin_get_chat_info(self, chat_id: int) -> dict:
        return self.send_message(
            MessageType.ADMIN_GET_CHAT_INFO,
            {
                "chat_id": chat_id,
            },
        )

    def admin_create_chat(self, name: str, member_ids: list[int]) -> dict:
        return self.send_message(
            MessageType.ADMIN_CREATE_CHAT,
            {
                "name": name,
                "members": member_ids,
            },
        )

    def admin_update_chat(self, chat_id: int, name: str, member_ids: list[int]) -> dict:
        return self.send_message(
            MessageType.ADMIN_UPDATE_CHAT,
            {
                "chat_id": chat_id,
                "name": name,
                "members": member_ids,
            },
        )

    def admin_archive_chat(self, chat_id: int) -> dict:
        return self.send_message(
            MessageType.ADMIN_ARCHIVE_CHAT,
            {
                "chat_id": chat_id,
            },
        )

    def admin_unarchive_chat(self, chat_id: int) -> dict:
        return self.send_message(
            MessageType.ADMIN_UNARCHIVE_CHAT,
            {
                "chat_id": chat_id,
            },
        )

    def admin_delete_chat(self, chat_id: int) -> dict:
        return self.send_message(
            MessageType.ADMIN_DELETE_CHAT,
            {
                "chat_id": chat_id,
            },
        )

    def get_audit_entries(self, limit: int = 200) -> dict:
        return self.send_message(
            MessageType.PING,
            {"audit": True, "limit": limit},
        )
