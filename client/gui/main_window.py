"""Conversation widgets; networking is yielded to the background controller."""

from PyQt5 import sip
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from client.controller import background
from client.gui.admin.admin_window import AdminWindow
from client.gui.conversation_view import ROW_PRESENTATION, ConversationDelegate, MessageHistory
from client.gui.styles import DARK_THEME, ElidedLabel, literal_tooltip
from shared.constants import MESSAGE_MAX_LENGTH


class MainWindow(QMainWindow):
    def __init__(self, network_client, user_info):
        super().__init__()
        self.network = network_client
        self.user_info = user_info
        self.role = user_info["role"]
        self.admin_window = None
        self.current_chat_id = None
        self._history = []
        self._next_before = None
        self._archived = False
        self.setWindowTitle(f"SecureTeam Messenger · {user_info['username']}")
        self.setMinimumSize(800, 540)
        self.resize(1120, 740)
        self.setStyleSheet(DARK_THEME)
        self.init_ui()
        self.chat_refresh_timer = QTimer(self)
        self.chat_refresh_timer.setInterval(3000)
        self.chat_refresh_timer.timeout.connect(self.auto_refresh)
        self.chat_refresh_timer.start()
        self.load_chats()

    def init_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(18)
        bar = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(4)
        heading.addWidget(QLabel("SecureTeam Messenger", objectName="title"))
        self.status_label = ElidedLabel(
            f"{self.user_info['username']} · {self.role.replace('_', ' ')}"
        )
        self.status_label.setObjectName("subtitle")
        heading.addWidget(self.status_label)
        bar.addLayout(heading, 1)
        self.admin_btn = QPushButton("Administration")
        self.admin_btn.setToolTip("Manage workspace users, conversations and audit records")
        self.admin_btn.clicked.connect(self.open_admin_console)
        self.admin_btn.setVisible(self.role in {"owner", "org_admin", "department_manager"})
        bar.addWidget(self.admin_btn)
        self.reconnect_btn = QPushButton("Reconnect / sign in", objectName="primary")
        self.reconnect_btn.clicked.connect(self.reconnect)
        self.reconnect_btn.hide()
        bar.addWidget(self.reconnect_btn)
        layout.addLayout(bar)
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        sidebar = QFrame(objectName="panel")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 18, 12, 12)
        side_layout.setSpacing(12)
        side_layout.addWidget(QLabel("CONVERSATIONS", objectName="eyebrow"))
        self.chats_list = QListWidget()
        self.chats_list.setMinimumWidth(195)
        self.chats_list.setTextElideMode(Qt.ElideRight)
        self.chats_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chats_list.setItemDelegate(ConversationDelegate(self.chats_list))
        self.chats_list.setAccessibleName("Conversations")
        self.chats_list.itemSelectionChanged.connect(self.on_chat_selected)
        side_layout.addWidget(self.chats_list, 1)
        self.sidebar_hint = QLabel("Choose a conversation to view its messages.", objectName="hint")
        self.sidebar_hint.setWordWrap(True)
        side_layout.addWidget(self.sidebar_hint)
        self.new_chat_btn = QPushButton("New conversation")
        self.new_chat_btn.setVisible(self.role != "guest")
        self.new_chat_btn.clicked.connect(self.create_chat_dialog)
        side_layout.addWidget(self.new_chat_btn)
        self.splitter.addWidget(sidebar)
        conversation = QFrame(objectName="panel")
        conversation.setMinimumWidth(380)
        messages = QVBoxLayout(conversation)
        messages.setContentsMargins(0, 0, 0, 0)
        messages.setSpacing(0)
        title_bar = QVBoxLayout()
        title_bar.setContentsMargins(20, 16, 20, 14)
        title_bar.setSpacing(5)
        self.conversation_label = ElidedLabel("Select a conversation")
        self.conversation_label.setObjectName("sectionTitle")
        title_bar.addWidget(self.conversation_label)
        self.conversation_hint = QLabel(
            "Your conversation history will appear here.", objectName="hint"
        )
        self.conversation_hint.setWordWrap(True)
        title_bar.addWidget(self.conversation_hint)
        messages.addLayout(title_bar)
        self.older_btn = QPushButton("Load earlier messages")
        self.older_btn.clicked.connect(self.load_older)
        self.older_btn.hide()
        messages.addWidget(self.older_btn)
        self.messages_view = MessageHistory()
        self.messages_view.setPlaceholderText(
            "Select a conversation\n\nChoose a name on the left to read and send messages."
        )
        messages.addWidget(self.messages_view, 1)
        composer_panel = QFrame(objectName="composer")
        composer_layout = QVBoxLayout(composer_panel)
        composer_layout.setContentsMargins(16, 14, 16, 12)
        composer_layout.setSpacing(8)
        composer = QHBoxLayout()
        composer.setSpacing(10)
        self.message_edit = QLineEdit()
        self.message_edit.setMaxLength(MESSAGE_MAX_LENGTH)
        self.message_edit.setAccessibleName("Message")
        self.message_edit.setPlaceholderText("Write a message…")
        self.message_edit.returnPressed.connect(self.send_message)
        composer.addWidget(self.message_edit, 1)
        self.send_btn = QPushButton("Send", objectName="primary")
        self.send_btn.setToolTip("Send message (Enter)")
        self.send_btn.clicked.connect(self.send_message)
        composer.addWidget(self.send_btn)
        composer_layout.addLayout(composer)
        self.composer_hint = QLabel(
            "Enter to send · Select message text to copy", objectName="hint"
        )
        self.composer_hint.setWordWrap(True)
        composer_layout.addWidget(self.composer_hint)
        messages.addWidget(composer_panel)
        self.splitter.addWidget(conversation)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 800])
        layout.addWidget(self.splitter, 1)
        self.setCentralWidget(central)
        self.setTabOrder(self.chats_list, self.messages_view)
        self.setTabOrder(self.messages_view, self.message_edit)
        self.setTabOrder(self.message_edit, self.send_btn)
        self._composer_state()
        self.statusBar().setSizeGripEnabled(True)
        self.statusBar().showMessage("Connected · updates every 3 seconds")

    def _composer_state(self):
        enabled = self.current_chat_id is not None and self.network.connected and not self._archived
        self.message_edit.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if not self.network.connected:
            self.composer_hint.setText("Connection lost · sign in again to continue")
        elif self._archived:
            self.composer_hint.setText("Archived conversation · messages are read-only")
        elif self.current_chat_id is None:
            self.composer_hint.setText("Select a conversation before writing a message")
        else:
            self.composer_hint.setText("Enter to send · Select message text to copy")

    def _check(self, response, silent=False):
        if response.get("success"):
            return True
        message = response.get("error", "Request failed")
        self.statusBar().showMessage(message)
        if not self.network.connected:
            self.reconnect_btn.show()
            self.chat_refresh_timer.stop()
            self._composer_state()
            if self.admin_window:
                self.admin_window.close()
        elif not silent:
            QMessageBox.warning(self, "Request failed", message)
        return False

    def auto_refresh(self):
        self.load_chats(silent=True)
        if self.current_chat_id:
            self.load_chat_history(self.current_chat_id, silent=True)

    @background
    def load_chats(self, silent=False):
        response = yield self.network.get_chat_list
        if not self._check(response, silent):
            return
        previous = self.current_chat_id
        self.chats_list.blockSignals(True)
        self.chats_list.clear()
        selected = None
        for chat in response["chats"]:
            item = QListWidgetItem(chat["name"] + (" · archived" if chat["archived"] else ""))
            item.setData(Qt.UserRole, chat)
            item.setData(
                ROW_PRESENTATION,
                {
                    "title": chat["name"],
                    "subtitle": "Archived · read only" if chat["archived"] else "Team conversation",
                },
            )
            item.setToolTip(
                literal_tooltip(chat["name"] + (" · archived" if chat["archived"] else ""))
            )
            self.chats_list.addItem(item)
            if chat["id"] == previous:
                selected = item
                self._archived = chat["archived"]
        self.chats_list.setCurrentItem(selected)
        self.chats_list.blockSignals(False)
        if selected:
            chat = selected.data(Qt.UserRole)
            self.conversation_label.setText(
                chat["name"] + (" · read-only archive" if chat["archived"] else "")
            )
            self.conversation_hint.setText(
                "Read-only archive" if chat["archived"] else "Messages are saved to your workspace"
            )
        if selected is None and previous:
            self.on_chat_selected()
        if not response["chats"]:
            self.conversation_label.setText(
                "No conversations yet · ask an administrator to add you"
            )
        count = len(response["chats"])
        self.sidebar_hint.setText(
            f"{count} conversation{'s' if count != 1 else ''} in your workspace"
            if count
            else "No conversations yet. An administrator can add you to one."
        )
        self._composer_state()
        transport = "TLS" if self.network.ssl_context else "unencrypted local TCP"
        self.statusBar().showMessage(f"Connected · {transport} · updates every 3 seconds")
        if response.get("truncated"):
            self.statusBar().showMessage("Showing the first 1,000 conversations")

    def on_chat_selected(self):
        item = self.chats_list.currentItem()
        self.current_chat_id = None
        self._history = []
        self._next_before = None
        self.older_btn.hide()
        self.messages_view.clear()
        if item:
            chat = item.data(Qt.UserRole)
            self.current_chat_id, self._archived = chat["id"], chat["archived"]
            self.conversation_label.setText(
                chat["name"] + (" · read-only archive" if chat["archived"] else "")
            )
            self.load_chat_history(chat["id"])
        else:
            self.conversation_label.setText("Select a conversation")
        self.conversation_hint.setText(
            "Read-only archive"
            if self._archived and item
            else "Messages are saved to your workspace"
            if item
            else "Choose a conversation from the sidebar."
        )
        self._composer_state()

    @background
    def load_chat_history(self, chat_id, silent=False):
        response = yield lambda: self.network.get_chat_history(chat_id)
        if chat_id != self.current_chat_id:
            # A selection changed while another history request was in flight.
            if self.current_chat_id:
                QTimer.singleShot(0, lambda: self.load_chat_history(self.current_chat_id))
            return
        if not self._check(response, silent):
            if response.get("code") == "FORBIDDEN":
                self.messages_view.clear()
                self._history = []
                self._archived = True
                self._composer_state()
            return
        incoming = response["messages"]
        latest_page = response
        old_latest = self._history[-1]["id"] if self._history else None
        attempts = 0
        # Fill a burst spanning several pages rather than displaying a gap
        # between cached messages and the newest page after a refresh.
        while (
            old_latest
            and incoming
            and incoming[0]["id"] > old_latest
            and response.get("next_before_id")
            and attempts < 5
        ):
            before = response["next_before_id"]
            response = yield lambda before=before: self.network.get_chat_history(chat_id, before)
            if chat_id != self.current_chat_id or not self._check(response, silent):
                return
            incoming = response["messages"] + incoming
            attempts += 1
        overlaps = old_latest is not None and incoming and incoming[0]["id"] <= old_latest
        if self._history and overlaps:
            known = {m["id"]: m for m in self._history}
            known.update({m["id"]: m for m in incoming})
            self._history = sorted(known.values(), key=lambda m: m["id"])
        else:
            self._history = latest_page["messages"]
            self._next_before = latest_page.get("next_before_id")
        self._render_history()

    def _render_history(self):
        bar = self.messages_view.verticalScrollBar()
        position = bar.value()
        at_bottom = position >= bar.maximum() - 5
        self.messages_view.render_messages(self._history, self.user_info["username"])
        bar.setValue(bar.maximum() if at_bottom else position)
        self.older_btn.setVisible(self._next_before is not None)
        if not self._history:
            self.messages_view.setPlaceholderText("No messages yet. Start the conversation.")

    @background
    def load_older(self):
        chat_id, before = self.current_chat_id, self._next_before
        if not chat_id or not before:
            return
        response = yield lambda: self.network.get_chat_history(chat_id, before)
        if chat_id != self.current_chat_id or not self._check(response):
            return
        self._history = response["messages"] + self._history
        self._next_before = response.get("next_before_id")
        self._render_history()

    @background
    def create_chat_dialog(self):
        name, ok = QInputDialog.getText(self, "New conversation", "Conversation name:")
        if not ok or not name.strip():
            return
        response = yield lambda: self.network.create_chat(name.strip())
        if self._check(response):
            self.current_chat_id = response["chat_id"]
            self.load_chats()
            self.load_chat_history(self.current_chat_id)

    @background
    def send_message(self):
        text = self.message_edit.text()
        chat_id = self.current_chat_id
        if not chat_id or not text.strip() or self._archived:
            return
        self.send_btn.setEnabled(False)
        try:
            response = yield lambda: self.network.send_text_message(chat_id, text)
            if self._check(response):
                if self.message_edit.text() == text:
                    self.message_edit.clear()
                if chat_id == self.current_chat_id:
                    self.load_chat_history(chat_id)
        finally:
            if not sip.isdeleted(self):
                self._composer_state()

    def open_admin_console(self):
        if self.role not in {"owner", "org_admin", "department_manager"}:
            return
        if self.admin_window is None:
            self.admin_window = AdminWindow(self.network, self.role, self)
        self.admin_window.show()
        self.admin_window.raise_()

    def reconnect(self):
        from client.gui.login_window import LoginWindow

        dialog = LoginWindow(self.network, self)
        if dialog.exec_() == dialog.Accepted:
            # A fresh window avoids stale identity, role permissions, and cached history.
            self.replacement = MainWindow(self.network, dialog.user_info)
            self.replacement.show()
            self._keep_connection = True
            self.close()

    def closeEvent(self, event):
        self._closing = True
        self.chat_refresh_timer.stop()
        if self.admin_window:
            self.admin_window.close()
        if not getattr(self, "_keep_connection", False):
            self.network.disconnect()
        event.accept()
