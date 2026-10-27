"""Shared desktop palette, typography, control states, and small layout helpers."""

from datetime import UTC, datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QGuiApplication, QPalette
from PyQt5.QtWidgets import QHeaderView, QLabel, QSizePolicy, QTableWidget

PALETTE = {
    "background": "#151b24",
    "panel": "#1c2430",
    "surface": "#222d3b",
    "border": "#39485d",
    "text": "#edf2f8",
    "secondary": "#bbc8d9",
    "muted": "#a3b3c9",
    "accent": "#9bc3ff",
    "success": "#91d7b5",
    "danger": "#ffc2c8",
    "own_message": "#263e5f",
}

DARK_THEME = """
QWidget { background: #151b24; color: #edf2f8; font: 10pt "Segoe UI"; }
QLabel { background: transparent; }
QLabel#title { font-size: 18pt; font-weight: 600; }
QLabel#sectionTitle { font-size: 14pt; font-weight: 600; }
QLabel#eyebrow { color: #a3b3c9; font-size: 9pt; font-weight: 600; }
QLabel#subtitle, QLabel#status, QLabel#hint { color: #bbc8d9; }
QLabel#status[state="error"] { color: #ffc2c8; }
QLabel#connection { color: #bbc8d9; padding: 6px 0; }
QFrame#panel, QWidget#panel { background: #1c2430; border: 1px solid #39485d; border-radius: 8px; }
QFrame#composer { background: #1c2430; border-top: 1px solid #39485d; }
QLineEdit, QTextEdit, QComboBox {
    background: #222d3b; border: 1px solid #39485d; border-radius: 6px;
    padding: 9px 12px; selection-background-color: #355e98; selection-color: #ffffff;
}
QLineEdit:disabled { color: #a3b3c9; background: #1c2430; }
QLineEdit:hover, QComboBox:hover { border-color: #6e829f; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #9bc3ff; }
QTextEdit#history { background: #151b24; border: 0; padding: 12px; }
QComboBox { min-height: 20px; padding-right: 26px; }
QComboBox::drop-down { width: 24px; border: 0; }
QComboBox::down-arrow { image: url("asset:/chevron-down.svg"); width: 16px; height: 16px; }
QComboBox QAbstractItemView { background: #222d3b; border: 1px solid #6e829f; selection-background-color: #355e98; padding: 4px; }
QPushButton {
    background: #29374a; color: #edf2f8; border: 1px solid #465974;
    border-radius: 6px; padding: 8px 14px; min-height: 20px;
}
QPushButton:hover { background: #354963; border-color: #8099bc; }
QPushButton:pressed { background: #20314a; }
QPushButton:focus { border: 1px solid #c0d8ff; }
QPushButton#primary { background: #315e9f; border-color: #527fbf; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #3d70b8; }
QPushButton#primary:pressed { background: #274e87; }
QDialogButtonBox QPushButton:default { background: #315e9f; border-color: #9bc3ff; }
QPushButton#danger { background: #442b38; border-color: #a16677; color: #ffcbd1; }
QPushButton#danger:hover { background: #613345; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#danger:disabled {
    background: #202a38; border-color: #39485d; color: #a3b3c9;
}
QListWidget { background: #1c2430; border: 0; border-radius: 6px; padding: 5px; outline: 0; }
QListWidget::item { border-radius: 5px; border: 1px solid transparent; }
QListWidget::item:hover { background: #27364b; }
QListWidget::item:selected { background: #2b466b; border-color: #648fcb; }
QListWidget:focus { border: 1px solid #9bc3ff; }
QTableWidget { background: #1c2430; alternate-background-color: #222d3b; border: 1px solid #39485d; border-radius: 6px; gridline-color: #39485d; selection-background-color: #2b466b; selection-color: #ffffff; }
QTableWidget::item { padding: 6px 10px; border: 0; }
QTableWidget::item:focus { border: 1px solid #9bc3ff; }
QTableView::indicator { width: 18px; height: 18px; border: 1px solid #8099bc; border-radius: 3px; background: #222d3b; }
QTableView::indicator:checked { background: #315e9f; border-color: #9bc3ff; image: url("asset:/check.svg"); }
QHeaderView::section { background: #263347; color: #bbc8d9; font-weight: 600; padding: 11px 10px; border: 0; border-bottom: 1px solid #465974; }
QHeaderView { background: #263347; }
QTabWidget::pane { border: 0; border-top: 1px solid #39485d; }
QTabBar::tab { background: transparent; color: #bbc8d9; padding: 12px 22px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #ffffff; background: #222d3b; border-bottom-color: #9bc3ff; }
QTabBar::tab:hover { background: #27364b; }
QTabBar::tab:focus { border: 1px solid #9bc3ff; }
QSplitter::handle { background: #151b24; }
QSplitter::handle:hover { background: #527fbf; }
QStatusBar { border-top: 1px solid #39485d; color: #bbc8d9; padding: 5px 12px; }
QStatusBar::item { border: 0; }
QScrollBar:vertical { background: #1c2430; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: #61748e; min-height: 32px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #91aacd; }
QScrollBar:horizontal { background: #1c2430; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: #61748e; min-width: 32px; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: #263347; color: #edf2f8; border: 1px solid #8099bc; padding: 6px; }
QMessageBox QLabel { min-width: 260px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; }
"""
DARK_THEME = DARK_THEME.replace("asset:/", Path(__file__).with_name("assets").as_posix() + "/")


