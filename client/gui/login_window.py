"""Sign-in dialog with background connection and authentication."""

from PyQt5 import sip
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from client.controller import background
from client.gui.styles import DARK_THEME


class LoginWindow(QDialog):
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.user_info = None
        self.setWindowTitle("Sign in · SecureTeam Messenger")
        self.setMinimumSize(480, 500)
        self.resize(540, 550)
        self.setStyleSheet(DARK_THEME)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 30, 32, 26)
        layout.setSpacing(12)
        layout.addWidget(QLabel("WORKSPACE SIGN-IN", objectName="eyebrow"))
        title = QLabel("SecureTeam Messenger", objectName="title")
        title.setWordWrap(True)
        layout.addWidget(title)
        subtitle = QLabel("A shared space for your team's conversations.", objectName="subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        panel = QFrame(objectName="panel")
        card = QVBoxLayout(panel)
        card.setContentsMargins(22, 20, 22, 20)
        card.setSpacing(18)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(8)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setMaxLength(128)
        self.username_edit.setAccessibleName("Username")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMaxLength(128)
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setAccessibleName("Password")
        self.password_edit.returnPressed.connect(self.try_login)
        form.addRow("&Username", self.username_edit)
        form.addRow("&Password", self.password_edit)
        card.addLayout(form)
        self.login_btn = QPushButton("Sign in", objectName="primary")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.try_login)
        card.addWidget(self.login_btn)
        self.status_label = QLabel("Accounts are created by your workspace administrator.")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setObjectName("status")
        card.addWidget(self.status_label)
        layout.addWidget(panel)
        layout.addStretch(1)
        transport = (
            "Verified TLS" if self.network.ssl_context else "Local TCP · transport is unencrypted"
        )
        self.transport_label = QLabel(
            f"{self.network.host}:{self.network.port}\n{transport}", objectName="hint"
        )
        self.transport_label.setWordWrap(True)
        self.transport_label.setTextFormat(Qt.PlainText)
        layout.addWidget(self.transport_label)
        self.setTabOrder(self.username_edit, self.password_edit)
        self.setTabOrder(self.password_edit, self.login_btn)
        self.username_edit.setFocus()

    def _set_status(self, message, error=False):
        self.status_label.setText(message)
        self.status_label.setProperty("state", "error" if error else "normal")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    @background
    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()  # Spaces can be part of a password.
        if not username or not password:
            self._set_status("Enter your username and password.", error=True)
            return
        self.login_btn.setEnabled(False)
        self.username_edit.setEnabled(False)
        self.password_edit.setEnabled(False)
        self._set_status("Connecting and signing in…")
        try:
            if not self.network.connected:
                connected = yield self.network.connect
                if not connected:
                    self._set_status(self.network.last_error, error=True)
                    return
            response = yield lambda: self.network.login(username, password)
            if not response.get("success"):
                self._set_status(response.get("error", "Sign-in failed"), error=True)
                return
            self.user_info = self.network.user_info.copy()
            self.password_edit.clear()
            self.accept()
        finally:
            if not sip.isdeleted(self):
                self.login_btn.setEnabled(True)
                self.username_edit.setEnabled(True)
                self.password_edit.setEnabled(True)

    def reject(self):
        self._closing = True
        self.network.disconnect()
        super().reject()
