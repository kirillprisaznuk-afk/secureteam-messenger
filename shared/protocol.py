"""Four-byte network-order length followed by one strict UTF-8 JSON envelope."""

import json
import socket
import struct
import time
from enum import Enum, auto

from shared.constants import MAX_FRAME_SIZE, REQUEST_TIMEOUT


class MessageType(Enum):
    LOGIN = auto()
    LOGOUT = auto()
    TEXT_MESSAGE = auto()
    GET_CHAT_HISTORY = auto()
    GET_CHAT_LIST = auto()
    CREATE_CHAT = auto()
    FILE_TRANSFER = auto()  # Reserved; unsupported by this application.
    CREATE_USER = auto()
    GET_ALL_USERS = auto()
    UPDATE_USER = auto()
    BLOCK_USER = auto()
    UNBLOCK_USER = auto()
    DELETE_USER = auto()
    ADMIN_GET_ALL_CHATS = auto()
    ADMIN_GET_CHAT_INFO = auto()
    ADMIN_CREATE_CHAT = auto()
    ADMIN_UPDATE_CHAT = auto()
    ADMIN_ARCHIVE_CHAT = auto()
    ADMIN_UNARCHIVE_CHAT = auto()
    ADMIN_DELETE_CHAT = auto()
    PING = auto()
    ACK = auto()


class ProtocolError(ValueError):
    """The current frame or envelope cannot safely be processed."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ProtocolError("Non-finite JSON number")


class Protocol:
    HEADER_SIZE = 4

    @staticmethod
    def create_message(msg_type: MessageType, data: dict) -> bytes:
        if not isinstance(msg_type, MessageType) or not isinstance(data, dict):
            raise ProtocolError("Invalid envelope")
        raw = json.dumps(
            {"type": msg_type.name, "data": data},
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if not 0 < len(raw) <= MAX_FRAME_SIZE:
            raise ProtocolError("Frame too large")
        return struct.pack("!I", len(raw)) + raw

    @staticmethod
    def read_message(sock: socket.socket) -> bytes | None:
        # Idle connections use their socket timeout. Once the first byte arrives,
        # the entire frame has a fixed deadline, defeating trickle-byte reads.
        first = sock.recv(1)
        if not first:
            return None
        deadline = time.monotonic() + REQUEST_TIMEOUT
        original_timeout = sock.gettimeout()
        try:
            header = first + Protocol._read_exact(sock, 3, deadline)
            (length,) = struct.unpack("!I", header)
            if not 0 < length <= MAX_FRAME_SIZE:
                raise ProtocolError("Invalid frame length")
            return Protocol._read_exact(sock, length, deadline)
        finally:
            sock.settimeout(original_timeout)

    @staticmethod
    def parse_message(raw: bytes) -> tuple[MessageType, dict]:
        if not 0 < len(raw) <= MAX_FRAME_SIZE:
            raise ProtocolError("Invalid frame length")
        try:
            payload = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
            if not isinstance(payload, dict) or set(payload) != {"type", "data"}:
                raise ProtocolError("Expected type and data envelope")
            if not isinstance(payload["type"], str) or not isinstance(payload["data"], dict):
                raise ProtocolError("Invalid envelope types")
            return MessageType[payload["type"]], payload["data"]
        except (UnicodeError, ValueError, KeyError, TypeError, RecursionError) as exc:
            raise ProtocolError("Invalid JSON message") from exc

    @staticmethod
    def _read_exact(sock: socket.socket, size: int, deadline: float) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Frame deadline exceeded")
            sock.settimeout(remaining)
            chunk = sock.recv(size - len(chunks))
            if not chunk:
                raise ProtocolError("Truncated frame")
            chunks.extend(chunk)
        return bytes(chunks)
