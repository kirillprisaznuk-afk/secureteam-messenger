"""Capture real Qt widgets backed by a running TCP server and synthetic accounts.

Run from the repository: python -m scripts.capture_screenshots
Offscreen widget captures are authentic application renders, not desktop mockups.
Use --output-dir to capture visual checks without replacing the published images.
"""

import argparse
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault("QT_FONT_DPI", "96")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from client.controller import _TASKS, worker_pool
from client.gui.admin.admin_window import AdminWindow
from client.gui.admin.chats_tab import MembersDialog
from client.gui.admin.users_tab import UserEditDialog
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow
from client.gui.styles import apply_application_theme, configure_high_dpi
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
    configure_high_dpi()
    app = QApplication([])
    apply_application_theme(app)
    app.setQuitOnLastWindowClosed(False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "screenshots",
    )
    parser.add_argument(
        "--check-layouts", action="store_true", help="Also capture minimum-size layouts"
    )
    args = parser.parse_args()
    output = args.output_dir
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
            owner.admin_create_chat("Engineering notes", [alex_id, sam_id])
            archived = owner.admin_create_chat("Previous release", [alex_id, sam_id])["chat_id"]
            assert owner.admin_archive_chat(archived)["success"]
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
            wait_for(lambda: messenger.chats_list.count() == 3)
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
            admin.tab_widget.setCurrentIndex(1)
            wait_for(lambda: admin.chats_tab.chats_list.count() == 3)
            QTest.qWait(100)
            assert admin.grab().save(str(output / "chat-administration.png"))
            admin.tab_widget.setCurrentIndex(2)
            wait_for(lambda: admin.audit_tab.table.rowCount() >= 5)
            QTest.qWait(100)
            assert admin.grab().save(str(output / "audit.png"))
            user_dialog = UserEditDialog(
                "create", ["org_admin", "department_manager", "employee", "guest"], parent=admin
            )
            windows.append(user_dialog)
            user_dialog.show()
            QTest.qWait(100)
            assert user_dialog.grab().save(str(output / "user-dialog.png"))
            user_dialog.close()
            members = MembersDialog(owner, [alex_id, sam_id], parent=admin)
            windows.append(members)
            members.show()
            wait_for(lambda: members.table.rowCount() == 3)
            QTest.qWait(100)
            assert members.grab().save(str(output / "members-dialog.png"))
            if args.check_layouts:
                for name, window, controls in [
                    ("login", login, [login.username_edit, login.password_edit, login.login_btn]),
                    (
                        "conversation",
                        messenger,
                        [messenger.chats_list, messenger.message_edit, messenger.send_btn],
                    ),
                    ("administration", admin, [admin.tab_widget]),
                    ("members", members, [members.table]),
                ]:
                    window.show()
                    window.resize(window.minimumSizeHint().expandedTo(window.minimumSize()))
                    QTest.qWait(50)
                    for control in controls:
                        assert window.rect().contains(
                            control.mapTo(window, control.rect().bottomRight())
                        ), (name, control.objectName())
                    assert window.grab().save(str(output / f"{name}-compact.png"))
                print("Minimum-size control containment checks passed.")
            print(f"Captured seven live Qt views at {app.devicePixelRatio():g}x scale in {output}.")
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
