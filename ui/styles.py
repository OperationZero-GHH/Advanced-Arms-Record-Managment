from __future__ import annotations


LIGHT_QSS = """
QMainWindow, QDialog {
    background-color: #f5f7fb;
    color: #1f2430;
}
QFrame#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #dfe3eb;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d4d9e3;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton:hover {
    background: #eef4ff;
    border-color: #85a8ff;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #ccd3df;
    border-radius: 6px;
    padding: 6px;
    background: #ffffff;
}
QTableWidget {
    background: white;
    gridline-color: #e8ebf2;
    alternate-background-color: #f8faff;
}
QHeaderView::section {
    background: #e9effc;
    border: none;
    border-bottom: 1px solid #d3dcf1;
    padding: 6px;
}
"""


DARK_QSS = """
QMainWindow, QDialog {
    background-color: #151a22;
    color: #e8ecf3;
}
QFrame#sidebar {
    background-color: #1c2330;
    border-right: 1px solid #2d3747;
}
QPushButton {
    background: #222b3a;
    border: 1px solid #3c485c;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e8ecf3;
}
QPushButton:hover {
    background: #2f3c52;
    border-color: #72a1ff;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #3c485c;
    border-radius: 6px;
    padding: 6px;
    background: #222b3a;
    color: #f0f4ff;
}
QTableWidget {
    background: #1d2433;
    alternate-background-color: #222b3a;
    gridline-color: #2f3a4e;
}
QHeaderView::section {
    background: #2a3447;
    border: none;
    border-bottom: 1px solid #3b4962;
    padding: 6px;
}
QStatusBar {
    background: #1c2330;
    color: #b7c3d9;
}
"""
