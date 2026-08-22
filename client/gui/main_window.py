from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QPushButton, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, QTimer

from client.gui.admin.admin_window import AdminWindow


class MainWindow(QMainWindow):
    def __init__(self, network_client, user_info):
        super().__init__()
        self.network = network_client
        self.user_info = user_info
        self.role = self.user_info.get("role", "guest")
        self.admin_window = None

        self.current_chat_id = None
        self.chat_refresh_timer: QTimer | None = None

        self.init_ui()
        self.apply_dark_theme()
        self.init_timers()
        self.load_chats()  

    def init_ui(self):
        username = self.user_info.get("username", "User")
        self.setWindowTitle(f"Corporate Messenger - {username}")
        self.resize(1000, 650)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_bar = QHBoxLayout()
        self.status_label = QLabel(f"Logged in as: {username}")
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()

        self.admin_btn = QPushButton("Admin Console")
        self.admin_btn.clicked.connect(self.open_admin_console)
        if self.role in ("owner", "org_admin", "department_manager"):
            top_bar.addWidget(self.admin_btn)
        else:
            self.admin_btn.hide()

        layout.addLayout(top_bar)

        center_layout = QHBoxLayout()
        center_layout.setSpacing(8)

        chats_layout = QVBoxLayout()
        chats_label = QLabel("Chats")
        chats_layout.addWidget(chats_label)

        self.chats_list = QListWidget()
        self.chats_list.itemSelectionChanged.connect(self.on_chat_selected)
        self.chats_list.setMinimumWidth(220)
        chats_layout.addWidget(self.chats_list, 1)

        center_layout.addLayout(chats_layout, 1)

        messages_layout = QVBoxLayout()
        messages_label = QLabel("Messages")
        messages_layout.addWidget(messages_label)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        messages_layout.addWidget(self.messages_view, 1)

        center_layout.addLayout(messages_layout, 3)

        layout.addLayout(center_layout, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.clicked.connect(self.create_chat_dialog)
        if self.role in ("owner", "org_admin", "department_manager"):
            bottom_layout.addWidget(self.new_chat_btn)
        else:
            self.new_chat_btn.hide()

        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Type a message...")
        self.message_edit.returnPressed.connect(self.send_message)
        bottom_layout.addWidget(self.message_edit, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        bottom_layout.addWidget(self.send_btn)

        layout.addLayout(bottom_layout)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Connected")

    def apply_dark_theme(self):
        dark_stylesheet = """
        QMainWindow {
            background-color: #1e1f22;
        }
        QWidget {
            background-color: #1e1f22;
            color: #f0f0f0;
            font-family: Segoe UI, Arial;
            font-size: 10pt;
        }
        QLabel {
            color: #c8c8c8;
        }
        QListWidget {
            background-color: #232428;
            border: 1px solid #33363d;
        }
        QTextEdit {
            background-color: #232428;
            border: 1px solid #33363d;
        }
        QLineEdit {
            background-color: #232428;
            border: 1px solid #33363d;
            padding: 4px;
        }
        QPushButton {
            background-color: #2b7cff;
            color: white;
            border-radius: 4px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #3c8dff;
        }
        QPushButton:pressed {
            background-color: #2464d6;
        }
        QPushButton#danger {
            background-color: #d64545;
        }
        QPushButton#danger:hover {
            background-color: #e05555;
        }
        QScrollBar:vertical, QScrollBar:horizontal {
            background: #1e1f22;
        }
        """
        self.setStyleSheet(dark_stylesheet)


    def init_timers(self):
        self.chat_refresh_timer = QTimer(self)
        self.chat_refresh_timer.setInterval(3000)
        self.chat_refresh_timer.timeout.connect(self.auto_refresh)
        self.chat_refresh_timer.start()

    def auto_refresh(self):
        self.load_chats(silent=True)
        if self.current_chat_id:
            self.load_chat_history(self.current_chat_id, silent=True)


    def load_chats(self, silent: bool = False):
        resp = self.network.get_chat_list()
        if not resp.get("success"):
            if not silent:
                QMessageBox.critical(
                    self, "Error", resp.get("error", "Failed to load chats")
                )
            return

        chats = resp.get("chats", [])
        prev_chat_id = self.current_chat_id

        self.chats_list.blockSignals(True)
        self.chats_list.clear()
        for chat in chats:
            item = QListWidgetItem(chat["name"])
            item.setData(Qt.UserRole, chat["id"])
            self.chats_list.addItem(item)
            if prev_chat_id is not None and chat["id"] == prev_chat_id:
                item.setSelected(True)
        self.chats_list.blockSignals(False)

    def on_chat_selected(self):
        item = self.chats_list.currentItem()
        if not item:
            self.current_chat_id = None
            self.messages_view.clear()
            return
        chat_id = item.data(Qt.UserRole)
        self.current_chat_id = chat_id
        self.load_chat_history(chat_id)

    def load_chat_history(self, chat_id: int, silent: bool = False):
        resp = self.network.get_chat_history(chat_id)
        if not resp.get("success"):
            if not silent:
                QMessageBox.critical(
                    self,
                    "Error",
                    resp.get("error", "Failed to load messages"),
                )
            return

        self.messages_view.clear()
        for msg in resp.get("messages", []):
            line = f'[{msg["created_at"]}] {msg["sender"]}: {msg["content"]}'
            self.messages_view.append(line)

    def create_chat_dialog(self):
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "New chat", "Chat name:")
        if not ok or not name.strip():
            return
        resp = self.network.create_chat(name.strip())
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Create chat failed"),
            )
            return
        self.load_chats()


    def send_message(self):
        if not self.current_chat_id:
            return
        text = self.message_edit.text().strip()
        if not text:
            return

        resp = self.network.send_text_message(self.current_chat_id, text)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Send failed"),
            )
            return

        self.message_edit.clear()
        self.load_chat_history(self.current_chat_id)


    def open_admin_console(self):
        if self.role not in ("owner", "org_admin", "department_manager"):
            return
        if self.admin_window is None:
            self.admin_window = AdminWindow(self.network, self.role)
        self.admin_window.show()
        self.admin_window.raise_()
        self.admin_window.activateWindow()
