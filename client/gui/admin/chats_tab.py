from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from client.network import NetworkClient


class MembersDialog(QDialog):


    def __init__(self, network: NetworkClient, current_members: list[int], parent=None):
        super().__init__(parent)
        self.network = network
        self.current_members = set(current_members)
        self.selected_members: set[int] = set(current_members)

        self.setWindowTitle("Chat members")
        self.resize(400, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Member"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_users()

    def load_users(self):
        resp = self.network.get_all_users()
        if not resp.get("success"):
            QMessageBox.critical(
                self, "Error", resp.get("error", "Failed to load users")
            )
            return

        users = resp.get("users", [])
        self.table.setRowCount(len(users))

        for row, u in enumerate(users):
            uid = u["id"]
            username = u["username"]

            id_item = QTableWidgetItem(str(uid))
            username_item = QTableWidgetItem(username)
            member_item = QTableWidgetItem()
            member_item.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
            )
            member_item.setCheckState(
                Qt.Checked if uid in self.current_members else Qt.Unchecked
            )

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

        btn_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_create = QPushButton("Create chat")
        self.btn_rename = QPushButton("Rename")
        self.btn_members = QPushButton("Edit members")
        self.btn_archive = QPushButton("Archive")
        self.btn_unarchive = QPushButton("Unarchive")
        self.btn_delete = QPushButton("Delete")

        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_create)
        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_members)
        btn_layout.addWidget(self.btn_archive)
        btn_layout.addWidget(self.btn_unarchive)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self.chats_list = QListWidget(self)
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


    def load_chats(self):
        self._load_chats_internal(silent=False)

    def load_chats_silent(self):
        self._load_chats_internal(silent=True)

    def _load_chats_internal(self, silent: bool):
        resp = self.network.admin_get_all_chats()
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
        resp = self.network.admin_get_chat_info(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Failed to get chat info"),
            )
            return None
        return resp.get("chat")


    def create_chat(self):
        name, ok = QInputDialog.getText(self, "Create chat", "Chat name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        dlg = MembersDialog(self.network, current_members=[], parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        members = dlg.get_selected_members()

        resp = self.network.admin_create_chat(name, members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Create chat failed"),
            )
            return

        self.load_chats()

    def rename_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        info = self._get_chat_info(chat_id)
        if not info:
            return

        old_name = info["name"]
        members = info["members"]

        new_name, ok = QInputDialog.getText(
            self, "Rename chat", "New name:", text=old_name
        )
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        resp = self.network.admin_update_chat(chat_id, new_name, members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Rename failed"),
            )
            return

        self.load_chats()

    def edit_members(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        info = self._get_chat_info(chat_id)
        if not info:
            return

        name = info["name"]
        members = info["members"]

        dlg = MembersDialog(self.network, current_members=members, parent=self)
        dlg.setWindowTitle(f"Members of '{name}'")
        if dlg.exec_() != QDialog.Accepted:
            return

        new_members = dlg.get_selected_members()

        resp = self.network.admin_update_chat(chat_id, name, new_members)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Update members failed"),
            )
            return

        self.load_chats()

    def archive_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        resp = self.network.admin_archive_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Archive failed"),
            )
            return

        self.load_chats()

    def unarchive_chat(self):
        chat_id = self._get_selected_chat_id()
        if not chat_id:
            QMessageBox.warning(self, "No selection", "Select a chat first.")
            return

        resp = self.network.admin_unarchive_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Unarchive failed"),
            )
            return

        self.load_chats()

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

        resp = self.network.admin_delete_chat(chat_id)
        if not resp.get("success"):
            QMessageBox.critical(
                self,
                "Error",
                resp.get("error", "Delete failed"),
            )
            return

        self.current_chat_id = None
        self.load_chats()
