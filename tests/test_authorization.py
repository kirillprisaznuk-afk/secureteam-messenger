import pytest

from shared.protocol import MessageType as T


def test_membership_controls_read_and_send(client_factory):
    owner = client_factory("owner")
    alice = client_factory("alice")
    bob = client_factory("bob")
    outsider = client_factory("outsider")
    cid = owner.admin_create_chat("Private conversation", [2, 3])["chat_id"]
    assert alice.send_text_message(cid, "hello")["success"]
    assert bob.get_chat_history(cid)["messages"][0]["content"] == "hello"
    assert outsider.get_chat_history(cid)["code"] == "FORBIDDEN"
    assert outsider.send_text_message(cid, "injected")["code"] == "FORBIDDEN"
    assert not outsider.get_chat_list()["chats"]
    # Even an owner needs membership to read message content.
    other = alice.create_chat("Alice only")["chat_id"]
    assert owner.get_chat_history(other)["code"] == "FORBIDDEN"


@pytest.mark.parametrize(
    "kind,data",
    [
        (
            T.CREATE_USER,
            {"username": "intruder", "password": "long enough password", "role": "owner"},
        ),
        (T.GET_ALL_USERS, {}),
        (T.UPDATE_USER, {"user_id": 2, "role": "owner"}),
        (T.BLOCK_USER, {"user_id": 1}),
        (T.DELETE_USER, {"user_id": 1}),
        (T.ADMIN_GET_ALL_CHATS, {}),
        (T.PING, {"audit": True}),
    ],
)
def test_employee_cannot_invoke_admin_actions(client_factory, kind, data):
    user = client_factory("alice")
    data.update({"role": "owner", "sender_id": 1, "user_id": 1})
    assert user.send_message(kind, data)["code"] == "FORBIDDEN"


def test_no_self_modification_or_role_escalation(client_factory):
    owner = client_factory("owner")
    admin = client_factory("administrator")
    assert owner.update_user(1, "guest")["code"] == "FORBIDDEN"
    assert owner.block_user(1)["code"] == "FORBIDDEN"
    assert owner.delete_user(1)["code"] == "FORBIDDEN"
    assert admin.update_user(2, "owner")["code"] == "FORBIDDEN"
    assert admin.block_user(1)["code"] == "FORBIDDEN"
    assert admin.create_user("second.owner", "long enough password", "owner")["code"] == "FORBIDDEN"


def test_blocked_session_and_live_role_change(client_factory):
    owner = client_factory("owner")
    admin = client_factory("administrator")
    assert owner.update_user(6, "employee")["success"]
    assert admin.get_all_users()["code"] == "FORBIDDEN"
    assert owner.block_user(6)["success"]
    assert admin.get_chat_list()["code"] == "NOT_AUTHENTICATED"
    assert owner.unblock_user(6)["success"]


def test_manager_scope_and_audit(client_factory):
    owner = client_factory("owner")
    manager = client_factory("manager")
    private = owner.admin_create_chat("Other team", [2])["chat_id"]
    assert manager.admin_get_chat_info(private)["code"] == "FORBIDDEN"
    assert manager.admin_delete_chat(private)["code"] == "FORBIDDEN"
    assert manager.get_audit_entries()["code"] == "FORBIDDEN"
    own = manager.admin_create_chat("Managed conversation", [2, 3])["chat_id"]
    assert manager.admin_update_chat(own, "Renamed", [3])["success"]
    assert manager.admin_get_chat_info(own)["chat"]["members"] == [3, 5]
    assert [row["id"] for row in manager.admin_get_all_chats()["chats"]] == [own]


def test_guest_cannot_create_but_can_send_when_member(client_factory):
    owner = client_factory("owner")
    guest = client_factory("visitor")
    assert guest.create_chat("No")["code"] == "FORBIDDEN"
    cid = owner.admin_create_chat("Guest room", [7])["chat_id"]
    assert guest.send_text_message(cid, "hello")["success"]
    assert owner.admin_archive_chat(cid)["success"]
    assert guest.send_text_message(cid, "no")["code"] == "BAD_REQUEST"
    assert guest.get_chat_history(cid)["success"]


def test_removed_member_loses_access(client_factory):
    owner, alice = client_factory("owner"), client_factory("alice")
    cid = owner.admin_create_chat("Room", [2])["chat_id"]
    assert owner.admin_update_chat(cid, "Room", [])["success"]
    assert alice.get_chat_history(cid)["code"] == "FORBIDDEN"
    assert alice.send_text_message(cid, "no")["code"] == "FORBIDDEN"


def test_client_identity_never_selects_sender(client_factory):
    alice = client_factory("alice")
    cid = alice.create_chat("Room")["chat_id"]
    assert alice.send_message(
        T.TEXT_MESSAGE, {"chat_id": cid, "content": "identity", "sender_id": 1, "role": "owner"}
    )["success"]
    assert alice.get_chat_history(cid)["messages"][0]["sender"] == "alice"


def test_unauthenticated_registration_is_forbidden(client_factory):
    assert (
        client_factory().create_user("new", "long enough password", "owner")["code"]
        == "NOT_AUTHENTICATED"
    )