def configure_high_dpi() -> None:
    """Called before QApplication; Qt lays out widgets in device-independent units."""
    from PyQt5.QtWidgets import QApplication

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def apply_application_theme(app) -> None:
    """Give popup controls and notifications the same palette as the main widgets."""
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in {
        QPalette.Window: "background",
        QPalette.WindowText: "text",
        QPalette.Base: "panel",
        QPalette.AlternateBase: "surface",
        QPalette.Text: "text",
        QPalette.Button: "surface",
        QPalette.ButtonText: "text",
        QPalette.ToolTipBase: "surface",
        QPalette.ToolTipText: "text",
        QPalette.Highlight: "own_message",
        QPalette.HighlightedText: "text",
        QPalette.PlaceholderText: "muted",
    }.items():
        palette.setColor(role, QColor(PALETTE[color]))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(PALETTE["muted"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(PALETTE["muted"]))
    app.setPalette(palette)
    app.setStyleSheet(DARK_THEME)


def display_time(value: str, *, date: bool = True) -> str:
    """Presentation only: retain the original timestamp in tooltips where available."""
    try:
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)  # Earlier releases wrote naive UTC timestamps.
        moment = moment.astimezone()
        return moment.strftime("%d %b %Y · %H:%M" if date else "%H:%M")
    except (ValueError, TypeError):
        return value


class ElidedLabel(QLabel):
    """Long identities/titles never dictate the window's minimum width."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setTextFormat(Qt.PlainText)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setText(text)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._update_text()

    def _update_text(self):
        super().setText(self.fontMetrics().elidedText(self._full_text, Qt.ElideRight, self.width()))

    def text(self):
        return self._full_text

    def resizeEvent(self, event):
        self._update_text()
        super().resizeEvent(event)


def configure_table(table: QTableWidget, stretch: int, widths: dict[int, int]) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.ElideRight)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(42)
    header = table.horizontalHeader()
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setMinimumSectionSize(52)
    header.setStretchLastSection(False)
    for column, width in widths.items():
        header.setSectionResizeMode(column, QHeaderView.Interactive)
        table.setColumnWidth(column, width)
    header.setSectionResizeMode(stretch, QHeaderView.Stretch)


def style_table_item(item, *, muted=False, centered=False):
    item.setToolTip(item.text())
    if muted:
        item.setForeground(QColor(PALETTE["secondary"]))
    if centered:
        item.setTextAlignment(Qt.AlignCenter)
    return item
