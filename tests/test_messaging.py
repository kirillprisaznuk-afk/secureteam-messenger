import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from client.network import NetworkClient
from server.database import Database
from shared.protocol import MessageType as T
from tests.conftest import PASSWORD


def test_transaction_rolls_back_chat_and_members(database):
    count = len(database.admin_get_all_chats())
    with pytest.raises(sqlite3.IntegrityError):
        database.admin_create_chat("Rollback", 1, [2, 999999])
    assert len(database.admin_get_all_chats()) == count
    cid = database.admin_create_chat("Original", 1, [2])
    with pytest.raises(sqlite3.IntegrityError):
        database.admin_update_chat(cid, "Must rollback", [999999])
    chat = database.admin_get_chat_info(cid)
    assert chat["name"] == "Original" and chat["members"] == [1, 2]


def test_delete_cascades_and_preserves_history_references(client_factory, database):
    owner = client_factory("owner")
    cid = owner.admin_create_chat("Temporary", [2])["chat_id"]
    alice = client_factory("alice")
    assert alice.send_text_message(cid, "history")["success"]
    assert owner.delete_user(2)["code"] == "CONFLICT"
    assert owner.admin_delete_chat(cid)["success"]
    assert not database.get_chat_messages(cid)
    assert not database.get_chat_members(cid)
    assert owner.delete_user(2)["success"]


def test_audit_failure_rolls_back_mutation(client_factory, server, monkeypatch):
    owner = client_factory("owner")

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated unavailable audit storage")

    monkeypatch.setattr(server.db, "add_audit_entry", fail)
    response = owner.admin_create_chat("Should not exist", [])
    assert response["code"] == "DATABASE_ERROR"
    assert not server.db.admin_get_all_chats()


def test_concurrent_clients_order_and_persistence(client_factory, database):
    owner = client_factory("owner")
    cid = owner.admin_create_chat("Concurrent room", [2, 3, 4, 5])["chat_id"]
    clients = [client_factory(name) for name in ["alice", "bob", "outsider", "manager"]]

    def send(index):
        return [clients[index].send_text_message(cid, f"{index}:{n}") for n in range(5)]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(send, range(4)))
    assert all(response["success"] for batch in results for response in batch)
    messages = owner.get_chat_history(cid)["messages"]
    assert len(messages) == 20
    assert [m["id"] for m in messages] == sorted({m["id"] for m in messages})
    for i, name in enumerate(["alice", "bob", "outsider", "manager"]):
        assert [m["content"] for m in messages if m["sender"] == name] == [
            f"{i}:{n}" for n in range(5)
        ]
    assert len(Database(database.path).get_chat_messages(cid)) == 20


def test_restart_and_reconnect_preserve_history(server_factory, database):
    server = server_factory()
    first = NetworkClient(port=server.port)
    try:
        assert first.connect() and first.login("alice", PASSWORD)["success"]
        cid = first.create_chat("Persistent")["chat_id"]
        assert first.send_text_message(cid, "survives restart")["success"]
        first.disconnect()
        server.stop()
        restarted = server_factory()
        second = NetworkClient(port=restarted.port)
        try:
            assert second.connect()
            assert not second.login("alice", "incorrect")["success"]
            assert second.login("alice", PASSWORD)["success"]
            assert second.get_chat_history(cid)["messages"][0]["content"] == "survives restart"
        finally:
            second.disconnect()
    finally:
        first.disconnect()


def test_history_pagination(client_factory, database):
    alice = client_factory("alice")
    cid = alice.create_chat("Paged")["chat_id"]
    for n in range(45):
        database.add_message(cid, 2, f"message {n}")
    pages, before = [], None
    while True:
        response = alice.get_chat_history(cid, before)
        assert response["success"]
        pages = response["messages"] + pages
        before = response["next_before_id"]
        if before is None:
            break
    assert [row["content"] for row in pages] == [f"message {n}" for n in range(45)]


@pytest.mark.parametrize(
    "data",
    [
        {"chat_id": True, "content": "bad"},
        {"chat_id": "1", "content": "bad"},
        {"chat_id": 1, "content": []},
        {"chat_id": 1, "content": ""},
        {"chat_id": 1, "content": "x" * 10001},
        {"chat_id": 1, "content": "\x00"},
    ],
)
def test_invalid_message_data(client_factory, data):
    client = client_factory("alice")
    client.create_chat("Validation")
    response = client.send_message(T.TEXT_MESSAGE, data)
    assert response["code"] == "BAD_REQUEST"


def test_session_expiry_and_disconnect(server_factory):
    import time

    server = server_factory(session_timeout=0.02)
    client = NetworkClient(port=server.port)
    try:
        assert client.connect() and client.login("alice", PASSWORD)["success"]
        time.sleep(0.04)
        assert client.get_chat_list()["code"] == "SESSION_EXPIRED"
        assert not client.connected and client.socket is None
    finally:
        client.disconnect()


def test_server_unavailable(tmp_path):
    import socket

    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        client = NetworkClient(port=port, timeout=0.05)
        assert not client.connect()
        assert client.socket is None and not client.connected


def test_remote_plaintext_listener_rejected(database):
    from server.server import MessengerServer

    with pytest.raises(ValueError, match="require TLS"):
        MessengerServer("0.0.0.0", database_path=database.path)


def test_large_unicode_history_pages_remain_bounded(client_factory, database):
    from shared.constants import MAX_FRAME_SIZE
    from shared.protocol import Protocol

    client = client_factory("alice")
    cid = client.create_chat("Unicode")["chat_id"]
    for _ in range(20):
        database.add_message(cid, 2, "🌍" * 10000)
    response = client.get_chat_history(cid)
    assert response["success"] and response["has_more"]
    assert 0 < len(response["messages"]) < 20
    assert len(Protocol.create_message(T.ACK, response)) <= MAX_FRAME_SIZE + 4
    previous = client.get_chat_history(cid, response["next_before_id"])
    assert previous["messages"][-1]["id"] < response["messages"][0]["id"]


def test_idle_connections_expire(server_factory):
    import socket

    server = server_factory(idle_timeout=0.02)
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as conn:
        assert conn.recv(1) == b""


def test_request_rate_limit(client_factory, monkeypatch):
    import server.config as config

    client = client_factory("alice")
    monkeypatch.setattr(config, "MAX_REQUESTS_PER_SECOND", 2)
    assert client.get_chat_list()["success"]
    assert client.send_message(T.PING, {})["code"] == "RATE_LIMITED"


def test_connection_limit_covers_unauthenticated_sockets(server_factory):
    import socket
    import time

    server = server_factory(max_connections=1)
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as first:
        deadline = time.monotonic() + 2
        while not server.connections and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(server.connections) == 1
        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as second:
            assert second.recv(1) == b""
        assert first.fileno() != -1
        assert len(server.connections) == 1


def test_disconnect_during_connect_does_not_resurrect_socket(monkeypatch):
    import socket
    import threading

    left, right = socket.socketpair()
    entered, proceed = threading.Event(), threading.Event()

    def delayed(*args, **kwargs):
        entered.set()
        assert proceed.wait(2)
        return left

    monkeypatch.setattr(socket, "create_connection", delayed)
    client = NetworkClient()
    results = []
    thread = threading.Thread(target=lambda: results.append(client.connect()))
    try:
        thread.start()
        assert entered.wait(2)
        client.disconnect()
        proceed.set()
        thread.join(2)
        assert results == [False]
        assert not client.connected and client.socket is None
        assert left.fileno() == -1
    finally:
        proceed.set()
        thread.join(2)
        left.close()
        right.close()
