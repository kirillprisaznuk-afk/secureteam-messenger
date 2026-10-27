import json
import socket
import struct
import threading

import pytest

from shared.constants import MAX_FRAME_SIZE
from shared.protocol import MessageType as T
from shared.protocol import Protocol, ProtocolError


@pytest.mark.parametrize(
    "raw",
    [
        b"{",
        b"[]",
        b"null",
        b"{}",
        b"\xff",
        b'{"type":"UNKNOWN","data":{}}',
        b'{"type":"PING","data":[]}',
        b'{"type":"PING","data":{},"extra":1}',
        b'{"type":"PING","type":"LOGIN","data":{}}',
        b'{"type":"PING","data":{"value":NaN}}',
        b'{"type":4,"data":{}}',
    ],
)
def test_invalid_envelopes(raw):
    with pytest.raises(ProtocolError):
        Protocol.parse_message(raw)


def test_fragmentation_and_coalescing():
    left, right = socket.socketpair()
    frame = Protocol.create_message(T.PING, {"unicode": "Hello 🌍"})

    def send():
        for byte in frame:
            left.sendall(bytes([byte]))
        left.sendall(frame + frame)
        left.shutdown(socket.SHUT_WR)

    thread = threading.Thread(target=send)
    thread.start()
    try:
        for _ in range(3):
            kind, data = Protocol.parse_message(Protocol.read_message(right))
            assert kind == T.PING and data["unicode"] == "Hello 🌍"
        assert Protocol.read_message(right) is None
    finally:
        thread.join(2)
        left.close()
        right.close()


@pytest.mark.parametrize("length", [0, MAX_FRAME_SIZE + 1, 2**32 - 1])
def test_oversized_header_rejected_before_body(length):
    left, right = socket.socketpair()
    try:
        left.sendall(struct.pack("!I", length))
        with pytest.raises(ProtocolError):
            Protocol.read_message(right)
    finally:
        left.close()
        right.close()


def test_truncated_frame():
    left, right = socket.socketpair()
    try:
        left.sendall(struct.pack("!I", 10) + b"{}")
        left.shutdown(socket.SHUT_WR)
        with pytest.raises(ProtocolError, match="Truncated"):
            Protocol.read_message(right)
    finally:
        left.close()
        right.close()


def test_frame_deadline(monkeypatch):
    import shared.protocol as protocol

    monkeypatch.setattr(protocol, "REQUEST_TIMEOUT", 0.02)
    left, right = socket.socketpair()
    try:
        left.sendall(b"\x00")
        with pytest.raises(TimeoutError):
            Protocol.read_message(right)
    finally:
        left.close()
        right.close()


def test_malformed_connection_does_not_kill_server(server, client_factory):
    for body in [b"{", json.dumps({"type": "PING", "data": []}).encode()]:
        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as conn:
            conn.sendall(struct.pack("!I", len(body)) + body)
            _, response = Protocol.parse_message(Protocol.read_message(conn))
            assert response["code"] == "INVALID_FRAME"
            assert conn.recv(1) == b""
    assert client_factory("alice").get_chat_list()["success"]


def test_unknown_type_and_oversized_response():
    with pytest.raises(ProtocolError):
        Protocol.create_message(T.PING, {"text": "x" * MAX_FRAME_SIZE})


def test_extremely_large_json_integer_is_protocol_error():
    with pytest.raises(ProtocolError):
        Protocol.parse_message(b'{"type":"PING","data":{"n":' + b"1" * 5000 + b"}}")
