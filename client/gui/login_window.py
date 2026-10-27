"""Sign-in dialog with background connection and authentication."""

from PyQt5 import sip
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from client.controller import background
from client.gui.styles import DARK_THEME


class LoginWindow(QDialog):
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.user_info = None
        self.setWindowTitle("Sign in · SecureTeam Messenger")
        self.setMinimumSize(480, 360)
        self.resize(520, 380)
        self.setStyleSheet(DARK_THEME)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)
        title = QLabel("SecureTeam Messenger", objectName="title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("Sign in to your workspace", objectName="subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        form = QFormLayout()
        form.setSpacing(12)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Your username")
        self.username_edit.setMaxLength(128)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMaxLength(128)
        self.password_edit.setPlaceholderText("Your password")
        self.password_edit.returnPressed.connect(self.try_login)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)
        layout.addLayout(form)
        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self.try_login)
        layout.addWidget(self.login_btn)
        self.status_label = QLabel("Accounts are created by your workspace administrator.")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        transport = (
            "Verified TLS" if self.network.ssl_context else "Local TCP · transport is unencrypted"
        )
        layout.addWidget(QLabel(f"{self.network.host}:{self.network.port} · {transport}"))

    @background
    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()  # Spaces can be part of a password.
        if not username or not password:
            self.status_label.setText("Enter your username and password.")
            return
        self.login_btn.setEnabled(False)
        self.username_edit.setEnabled(False)
        self.password_edit.setEnabled(False)
        self.status_label.setText("Connecting and signing in…")
        try:
            if not self.network.connected:
                connected = yield self.network.connect
                if not connected:
                    self.status_label.setText(self.network.last_error)
                    return
            response = yield lambda: self.network.login(username, password)
            if not response.get("success"):
                self.status_label.setText(response.get("error", "Sign-in failed"))
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
