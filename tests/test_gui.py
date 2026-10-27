import threading
import time

from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtWidgets import QDialog

from client.controller import worker_pool
from client.gui.admin.admin_window import AdminWindow
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow
from client.network import NetworkClient
from tests.conftest import PASSWORD


def wait_idle(qtbot):
    from client.controller import _TASKS

    qtbot.waitUntil(lambda: not _TASKS, timeout=6000)


def test_login_validation_and_invalid_credentials(qtbot, server):
    network = NetworkClient(port=server.port)
    dialog = LoginWindow(network)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.mouseClick(dialog.login_btn, Qt.LeftButton)
    assert dialog.status_label.text() == "Enter your username and password."
    dialog.username_edit.setText("alice")
    dialog.password_edit.setText("wrong password")
    qtbot.mouseClick(dialog.login_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: "Invalid credentials" in dialog.status_label.text(), timeout=5000)
    assert dialog.login_btn.isEnabled() and dialog.user_info is None
    dialog.close()
    wait_idle(qtbot)
    network.disconnect()


def test_two_gui_clients_send_receive_and_plain_text(qtbot, client_factory):
    owner = client_factory("owner")
    cid = owner.admin_create_chat("Project planning", [2, 3])["chat_id"]
    alice, bob = client_factory("alice"), client_factory("bob")
    windows = [MainWindow(net, net.user_info) for net in [alice, bob]]
    for window in windows:
        qtbot.addWidget(window)
        window.show()
        qtbot.waitUntil(lambda window=window: window.chats_list.count() == 1, timeout=5000)
        window.chats_list.setCurrentRow(0)
    wait_idle(qtbot)
    first, second = windows
    first.message_edit.setText("<b>Hello Bob</b> — safe plain text")
    qtbot.keyClick(first.message_edit, Qt.Key_Return)
    qtbot.waitUntil(lambda: first.message_edit.text() == "", timeout=5000)
    second.auto_refresh()
    qtbot.waitUntil(lambda: "<b>Hello Bob</b>" in second.messages_view.toPlainText(), timeout=5000)
    assert second.current_chat_id == cid
    assert second.conversation_label.text() == "Project planning"
    for window in windows:
        window.close()
    wait_idle(qtbot)


def test_nonblocking_login_and_gui_thread_delivery(qtbot, qapp):
    class SlowNetwork:
        ssl_context = None
        host, port, connected = "127.0.0.1", 5555, True
        user_info = None

        def login(self, username, password):
            assert QThread.currentThread() != qapp.thread()
            time.sleep(0.15)
            self.user_info = {"username": username, "user_id": 2, "role": "employee"}
            return {"success": True, **self.user_info}

        def disconnect(self):
            self.connected = False

    net = SlowNetwork()
    dialog = LoginWindow(net)
    qtbot.addWidget(dialog)
    dialog.username_edit.setText("alice")
    dialog.password_edit.setText(PASSWORD)
    ticks = []
    accepted_threads = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(threading.get_ident()))
    timer.start()
    dialog.accepted.connect(lambda: accepted_threads.append(threading.get_ident()))
    dialog.try_login()
    assert not dialog.login_btn.isEnabled()
    qtbot.waitUntil(lambda: dialog.result() == QDialog.Accepted, timeout=3000)
    timer.stop()
    assert len(ticks) >= 5
    assert accepted_threads == [threading.get_ident()]
    assert set(ticks) == {threading.get_ident()}
    wait_idle(qtbot)


def test_disconnect_disables_composer(qtbot, client_factory, server):
    net = client_factory("alice")
    net.create_chat("Room")
    window = MainWindow(net, net.user_info)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda window=window: window.chats_list.count() == 1, timeout=5000)
    window.chats_list.setCurrentRow(0)
    wait_idle(qtbot)
    assert window.send_btn.isEnabled()
    server.stop()
    window.auto_refresh()
    qtbot.waitUntil(lambda: window.reconnect_btn.isVisible(), timeout=5000)
    assert not window.send_btn.isEnabled()
    assert not window.chat_refresh_timer.isActive()
    window.close()
    wait_idle(qtbot)


def test_admin_and_members_load_asynchronously(qtbot, client_factory):
    net = client_factory("owner")
    window = AdminWindow(net, "owner")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.users_tab.table.rowCount() == 7, timeout=5000)
    wait_idle(qtbot)
    assert window.users_tab.allowed_roles() == [
        "org_admin",
        "department_manager",
        "employee",
        "guest",
    ]
    window.close()
    assert not window.users_tab.refresh_timer.isActive()
    assert not window.chats_tab.refresh_timer.isActive()
    worker_pool().waitForDone(5000)
    wait_idle(qtbot)


def test_admin_member_selection(qtbot, client_factory):
    from PyQt5.QtWidgets import QDialogButtonBox

    from client.gui.admin.chats_tab import MembersDialog

    net = client_factory("owner")
    dialog = MembersDialog(net, [2])
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(lambda: dialog.table.rowCount() == 7, timeout=5000)
    assert dialog.get_selected_members() == [2]
    dialog.table.item(2, 2).setCheckState(Qt.Checked)
    assert dialog.get_selected_members() == [2, 3]
    dialog.findChild(QDialogButtonBox).rejected.emit()
    wait_idle(qtbot)


def test_duplicate_send_action_is_coalesced(qtbot, client_factory, database):
    net = client_factory("alice")
    cid = net.create_chat("One send")["chat_id"]
    window = MainWindow(net, net.user_info)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.chats_list.count() == 1, timeout=5000)
    window.chats_list.setCurrentRow(0)
    wait_idle(qtbot)
    window.message_edit.setText("once")
    window.send_message()
    window.send_message()
    qtbot.waitUntil(lambda: window.message_edit.text() == "", timeout=5000)
    assert len(database.get_chat_messages(cid)) == 1
    window.close()
    wait_idle(qtbot)


def test_refresh_fills_a_burst_across_history_pages(qtbot, client_factory, database):
    net = client_factory("alice")
    cid = net.create_chat("Burst")["chat_id"]
    database.add_message(cid, 2, "initial")
    window = MainWindow(net, net.user_info)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.chats_list.count() == 1, timeout=5000)
    window.chats_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: "initial" in window.messages_view.toPlainText(), timeout=5000)
    for n in range(45):
        database.add_message(cid, 2, f"burst {n}")
    window.load_chat_history(cid)
    qtbot.waitUntil(lambda: len(window._history) == 46, timeout=5000)
    assert [m["content"] for m in window._history] == ["initial"] + [
        f"burst {n}" for n in range(45)
    ]
    window.close()
    wait_idle(qtbot)


def test_reconnect_reauthenticates_and_replaces_window(qtbot, client_factory):
    from PyQt5.QtWidgets import QApplication

    net = client_factory("alice")
    net.create_chat("Reconnect room")
    original = MainWindow(net, net.user_info)
    qtbot.addWidget(original)
    original.show()
    wait_idle(qtbot)
    net.disconnect()
    original.auto_refresh()
    qtbot.waitUntil(lambda: original.reconnect_btn.isVisible(), timeout=5000)

    def sign_in():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, LoginWindow)
        modal.username_edit.setText("alice")
        modal.password_edit.setText(PASSWORD)
        modal.try_login()

    QTimer.singleShot(30, sign_in)
    original.reconnect()
    replacement = original.replacement
    qtbot.addWidget(replacement)
    assert replacement.isVisible() and not original.isVisible()
    assert replacement.user_info["username"] == "alice" and net.connected
    qtbot.waitUntil(lambda: replacement.chats_list.count() == 1, timeout=5000)
    replacement.close()
    wait_idle(qtbot)
