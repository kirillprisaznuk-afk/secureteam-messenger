from PyQt5.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from client.gui.admin.audit_tab import AuditTab
from client.gui.admin.chats_tab import ChatsTab
from client.gui.admin.users_tab import UsersTab


class AdminWindow(QMainWindow):
    def __init__(self, network_client, role: str, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.role = role
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        self.setWindowTitle("Administration · SecureTeam Messenger")
        self.setMinimumSize(900, 580)
        self.resize(1140, 740)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Workspace administration", objectName="title"))
        hint = QLabel("People, conversations and administrative activity", objectName="subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.users_tab = UsersTab(self.network)
        self.chats_tab = ChatsTab(self.network)
        self.audit_tab = (
            AuditTab(self.network) if self.role in {"owner", "org_admin"} else QWidget()
        )
        self.users_tab.set_read_only(self.role == "department_manager")

        self.tab_widget.addTab(self.users_tab, "Users")
        self.tab_widget.addTab(self.chats_tab, "Chats")
        if self.role in {"owner", "org_admin"}:
            self.tab_widget.addTab(self.audit_tab, "Audit")

        self.setCentralWidget(central)

    def apply_dark_theme(self):
        from client.gui.styles import DARK_THEME

        self.setStyleSheet(DARK_THEME)

    def closeEvent(self, event):
        for child in (self.users_tab, self.chats_tab, self.audit_tab):
            child._closing = True
            timer = getattr(child, "refresh_timer", None)
            if timer:
                timer.stop()
        event.accept()

    def showEvent(self, event):
        for child in (self.users_tab, self.chats_tab, self.audit_tab):
            child._closing = False
            timer = getattr(child, "refresh_timer", None)
            if timer:
                timer.start()
        super().showEvent(event)
