"""Bounded thread-per-connection TCP transport with connection-bound sessions."""

import ipaddress
import logging
import socket
import ssl
import threading
import time
from collections import deque

from server import config
from server.database import Database
from server.router import RequestRouter, error
from shared.constants import IDLE_TIMEOUT, REQUEST_TIMEOUT, SESSION_TIMEOUT
from shared.protocol import MessageType, Protocol, ProtocolError

log = logging.getLogger(__name__)


class MessengerServer:
    def __init__(
        self,
        host: str = config.HOST,
        port: int = config.PORT,
        database_path: str = config.DATABASE_PATH,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int = config.MAX_CONNECTIONS,
        idle_timeout: float = IDLE_TIMEOUT,
        session_timeout: float = SESSION_TIMEOUT,
    ):
        bind_address = ipaddress.ip_address(host)
        if bind_address.version != 4:
            raise ValueError("This server currently supports IPv4 listeners only")
        if ssl_context is None and not bind_address.is_loopback:
            raise ValueError("Non-loopback listeners require TLS (--cert and --key)")
        self.host, self.port = host, port
        self.ssl_context = ssl_context
        self.max_connections = max_connections
        self.idle_timeout, self.session_timeout = idle_timeout, session_timeout
        self.db = Database(database_path)
        self.server_socket: socket.socket | None = None
        self.running = False
        self.ready = threading.Event()
        self.lock = threading.RLock()
        self.clients: dict[socket.socket, int] = {}
        self.connections: set[socket.socket] = set()
        self.threads: set[threading.Thread] = set()
        self.router = RequestRouter(self.db, self._get_online_user_ids)

    def _get_online_user_ids(self) -> set[int]:
        with self.lock:
            return set(self.clients.values())

    def start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket = listener
        try:
            # Windows SO_REUSEADDR permits duplicate listeners; exclusive bind avoids that.
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, self.port))
            self.port = listener.getsockname()[1]
            listener.listen(self.max_connections)
            listener.settimeout(0.2)
            self.running = True
            self.ready.set()
            log.info(
                "Listening on %s:%d (%s)",
                self.host,
                self.port,
                "TLS" if self.ssl_context else "local plaintext TCP",
            )
            while self.running:
                try:
                    conn, address = listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
                with self.lock:
                    if not self.running or len(self.connections) >= self.max_connections:
                        conn.close()
                        continue
                    self.connections.add(conn)
                    worker = threading.Thread(
                        target=self.handle_client, args=(conn, address), name="messenger-connection"
                    )
                    self.threads.add(worker)
                    worker.start()
        finally:
            self.stop()
            self.ready.set()

    @staticmethod
    def _close(conn: socket.socket) -> None:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Already closed or disconnected.
        conn.close()

    def stop(self) -> None:
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        with self.lock:
            connections = list(self.connections)
            workers = list(self.threads)
        for conn in connections:
            self._close(conn)
        for worker in workers:
            if worker is not threading.current_thread():
                worker.join(timeout=12)
        log.info("Server stopped")

    def handle_client(self, conn: socket.socket, address) -> None:
        user_id = None
        expires_at = 0.0
        requests = deque()
        try:
            conn.settimeout(5)
            if self.ssl_context:
                raw = conn
                conn = self.ssl_context.wrap_socket(
                    conn, server_side=True, do_handshake_on_connect=False
                )
                with self.lock:
                    self.connections.discard(raw)
                    self.connections.add(conn)
                conn.do_handshake()
            conn.settimeout(self.idle_timeout)
            while self.running:
                raw = Protocol.read_message(conn)
                if raw is None:
                    break
                now = time.monotonic()
                while requests and now - requests[0] >= 1:
                    requests.popleft()
                if len(requests) >= config.MAX_REQUESTS_PER_SECOND:
                    self._reply(conn, error("RATE_LIMITED", "Too many requests"))
                    break
                requests.append(now)
                kind, data = Protocol.parse_message(raw)
                if user_id is not None and now >= expires_at:
                    self._reply(conn, error("SESSION_EXPIRED", "Session expired; sign in again"))
                    break
                response = self.router.process(kind, data, user_id, address[0])
                if kind == MessageType.LOGIN and response.get("success"):
                    user_id = response["user_id"]
                    expires_at = time.monotonic() + self.session_timeout
                    with self.lock:
                        self.clients[conn] = user_id
                if kind == MessageType.LOGOUT or response.get("code") == "NOT_AUTHENTICATED":
                    user_id = None
                    with self.lock:
                        self.clients.pop(conn, None)
                self._reply(conn, response)
        except ProtocolError:
            try:
                self._reply(conn, error("INVALID_FRAME", "Malformed protocol message"))
            except OSError:
                pass
        except (OSError, TimeoutError):
            log.debug("Connection closed or timed out")
        except Exception:
            log.exception("Connection worker failed")
        finally:
            with self.lock:
                self.clients.pop(conn, None)
                self.connections.discard(conn)
                self.threads.discard(threading.current_thread())
            self._close(conn)

    @staticmethod
    def _reply(conn: socket.socket, response: dict) -> None:
        try:
            encoded = Protocol.create_message(MessageType.ACK, response)
        except ProtocolError:
            encoded = Protocol.create_message(
                MessageType.ACK, error("RESPONSE_TOO_LARGE", "Response exceeds protocol limit")
            )
        original_timeout = conn.gettimeout()
        try:
            conn.settimeout(REQUEST_TIMEOUT)
            conn.sendall(encoded)
        finally:
            conn.settimeout(original_timeout)
