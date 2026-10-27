"""Fixtures own every socket, server thread and temporary SQLite database."""

import os
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

import pytest

from client.network import NetworkClient
from server.auth import hash_password
from server.database import Database
from server.server import MessengerServer

PASSWORD = "educational test password"


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def database(tmp_path, password_hash):
    db = Database(str(tmp_path / "test.db"))
    for username, role in [
        ("owner", "owner"),
        ("alice", "employee"),
        ("bob", "employee"),
        ("outsider", "employee"),
        ("manager", "department_manager"),
        ("administrator", "org_admin"),
        ("visitor", "guest"),
    ]:
        db.create_user(username, password_hash, role)
    return db


@pytest.fixture
def server_factory(database):
    running = []

    def start(**kwargs):
        server = MessengerServer(port=0, database_path=database.path, **kwargs)
        thread = threading.Thread(target=server.start, name="test-listener")
        thread.start()
        assert server.ready.wait(5)
        assert server.running
        running.append((server, thread))
        return server

    yield start
    for server, thread in running:
        server.stop()
        thread.join(15)
        assert not thread.is_alive()
        assert not server.threads
        assert not server.connections
        assert not server.clients


@pytest.fixture
def server(server_factory):
    return server_factory()


@pytest.fixture
def client_factory(server):
    clients = []

    def create(username=None):
        client = NetworkClient(port=server.port, timeout=3)
        assert client.connect()
        clients.append(client)
        if username:
            assert client.login(username, PASSWORD)["success"]
        return client

    yield create
    for client in clients:
        client.disconnect()
