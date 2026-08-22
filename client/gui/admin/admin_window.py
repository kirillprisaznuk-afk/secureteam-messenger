from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget

from client.gui.admin.users_tab import UsersTab
from client.gui.admin.chats_tab import ChatsTab
from client.gui.admin.audit_tab import AuditTab


class AdminWindow(QMainWindow):
    def __init__(self, network_client, role: str, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.role = role
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        self.setWindowTitle("Admin Console - Corporate Messenger")
        self.resize(900, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.users_tab = UsersTab(self.network)
        self.chats_tab = ChatsTab(self.network)
        self.audit_tab = AuditTab(self.network)

        self.tab_widget.addTab(self.users_tab, "Users")
        self.tab_widget.addTab(self.chats_tab, "Chats")
        self.tab_widget.addTab(self.audit_tab, "Audit")

        self.setCentralWidget(central)

    def apply_dark_theme(self):
        stylesheet = """
        QMainWindow {
            background-color: #1e1f22;
        }
        QWidget {
            background-color: #1e1f22;
            color: #f0f0f0;
            font-family: Segoe UI, Arial;
            font-size: 10pt;
        }
        QTabWidget::pane {
            border: 1px solid #33363d;
        }
        QTabBar::tab {
            background: #232428;
            padding: 6px 12px;
        }
        QTabBar::tab:selected {
            background: #2b7cff;
            color: white;
        }
        QTableWidget {
            background-color: #232428;
            gridline-color: #33363d;
        }
        QHeaderView::section {
            background-color: #2b2d31;
            color: #f0f0f0;
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
        """
        self.setStyleSheet(stylesheet)

    def closeEvent(self, event):
        event.accept()
