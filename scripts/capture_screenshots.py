"""Capture real Qt widgets backed by a running TCP server and synthetic accounts.

Run from the repository: python -m scripts.capture_screenshots
Offscreen widget captures are authentic application renders, not desktop mockups.
"""

import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from client.controller import _TASKS, worker_pool
from client.gui.admin.admin_window import AdminWindow
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow
from client.network import NetworkClient
from server.auth import hash_password
from server.database import Database
from server.server import MessengerServer


def wait_for(condition):
    deadline = time.monotonic() + 8
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError("Application did not reach expected screenshot state")
        QTest.qWait(10)


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    output = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="secureteam-screenshots-") as directory:
        password = secrets.token_urlsafe(24)
        db = Database(str(Path(directory) / "demo.db"))
        db.create_user("demo.owner", hash_password(password), "owner")
        server = MessengerServer(port=0, database_path=db.path)
        thread = threading.Thread(target=server.start)
        thread.start()
        assert server.ready.wait(5)
        clients, windows = [], []
        try:
            owner = NetworkClient(port=server.port)
            clients.append(owner)
            assert owner.connect() and owner.login("demo.owner", password)["success"]
            alex_id = owner.create_user("alex", password, "employee")["user_id"]
            sam_id = owner.create_user("sam", password, "employee")["user_id"]
            room = owner.admin_create_chat("Release planning", [alex_id, sam_id])["chat_id"]
            sam = NetworkClient(port=server.port)
            clients.append(sam)
            assert sam.connect() and sam.login("sam", password)["success"]
            assert sam.send_text_message(room, "The desktop build is ready for review.")["success"]
            alex = NetworkClient(port=server.port)
            clients.append(alex)
            login = LoginWindow(alex)
            windows.append(login)
            login.show()
            QTest.qWait(100)
            assert login.grab().save(str(output / "login.png"))
            login.username_edit.setText("alex")
            login.password_edit.setText(password)
            login.try_login()
            wait_for(lambda: login.result() == login.Accepted)
            messenger = MainWindow(alex, login.user_info)
            windows.append(messenger)
            messenger.show()
            wait_for(lambda: messenger.chats_list.count() == 1)
            messenger.chats_list.setCurrentRow(0)
            wait_for(lambda: "desktop build" in messenger.messages_view.toPlainText())
            messenger.message_edit.setText(
                "Thanks, Sam. Authentication and persistence checks passed."
            )
            messenger.send_message()
            wait_for(lambda: messenger.message_edit.text() == "")
            assert sam.get_chat_history(room)["messages"][-1]["sender"] == "alex"
            assert sam.send_text_message(
                room, "Great. I will review the conversation permissions next."
            )["success"]
            messenger.auto_refresh()
            wait_for(lambda: "permissions next" in messenger.messages_view.toPlainText())
            messenger.message_edit.setText("Ready for the final walkthrough.")
            QTest.qWait(100)
            assert messenger.grab().save(str(output / "conversation.png"))
            admin = AdminWindow(owner, "owner")
            windows.append(admin)
            admin.show()
            wait_for(lambda: admin.users_tab.table.rowCount() == 3)
            QTest.qWait(100)
            assert admin.grab().save(str(output / "administration.png"))
            print("Captured login, conversation and administration from live Qt widgets.")
        finally:
            for window in windows:
                window.close()
            for client in clients:
                client.disconnect()
            worker_pool().waitForDone(12000)
            wait_for(lambda: not _TASKS)
            server.stop()
            thread.join(5)
            assert not thread.is_alive()


if __name__ == "__main__":
    main()
