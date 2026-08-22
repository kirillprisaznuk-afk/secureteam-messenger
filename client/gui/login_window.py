from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt


class LoginWindow(QDialog):
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.user_info = None

        self.setWindowTitle("Sign in to Corporate Messenger")
        self.setFixedSize(600, 320)  
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Corporate Messenger")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("Sign in to your workspace")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.username_edit = QLineEdit()
        self.username_edit.setMinimumWidth(260)
        self.username_edit.setPlaceholderText("Username (admin)")

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumWidth(260)
        self.password_edit.setPlaceholderText("Password (admin123)")
        self.password_edit.returnPressed.connect(self.try_login)

        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.login_btn = QPushButton("Sign In")
        self.login_btn.clicked.connect(self.try_login)
        btn_row.addWidget(self.login_btn)

        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def apply_dark_theme(self):
        stylesheet = """
        QDialog {
            background-color: #1e1f22;
        }
        QLabel {
            color: #f0f0f0;
            font-family: Segoe UI, Arial;
        }
        QLabel#title {
            font-size: 14pt;
            font-weight: 600;
            color: #ffffff;
        }
        QLabel#subtitle {
            font-size: 9pt;
            color: #c8c8c8;
        }
        QLabel#status {
            font-size: 8pt;
            color: #ff6666;
        }
        QLineEdit {
            background-color: #232428;
            border: 1px solid #33363d;
            border-radius: 4px;
            padding: 6px;
            color: #f0f0f0;
            selection-background-color: #2b7cff;
        }
        QLineEdit:focus {
            border: 1px solid #2b7cff;
        }
        QPushButton {
            background-color: #2b7cff;
            color: white;
            border-radius: 4px;
            padding: 6px 18px;
        }
        QPushButton:hover {
            background-color: #3c8dff;
        }
        QPushButton:pressed {
            background-color: #2464d6;
        }
        """
        self.setStyleSheet(stylesheet)

    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            self.status_label.setText("Enter username and password")
            return

        self.status_label.setText("Signing in...")
        self.status_label.repaint()

        resp = self.network.login(username, password)
        if not resp.get("success"):
            QMessageBox.critical(self, "Error", resp.get("error", "Invalid credentials"))
            self.status_label.setText("Login failed")
            return

        self.user_info = {
            "user_id": resp.get("user_id"),
            "username": resp.get("username"),
            "role": resp.get("role"),
        }
        self.accept()
