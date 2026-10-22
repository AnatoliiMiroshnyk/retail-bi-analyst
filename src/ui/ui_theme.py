"""Application-wide Qt styles for Retail BI Analyst."""

from __future__ import annotations

from typing import Literal

ThemeName = Literal["light", "dark"]

LIGHT_STYLE = """
/* ---------- Base ---------- */
QMainWindow, QDialog {
    background-color: #eef2f7;
    color: #172033;
}
QWidget {
    color: #172033;
    background-color: transparent;
}
QWidget#centralWidget {
    background-color: #eef2f7;
}
QLabel {
    background-color: transparent;
    color: #25324a;
}

/* ---------- Menu ---------- */
QMenuBar {
    background-color: #ffffff;
    color: #172033;
    border-bottom: 1px solid #cbd5e1;
    padding: 3px 6px;
}
QMenuBar::item {
    background-color: transparent;
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background-color: #dbeafe;
    color: #1d4ed8;
}
QMenu {
    background-color: #ffffff;
    color: #172033;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px;
}
QMenu::item {
    border-radius: 4px;
    padding: 7px 28px 7px 10px;
}
QMenu::item:selected {
    background-color: #dbeafe;
    color: #1d4ed8;
}
QMenu::separator {
    height: 1px;
    background-color: #d9e1ec;
    margin: 5px 8px;
}

/* ---------- Tabs ---------- */
QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background-color: #dfe7f1;
    color: #475569;
    border: 1px solid #cbd5e1;
    border-bottom: none;
    min-width: 110px;
    padding: 9px 16px;
    margin-right: 3px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}
QTabBar::tab:hover {
    background-color: #eaf2ff;
    color: #1d4ed8;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1d4ed8;
    font-weight: 600;
    border-color: #93b4e8;
}
QTabBar::tab:disabled {
    color: #94a3b8;
    background-color: #edf1f5;
}

/* ---------- Buttons ---------- */
QPushButton {
    background-color: #e5ebf3;
    color: #172033;
    border: 1px solid #b8c5d6;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #d7e5f8;
    border-color: #7ba4dc;
}
QPushButton:pressed {
    background-color: #c6d9f2;
    border-color: #4f83c5;
}
QPushButton:focus {
    border: 2px solid #3b82f6;
    padding: 6px 11px;
}
QPushButton:disabled {
    background-color: #eef2f6;
    color: #9aa7b8;
    border-color: #d8e0e9;
}

/* ---------- Inputs ---------- */
QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: #ffffff;
    color: #172033;
    border: 1px solid #b8c5d6;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 24px;
    selection-background-color: #bfdbfe;
    selection-color: #172033;
}
QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover,
QSpinBox:hover, QLineEdit:hover {
    border-color: #7ba4dc;
}
QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #3b82f6;
    padding: 4px 7px;
}
QComboBox:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled,
QSpinBox:disabled, QLineEdit:disabled {
    background-color: #e9eef4;
    color: #94a3b8;
    border-color: #d4dce6;
}
QComboBox::drop-down {
    border: none;
    border-left: 1px solid #d6dee9;
    width: 26px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #172033;
    border: 1px solid #b8c5d6;
    selection-background-color: #dbeafe;
    selection-color: #1d4ed8;
    outline: 0;
}
QCalendarWidget QWidget {
    background-color: #ffffff;
    color: #172033;
}
QCalendarWidget QToolButton {
    color: #172033;
    background-color: #e5ebf3;
    border-radius: 4px;
    padding: 4px;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #ffffff;
    color: #172033;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

/* ---------- Tables ---------- */
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f4f7fb;
    color: #172033;
    gridline-color: #d8e0e9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #cfe3ff;
    selection-color: #10213a;
}
QTableView::item {
    padding: 5px;
}
QTableView::item:hover {
    background-color: #e8f1ff;
}
QTableView::item:selected {
    background-color: #cfe3ff;
    color: #10213a;
}
QHeaderView::section {
    background-color: #dde6f1;
    color: #27364d;
    border: none;
    border-right: 1px solid #c5d0de;
    border-bottom: 1px solid #b8c5d6;
    padding: 7px;
    font-weight: 600;
}
QTableCornerButton::section {
    background-color: #dde6f1;
    border: 1px solid #b8c5d6;
}

/* ---------- Report ---------- */
QTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #172033;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 10px;
    selection-background-color: #bfdbfe;
}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {
    background-color: #edf2f7;
    width: 13px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #b7c4d5;
    border-radius: 6px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background-color: #8fa3bb; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #edf2f7;
    height: 13px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #b7c4d5;
    border-radius: 6px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background-color: #8fa3bb; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ---------- Tooltips and status ---------- */
QToolTip {
    background-color: #172033;
    color: #ffffff;
    border: 1px solid #334155;
    padding: 5px;
}
QStatusBar {
    background-color: #ffffff;
    color: #475569;
    border-top: 1px solid #cbd5e1;
}
"""

