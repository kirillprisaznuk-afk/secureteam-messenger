from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QInputDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QComboBox,
)

from client.network import NetworkClient


class UserEditDialog(QDialog):

    def __init__(
        self,
        mode: str,
        roles: list[str],
        username: str = "",
        role: str = "employee",
        parent=None,
    ):
        super().__init__(parent)
        self.mode = mode
        self.roles = roles

        self.setWindowTitle("Create user" if mode == "create" else "Change role")
        self.resize(320, 160)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.username_edit = QLineEdit(self)
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.role_combo = QComboBox(self)
        self.role_combo.addItems(self.roles)

        if mode == "create":
            form.addRow("Username:", self.username_edit)
            form.addRow("Password:", self.password_edit)
        else:
            self.username_edit.setText(username)
            self.username_edit.setReadOnly(True)
            form.addRow("Username:", self.username_edit)

        form.addRow("Role:", self.role_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        idx = self.role_combo.findText(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    def get_values(self):
        return {
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text().strip(),
            "role": self.role_combo.currentText(),
        }


class UsersTab(QWidget):

    AVAILABLE_ROLES = ["owner", "org_admin", "department_manager", "employee", "guest"]

    def __init__(self, network: NetworkClient, parent=None):
        super().__init__(parent)
        self.network = network

        self._read_only = False

        self._init_ui()
        self._init_timer()
        self.load_users()


    def _init_ui(self):
        layout = QVBoxLayout(self)

        buttons_layout = QHBoxLayout()

        self.btn_create = QPushButton("Create")
        self.btn_change_role = QPushButton("Change Role")
        self.btn_block = QPushButton("Block")
        self.btn_unblock = QPushButton("Unblock")
        self.btn_delete = QPushButton("Delete")

        buttons_layout.addWidget(self.btn_create)
        buttons_layout.addWidget(self.btn_change_role)
        buttons_layout.addWidget(self.btn_block)
        buttons_layout.addWidget(self.btn_unblock)
        buttons_layout.addWidget(self.btn_delete)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Username", "Role", "Blocked", "Online"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        self.btn_create.clicked.connect(self.on_create_clicked)
        self.btn_change_role.clicked.connect(self.on_change_role_clicked)
        self.btn_block.clicked.connect(self.on_block_clicked)
        self.btn_unblock.clicked.connect(self.on_unblock_clicked)
        self.btn_delete.clicked.connect(self.on_delete_clicked)



    def _init_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(3000)
        self.refresh_timer.timeout.connect(self.load_users)
        self.refresh_timer.start()


    def load_users(self):
        resp = self.network.get_all_users()
        if not resp.get("success"):
            return

        users = resp.get("users", [])
        self.table.setRowCount(len(users))

        for row, user in enumerate(users):
            uid = user.get("id")
            username = user.get("username")
            role = user.get("role")
            blocked = "Yes" if user.get("is_blocked") else "No"
            online = "Online" if user.get("is_online") else "Offline"

            self.table.setItem(row, 0, QTableWidgetItem(str(uid)))
            self.table.setItem(row, 1, QTableWidgetItem(username))
            self.table.setItem(row, 2, QTableWidgetItem(role))
            self.table.setItem(row, 3, QTableWidgetItem(blocked))

            online_item = QTableWidgetItem(online)
            if user.get("is_online"):
                online_item.setForeground(Qt.green)
            else:
                online_item.setForeground(Qt.gray)
            self.table.setItem(row, 4, online_item)

    def _get_selected_user_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _get_selected_username_and_role(self):
        row = self.table.currentRow()
        if row < 0:
            return None, None
        item_user = self.table.item(row, 1)
        item_role = self.table.item(row, 2)
        if not item_user or not item_role:
            return None, None
        return item_user.text(), item_role.text()


    def set_read_only(self, read_only: bool):

        self._read_only = read_only
        enabled = not read_only
        self.btn_create.setEnabled(enabled)
        self.btn_change_role.setEnabled(enabled)
        self.btn_block.setEnabled(enabled)
        self.btn_unblock.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)


    def on_create_clicked(self):
        if self._read_only:
            return

        dlg = UserEditDialog(
            mode="create",
            roles=self.AVAILABLE_ROLES,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        values = dlg.get_values()
        username = values["username"]
        password = values["password"]
        role = values["role"]

        if not username or not password:
            QMessageBox.warning(self, "Invalid data", "Username and password required.")
            return

        resp = self.network.create_user(username, password, role)
        if not resp.get("success"):
            QMessageBox.warning(
                self, "Error", resp.get("error", "Failed to create user")
            )
            return

        self.load_users()

    def on_change_role_clicked(self):
        if self._read_only:
            return

        uid = self._get_selected_user_id()
        username, current_role = self._get_selected_username_and_role()
        if not uid or not username:
            QMessageBox.warning(self, "No selection", "Select a user first.")
            return

        dlg = UserEditDialog(
            mode="edit",
            roles=self.AVAILABLE_ROLES,
            username=username,
            role=current_role,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        values = dlg.get_values()
        new_role = values["role"]
        if new_role == current_role:
            return

        resp = self.network.update_user(uid, new_role)
        if not resp.get("success"):
            QMessageBox.warning(
                self, "Error", resp.get("error", "Failed to update role")
            )
            return

        self.load_users()

    def on_block_clicked(self):
        if self._read_only:
            return

        uid = self._get_selected_user_id()
        if not uid:
            QMessageBox.warning(self, "No selection", "Select a user first.")
            return
        resp = self.network.block_user(uid)
        if not resp.get("success"):
            QMessageBox.warning(self, "Error", resp.get("error", "Unknown error"))
        self.load_users()

    def on_unblock_clicked(self):
        if self._read_only:
            return

        uid = self._get_selected_user_id()
        if not uid:
            QMessageBox.warning(self, "No selection", "Select a user first.")
            return
        resp = self.network.unblock_user(uid)
        if not resp.get("success"):
            QMessageBox.warning(self, "Error", resp.get("error", "Unknown error"))
        self.load_users()

    def on_delete_clicked(self):
        if self._read_only:
            return

        uid = self._get_selected_user_id()
        if not uid:
            QMessageBox.warning(self, "No selection", "Select a user first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete user",
            "Are you sure you want to delete this user?",
        )
        if confirm != QMessageBox.Yes:
            return

        resp = self.network.delete_user(uid)
        if not resp.get("success"):
            QMessageBox.warning(self, "Error", resp.get("error", "Unknown error"))
        self.load_users()
