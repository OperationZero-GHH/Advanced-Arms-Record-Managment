from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from utils.file_utils import safe_copy


class ItemEditorDialog(QDialog):
    def __init__(self, item: dict | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Item Editor")
        self.setAcceptDrops(True)
        self.image_path: str | None = item.get("image_path") if item else None

        self.identifier = QLineEdit(item.get("identifier", "") if item else "")
        self.title = QLineEdit(item.get("title", "") if item else "")
        self.category = QLineEdit(item.get("category", "") if item else "")
        self.available = QCheckBox("Available")
        self.available.setChecked(bool(item.get("available", True) if item else True))

        self.preview = QLabel("Drop image or browse")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(160)
        self.preview.setStyleSheet("border:1px dashed #7f8ea3; border-radius:8px;")

        self.btn_browse = QPushButton("Browse Image")
        self.btn_browse.clicked.connect(self.pick_image)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.accept)

        form = QFormLayout()
        form.addRow("Identifier", self.identifier)
        form.addRow("Title", self.title)
        form.addRow("Category", self.category)
        form.addRow("", self.available)

        actions = QHBoxLayout()
        actions.addWidget(self.btn_browse)
        actions.addWidget(self.btn_save)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addWidget(self.preview)
        root.addLayout(actions)
        self.setLayout(root)

        if self.image_path:
            self._set_preview(self.image_path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        self._store_image(path)

    def pick_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self._store_image(file_path)

    def _store_image(self, source_path: str) -> None:
        try:
            stored = safe_copy(source_path, Path("assets/images"))
            self.image_path = str(stored)
            self._set_preview(self.image_path)
        except Exception as exc:
            QMessageBox.critical(self, "Image Error", str(exc))

    def _set_preview(self, image_path: str) -> None:
        pixmap = QPixmap(image_path).scaled(
            240, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.preview.setPixmap(pixmap)

    def payload(self) -> dict:
        return {
            "identifier": self.identifier.text().strip(),
            "title": self.title.text().strip(),
            "category": self.category.text().strip(),
            "available": self.available.isChecked(),
            "image_path": self.image_path,
        }
