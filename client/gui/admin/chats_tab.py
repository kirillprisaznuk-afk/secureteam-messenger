from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.controller import background
from client.gui.conversation_view import ROW_PRESENTATION, ConversationDelegate
from client.gui.styles import DARK_THEME, configure_table, style_table_item
from client.network import NetworkClient


class MembersDialog(QDialog):
    def __init__(self, network: NetworkClient, current_members: list[int], parent=None):
        super().__init__(parent)
        self.network = network
        self.current_members = set(current_members)
        self.selected_members: set[int] = set(current_members)

        self.setWindowTitle("Chat members")
        self.setStyleSheet(DARK_THEME)
        self.setMinimumSize(440, 360)
        self.resize(540, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Conversation members", objectName="sectionTitle"))
        hint = QLabel(
            "Select the users who should have access to this conversation.", objectName="hint"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Member"])
        configure_table(self.table, stretch=1, widths={0: 64, 2: 100})
        self.table.setAccessibleName("Choose conversation members")
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.button(QDialogButtonBox.Ok).setText("Apply selection")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_users()

    @background
    def load_users(self):
        resp = yield lambda: self.network.get_all_users()
        if not resp.get("success"):
            QMessageBox.critical(self, "Error", resp.get("error", "Failed to load users"))
            return

        users = resp.get("users", [])
        self.table.setRowCount(len(users))

        for row, u in enumerate(users):
            uid = u["id"]
            username = u["username"]

            id_item = QTableWidgetItem(str(uid))
            username_item = QTableWidgetItem(username)
            member_item = QTableWidgetItem()
            member_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            member_item.setCheckState(Qt.Checked if uid in self.current_members else Qt.Unchecked)

            style_table_item(id_item, muted=True, centered=True)
            style_table_item(username_item)
            member_item.setToolTip(f"Include {username} in this conversation")
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, username_item)
            self.table.setItem(row, 2, member_item)

        self.table.cellChanged.connect(self.on_cell_changed)

    def on_cell_changed(self, row: int, column: int):
        if column != 2:
            return
        id_item = self.table.item(row, 0)
        member_item = self.table.item(row, 2)
        if not id_item or not member_item:
            return
        try:
            uid = int(id_item.text())
        except ValueError:
            return
        if member_item.checkState() == Qt.Checked:
            self.selected_members.add(uid)
        else:
            self.selected_members.discard(uid)

    def get_selected_members(self) -> list[int]:
        return sorted(self.selected_members)


class ChatsTab(QWidget):
    def __init__(self, network: NetworkClient, parent=None):
        super().__init__(parent)
        self.network = network

        self.current_chat_id: int | None = None
        self.chats_cache: list[dict] = []

        self._init_ui()
        self._init_timer()

        self.load_chats()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Workspace conversations", objectName="sectionTitle"))
        hint = QLabel("Manage names, membership and read-only archives.", objectName="hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_create = QPushButton("Create conversation", objectName="primary")
        self.btn_rename = QPushButton("Rename")
        self.btn_members = QPushButton("Edit members")
        self.btn_archive = QPushButton("Archive")
        self.btn_unarchive = QPushButton("Unarchive")
        self.btn_delete = QPushButton("Delete", objectName="danger")

        btn_layout.addWidget(self.btn_create)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        actions = QHBoxLayout()
        actions.addWidget(self.btn_rename)
        actions.addWidget(self.btn_members)
        actions.addWidget(self.btn_archive)
        actions.addWidget(self.btn_unarchive)
        actions.addStretch()
        actions.addWidget(self.btn_delete)
        layout.addLayout(actions)

        self.chats_list = QListWidget(self)
        self.chats_list.setItemDelegate(ConversationDelegate(self.chats_list))
        self.chats_list.setAccessibleName("Administer workspace conversations")
        self.chats_list.itemSelectionChanged.connect(self.on_chat_selected)
        layout.addWidget(self.chats_list)

        self.btn_refresh.clicked.connect(self.load_chats)
        self.btn_create.clicked.connect(self.create_chat)
        self.btn_rename.clicked.connect(self.rename_chat)
        self.btn_members.clicked.connect(self.edit_members)
        self.btn_archive.clicked.connect(self.archive_chat)
        self.btn_unarchive.clicked.connect(self.unarchive_chat)
        self.btn_delete.clicked.connect(self.delete_chat)

    def _init_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.load_chats_silent)
        self.refresh_timer.start()

    @background
    def load_chats(self):
        yield from self._load_chats_internal(silent=False)

    @background
    def load_chats_silent(self):
        yield from self._load_chats_internal(silent=True)

    def _load_chats_internal(self, silent: bool):
        resp = yield lambda: self.network.admin_get_all_chats()
        if not resp.get("success"):
            if not silent:
                QMessageBox.critical(
                    self,
                    "Error",
                    resp.get("error", "Failed to load chats"),
                )
            return

        chats = resp.get("chats", [])
        self.chats_cache = chats

        prev_chat_id = self.current_chat_id

        self.chats_list.blockSignals(True)
        self.chats_list.clear()

        for chat in chats:
            chat_id = chat["id"]
            name = chat["name"]
            archived = chat["archived"]
            owner = chat["owner_username"]
            members_count = chat["members_count"]

            text = name
            if archived:
                text += " (archived)"
            text += f"  [{owner}, {members_count} members]"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, chat_id)
            detail = f"{members_count} members · Owner: {owner}" + (
                " · Archived" if archived else " · Active"
            )
            item.setData(ROW_PRESENTATION, {"title": name, "subtitle": detail})
            item.setToolTip(f"{name}\n{detail}")
            self.chats_list.addItem(item)

            if prev_chat_id is not None and chat_id == prev_chat_id:
                item.setSelected(True)

        self.chats_list.blockSignals(False)

    def _get_selected_chat_id(self) -> int | None:
        item = self.chats_list.currentItem()
        if not item:
            return None
        chat_id = item.data(Qt.UserRole)
        try:
            return int(chat_id)
        except (TypeError, ValueError):
            return None

    def on_chat_selected(self):
        cid = self._get_selected_chat_id()
        self.current_chat_id = cid

    def _get_chat_info(self, chat_id: int) -> dict | None:
        resp = yield lambda: self.network.admin_get_chat_info(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Failed to get chat info"),
            )
            return None
        return resp.get("chat")

    @background
    def create_chat(self):
        name, ok = QInputDialog.getText(self, "Create chat", "Chat name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        dlg = MembersDialog(self.network, current_members=[], parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        members = dlg.get_selected_members()

        resp = yield lambda: self.network.admin_create_chat(name, members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Create chat failed"),
            )
            return

        self.load_chats()

    @background
    def rename_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        info = yield from self._get_chat_info(chat_id)
        if not info:
            return

        old_name = info["name"]
        members = info["members"]

        new_name, ok = QInputDialog.getText(self, "Rename chat", "New name:", text=old_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        resp = yield lambda: self.network.admin_update_chat(chat_id, new_name, members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Rename failed"),
            )
            return

        self.load_chats()

    @background
    def edit_members(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        info = yield from self._get_chat_info(chat_id)
        if not info:
            return

        name = info["name"]
        members = info["members"]

        dlg = MembersDialog(self.network, current_members=members, parent=self)
        dlg.setWindowTitle(f"Members of '{name}'")
        if dlg.exec_() != QDialog.Accepted:
            return

        new_members = dlg.get_selected_members()

        resp = yield lambda: self.network.admin_update_chat(chat_id, name, new_members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Update members failed"),
            )
            return

        self.load_chats()

    @background
    def archive_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        resp = yield lambda: self.network.admin_archive_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Archive failed"),
            )
            return

        self.load_chats()

    @background
    def unarchive_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        resp = yield lambda: self.network.admin_unarchive_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Unarchive failed"),
            )
            return

        self.load_chats()

    @background
    def delete_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete chat",
            "Are you sure you want to delete this chat? This cannot be undone.",
        )
        if confirm != QMessageBox.Yes:
            return

        resp = yield lambda: self.network.admin_delete_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Delete failed"),
            )
            return

        self.current_chat_id = None
        self.load_chats()
