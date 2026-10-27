import hashlib
import sqlite3

import pytest

from server.auth import AuthManager, hash_password, verify_password
from shared.protocol import MessageType as T
from tests.conftest import PASSWORD


def test_argon2_random_salts_and_verification():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("$argon2id$") and first != second
    assert verify_password(first, PASSWORD)
    assert not verify_password(first, "incorrect")
    assert not verify_password("broken hash", PASSWORD)


def test_legacy_login_upgrades_without_data_loss(database):
    old = hashlib.sha256(b"legacy secret").hexdigest()
    uid = database.create_user("legacy", old, "employee")
    chat = database.create_chat("retained", uid)
    mid = database.add_message(chat, uid, "retained history")
    auth = AuthManager(database)
    assert not auth.login("legacy", "wrong", "127.0.0.1")["success"]
    assert database.get_user_by_id(uid)["password_hash"] == old
    assert auth.login("legacy", "legacy secret", "127.0.0.1")["success"]
    assert database.get_user_by_id(uid)["password_hash"].startswith("$argon2id$")
    assert database.get_chat_messages(chat)[0]["id"] == mid


def test_admin_registration_and_login(client_factory):
    owner = client_factory("owner")
    response = owner.create_user("new.account", PASSWORD, "employee")
    assert response["success"]
    user = client_factory()
    assert not user.login("new.account", "wrong")["success"]
    assert user.login("new.account", PASSWORD)["success"]
    assert not owner.create_user("new.account", PASSWORD, "employee")["success"]
    assert owner.get_audit_entries()["entries"][0]["action"] == "user.create"


@pytest.mark.parametrize(
    "username,password,role",
    [
        ("ab", PASSWORD, "employee"),
        ("bad space", PASSWORD, "employee"),
        ("valid", "short", "employee"),
        ("valid", PASSWORD, "root"),
        ([], PASSWORD, "employee"),
        ("valid", None, "employee"),
    ],
)
def test_invalid_account_input(client_factory, username, password, role):
    client = client_factory("owner")
    response = client.create_user(username, password, role)
    assert not response["success"] and response["code"] == "BAD_REQUEST"


def test_login_throttling_and_sql_injection(client_factory):
    client = client_factory()
    for _ in range(5):
        response = client.login("' OR 1=1 --", "anything")
        assert response["code"] == "INVALID_CREDENTIALS"
    assert client.login("owner", PASSWORD)["code"] == "RATE_LIMITED"


def test_duplicate_username_constraint(database, password_hash):
    with pytest.raises(sqlite3.IntegrityError):
        database.create_user("alice", password_hash, "employee")


def test_no_default_account(tmp_path):
    from server.database import Database

    assert Database(str(tmp_path / "empty.db")).user_count() == 0


def test_logout_requires_new_authentication(client_factory):
    user = client_factory("alice")
    assert user.logout()["success"]
    assert user.get_chat_list()["code"] == "NOT_AUTHENTICATED"
    assert user.login("alice", PASSWORD)["success"]
    assert (
        user.send_message(T.LOGIN, {"username": "owner", "password": PASSWORD})["code"]
        == "ALREADY_AUTHENTICATED"
    )


def test_bootstrap_and_password_recovery_are_explicit(tmp_path, monkeypatch):
    import sys

    import run_server
    from server.database import Database

    path = str(tmp_path / "bootstrap.db")

    def invoke(*options):
        monkeypatch.setattr(sys, "argv", ["run_server.py", "--database", path, *options])
        return run_server.main()

    monkeypatch.setattr("builtins.input", lambda _: "local.owner")
    monkeypatch.setattr("getpass.getpass", lambda _: PASSWORD)
    assert invoke("--init-admin") == 0
    db = Database(path)
    assert db.user_count() == 1
    assert invoke("--init-admin") == 1
    assert db.user_count() == 1
    cid = db.create_chat("Retained", 1)
    db.add_message(cid, 1, "retained")
    replacement = "replacement test password"
    monkeypatch.setattr("getpass.getpass", lambda _: replacement)
    assert invoke("--reset-password", "local.owner") == 0
    assert verify_password(db.get_user_by_id(1)["password_hash"], replacement)
    assert db.get_chat_messages(cid)[0]["content"] == "retained"
