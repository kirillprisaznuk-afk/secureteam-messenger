from shared.constants import *

LIGHT_THEME = f"""
QWidget {{
    background-color: {COLOR_BACKGROUND_LIGHT};
    color: {COLOR_TEXT_LIGHT};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}}

QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: {COLOR_PRIMARY_DARK};
}}

QLineEdit, QTextEdit {{
    background-color: white;
    border: 2px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 10px;
}}

QLineEdit:focus, QTextEdit:focus {{
    border: 2px solid {COLOR_PRIMARY};
}}

QListWidget {{
    background-color: white;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 12px;
    border-radius: 8px;
    margin: 2px;
}}

QListWidget::item:hover {{
    background-color: {COLOR_HOVER};
}}

QListWidget::item:selected {{
    background-color: #EFF6FF;
    border-left: 4px solid {COLOR_PRIMARY};
}}

QScrollBar:vertical {{
    background-color: #F3F4F6;
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: #D1D5DB;
    border-radius: 6px;
}}

QLabel[subtitle="true"] {{
    color: #6B7280;
    font-size: 12px;
}}
"""

def get_theme(theme_name: str) -> str:
    return LIGHT_THEME
