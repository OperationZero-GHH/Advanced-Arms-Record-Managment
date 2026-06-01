from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QListWidget, QVBoxLayout


class HistoryDialog(QDialog):
    def __init__(self, rows: list[dict]) -> None:
        super().__init__()
        self.setWindowTitle("Item Activity Timeline")
        self.resize(620, 420)
        self.listing = QListWidget()
        for row in rows:
            actor = row.get("actor_name") or "System"
            self.listing.addItem(
                f"[{row['created_at']}] {row['action'].upper()} by {actor} - {row.get('notes') or ''}"
            )
        layout = QVBoxLayout()
        layout.addWidget(self.listing)
        self.setLayout(layout)
