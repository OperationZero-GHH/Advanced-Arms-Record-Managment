from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from database.db_manager import DatabaseManager
from database.models import User


class LoginWindow(QDialog):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.db = db
        self.authenticated_user: User | None = None
        self.setWindowTitle("Sign In")
        self.setMinimumWidth(360)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.info = QLabel("Default credentials: admin/admin123")
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)

        form = QFormLayout()
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)

        root = QVBoxLayout()
        root.addWidget(self.info)
        root.addLayout(form)
        root.addWidget(self.login_btn)
        self.setLayout(root)

    def handle_login(self) -> None:
        user = self.db.authenticate(self.username_edit.text().strip(), self.password_edit.text())
        if user is None:
            QMessageBox.warning(self, "Auth Failed", "Invalid credentials or inactive account.")
            return
        self.authenticated_user = user
        self.accept()