DARK_STYLE = """
/* ---------- Base ---------- */
QMainWindow, QDialog {
    background-color: #171a1f;
    color: #e5e7eb;
}
QWidget {
    color: #e5e7eb;
    background-color: transparent;
}
QWidget#centralWidget {
    background-color: #171a1f;
}
QLabel {
    background-color: transparent;
    color: #d7dce5;
}

/* ---------- Menu ---------- */
QMenuBar {
    background-color: #20242b;
    color: #e5e7eb;
    border-bottom: 1px solid #3a404a;
    padding: 3px 6px;
}
QMenuBar::item {
    background-color: transparent;
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background-color: #353c47;
    color: #ffffff;
}
QMenu {
    background-color: #252a32;
    color: #e5e7eb;
    border: 1px solid #4a515d;
    border-radius: 6px;
    padding: 5px;
}
QMenu::item {
    border-radius: 4px;
    padding: 7px 28px 7px 10px;
}
QMenu::item:selected {
    background-color: #3a424e;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #444b56;
    margin: 5px 8px;
}

/* ---------- Tabs ---------- */
QTabWidget::pane {
    background-color: #20242b;
    border: 1px solid #454c57;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background-color: #2b3038;
    color: #aeb7c5;
    border: 1px solid #444b56;
    border-bottom: none;
    min-width: 110px;
    padding: 9px 16px;
    margin-right: 3px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}
QTabBar::tab:hover {
    background-color: #373e48;
    color: #ffffff;
}
QTabBar::tab:selected {
    background-color: #20242b;
    color: #ffffff;
    font-weight: 600;
    border-color: #626c7b;
}
QTabBar::tab:disabled {
    color: #687281;
    background-color: #242830;
}

/* ---------- Buttons ---------- */
QPushButton {
    background-color: #303640;
    color: #e7eaf0;
    border: 1px solid #535c69;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #3b424d;
    border-color: #747f8f;
}
QPushButton:pressed {
    background-color: #262b33;
    border-color: #8994a4;
}
QPushButton:focus {
    border: 2px solid #94a3b8;
    padding: 6px 11px;
}
QPushButton:disabled {
    background-color: #242830;
    color: #687281;
    border-color: #343a44;
}

/* ---------- Inputs ---------- */
QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: #252a32;
    color: #edf0f5;
    border: 1px solid #505966;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 24px;
    selection-background-color: #596575;
    selection-color: #ffffff;
}
QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover,
QSpinBox:hover, QLineEdit:hover {
    border-color: #788392;
    background-color: #2b313a;
}
QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #94a3b8;
    padding: 4px 7px;
}
QComboBox:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled,
QSpinBox:disabled, QLineEdit:disabled {
    background-color: #20242b;
    color: #626c79;
    border-color: #353b45;
}
QComboBox::drop-down {
    border: none;
    border-left: 1px solid #454d59;
    width: 26px;
}
QComboBox QAbstractItemView {
    background-color: #252a32;
    color: #edf0f5;
    border: 1px solid #596270;
    selection-background-color: #454e5b;
    selection-color: #ffffff;
    outline: 0;
}
QCalendarWidget QWidget {
    background-color: #252a32;
    color: #edf0f5;
}
QCalendarWidget QToolButton {
    color: #edf0f5;
    background-color: #353b45;
    border-radius: 4px;
    padding: 4px;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #252a32;
    color: #edf0f5;
    selection-background-color: #596575;
    selection-color: #ffffff;
}

/* ---------- Tables ---------- */
QTableView {
    background-color: #20242b;
    alternate-background-color: #252a32;
    color: #e5e7eb;
    gridline-color: #3a414b;
    border: 1px solid #454c57;
    border-radius: 6px;
    selection-background-color: #495360;
    selection-color: #ffffff;
}
QTableView::item {
    padding: 5px;
}
QTableView::item:hover {
    background-color: #303742;
}
QTableView::item:selected {
    background-color: #495360;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #303640;
    color: #e7eaf0;
    border: none;
    border-right: 1px solid #454c57;
    border-bottom: 1px solid #535c69;
    padding: 7px;
    font-weight: 600;
}
QTableCornerButton::section {
    background-color: #303640;
    border: 1px solid #535c69;
}

/* ---------- Report ---------- */
QTextEdit, QTextBrowser {
    background-color: #20242b;
    color: #e5e7eb;
    border: 1px solid #454c57;
    border-radius: 7px;
    padding: 10px;
    selection-background-color: #596575;
}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {
    background-color: #20242b;
    width: 13px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #4b5563;
    border-radius: 6px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background-color: #687384; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #20242b;
    height: 13px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #4b5563;
    border-radius: 6px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background-color: #687384; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ---------- Tooltips and status ---------- */
QToolTip {
    background-color: #e5e7eb;
    color: #171a1f;
    border: 1px solid #ffffff;
    padding: 5px;
}
QStatusBar {
    background-color: #20242b;
    color: #aeb7c5;
    border-top: 1px solid #3a404a;
}
"""


def build_stylesheet(theme: str, font_size_pt: int) -> str:
    """Return a complete, non-accumulating stylesheet for the selected theme."""
    normalized = theme if theme in {"light", "dark"} else "light"
    size = max(8, min(int(font_size_pt), 18))
    base = DARK_STYLE if normalized == "dark" else LIGHT_STYLE
    return f"{base}\nQWidget {{ font-size: {size}pt; }}\n"
