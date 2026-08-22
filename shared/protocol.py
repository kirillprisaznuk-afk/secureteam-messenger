from enum import Enum, auto
import json
import struct


class MessageType(Enum):

    LOGIN            = auto()
    LOGOUT           = auto()

    TEXT_MESSAGE     = auto()
    GET_CHAT_HISTORY = auto()
    GET_CHAT_LIST    = auto()
    CREATE_CHAT      = auto()
    FILE_TRANSFER    = auto()

    CREATE_USER      = auto()
    GET_ALL_USERS    = auto()
    UPDATE_USER      = auto()
    BLOCK_USER       = auto()
    UNBLOCK_USER     = auto()
    DELETE_USER      = auto()

    ADMIN_GET_ALL_CHATS   = auto()
    ADMIN_GET_CHAT_INFO   = auto()
    ADMIN_CREATE_CHAT     = auto()
    ADMIN_UPDATE_CHAT     = auto()
    ADMIN_ARCHIVE_CHAT    = auto()
    ADMIN_UNARCHIVE_CHAT  = auto()
    ADMIN_DELETE_CHAT     = auto()

    PING             = auto()
    ACK              = auto()


class Protocol:


    HEADER_SIZE = 4

    @staticmethod
    def create_message(msg_type: MessageType, data: dict) -> bytes:
        payload = {
            "type": msg_type.name,
            "data": data or {},
        }
        raw = json.dumps(payload).encode("utf-8")
        return struct.pack("!I", len(raw)) + raw

    @staticmethod
    def read_message(sock) -> bytes | None:
        header = Protocol._read_exact(sock, Protocol.HEADER_SIZE)
        if not header:
            return None
        (length,) = struct.unpack("!I", header)
        if length <= 0:
            return None
        return Protocol._read_exact(sock, length)
        
    @staticmethod
    def parse_message(raw: bytes):
        payload = json.loads(raw.decode("utf-8"))
        type_name = payload.get("type")
        data = payload.get("data", {})
        msg_type = MessageType[type_name]
        return msg_type, data

    @staticmethod
    def _read_exact(sock, n: int) -> bytes | None:
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
