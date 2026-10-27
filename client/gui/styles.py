"""Consistent restrained desktop styling shared by every window."""

DARK_THEME = """
QWidget { background: #1e1f22; color: #e7e9ed; font: 10pt "Segoe UI"; }
QLabel#title { font-size: 20pt; font-weight: 600; color: white; }
QLabel#subtitle, QLabel#status { color: #aeb8c8; }
QLineEdit, QTextEdit, QListWidget, QTableWidget {
    background: #25272d; border: 1px solid #3b414c; border-radius: 5px; padding: 7px;
    selection-background-color: #315b9d;
}
QLineEdit:focus, QTextEdit:focus { border-color: #6597ed; }
QListWidget::item { padding: 9px; }
QListWidget::item:selected { background: #315b9d; }
QPushButton { background: #345e9f; color: white; border: 0; border-radius: 5px; padding: 8px 14px; }
QPushButton:hover { background: #416fb5; }
QPushButton:disabled { background: #333943; color: #949dab; }
QPushButton#danger { background: #923f49; }
QHeaderView::section, QTabBar::tab { background: #30343c; padding: 8px; }
QTabBar::tab:selected { background: #345e9f; }
QTabWidget::pane { border: 1px solid #3b414c; }
QStatusBar { color: #aeb8c8; }
"""
