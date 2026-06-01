from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QCompleter,
)

from database.db_manager import DatabaseManager
from database.models import User, UserRole
from services.analytics_engine import AnalyticsEngine
from services.backup_manager import BackupManager
from services.qr_service import QRService
from services.recommendation_engine import RecommendationEngine
from services.reporting_service import ReportingService
from ui.dialogs.history_dialog import HistoryDialog
from ui.dialogs.item_editor import ItemEditorDialog
from ui.styles import DARK_QSS, LIGHT_QSS

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        db: DatabaseManager,
        analytics_engine: AnalyticsEngine,
        recommendation_engine: RecommendationEngine,
        backup_manager: BackupManager,
        qr_service: QRService,
        current_user: User,
    ) -> None:
        super().__init__()
        self.db = db
        self.analytics_engine = analytics_engine
        self.recommendation_engine = recommendation_engine
        self.backup_manager = backup_manager
        self.qr_service = qr_service
        self.current_user = current_user
        self.dark_mode = False
        self.reporting_service = ReportingService(db, analytics_engine)

        self.setWindowTitle("Ultra Advanced Record System")
        self.resize(1280, 780)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._build_ui()
        self._connect_services()
        self._apply_role_permissions()
        self._refresh_items()
        self._refresh_dashboard()
        self._notify_overdues()
        self.backup_manager.schedule(30)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 14, 10, 14)
        side_layout.setSpacing(8)
        side_layout.addWidget(QLabel(f"User: {self.current_user.full_name} ({self.current_user.role.value})"))
        self.nav_list = QListWidget()
        for title in ("Dashboard", "Items", "Gallery", "Recommendations"):
            QListWidgetItem(title, self.nav_list)
        self.nav_list.currentRowChanged.connect(self._switch_page)
        side_layout.addWidget(self.nav_list)

        self.theme_btn = QPushButton("Toggle Theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        side_layout.addWidget(self.theme_btn)
        side_layout.addStretch(1)
        sidebar.setMaximumWidth(260)
        outer.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard_page())
        self.pages.addWidget(self._items_page())
        self.pages.addWidget(self._gallery_page())
        self.pages.addWidget(self._recommendations_page())
        outer.addWidget(self.pages, 1)
        self.nav_list.setCurrentRow(0)

        self._build_menu()
        self._toggle_theme()

    def _build_menu(self) -> None:
        import_action = QAction("Bulk Import", self)
        import_action.triggered.connect(self._bulk_import)
        export_action = QAction("Export Excel", self)
        export_action.triggered.connect(self._export_excel)
        pdf_action = QAction("Generate PDF Report", self)
        pdf_action.triggered.connect(self._export_pdf)
        backup_action = QAction("Run Backup", self)
        backup_action.triggered.connect(self.backup_manager.run_backup_async)

        menu = self.menuBar().addMenu("Operations")
        menu.addAction(import_action)
        menu.addAction(export_action)
        menu.addAction(pdf_action)
        menu.addAction(backup_action)

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.metrics = QLabel("Metrics")
        self.canvas = FigureCanvas(Figure(figsize=(7, 3)))
        layout.addWidget(self.metrics)
        layout.addWidget(self.canvas)
        return page

    def _items_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Smart search by title or identifier...")
        self.search_edit.textChanged.connect(self._refresh_items)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setCompleter(QCompleter(self.db.identifiers_for_autocomplete()))

        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories", None)
        for category in self.db.categories():
            self.category_filter.addItem(category, category)
        self.category_filter.currentIndexChanged.connect(self._refresh_items)

        self.availability_filter = QComboBox()
        self.availability_filter.addItem("Any availability", None)
        self.availability_filter.addItem("Available", True)
        self.availability_filter.addItem("Borrowed", False)
        self.availability_filter.currentIndexChanged.connect(self._refresh_items)

        filters.addWidget(self.search_edit, 1)
        filters.addWidget(self.category_filter)
        filters.addWidget(self.availability_filter)
        layout.addLayout(filters)

        self.item_table = QTableWidget(0, 6)
        self.item_table.setHorizontalHeaderLabels(
            ["ID", "Identifier", "Title", "Category", "Availability", "Image"]
        )
        self.item_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.item_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.item_table.setSortingEnabled(True)
        self.item_table.setAlternatingRowColors(True)
        layout.addWidget(self.item_table)

        action_bar = QHBoxLayout()
        self.btn_add = QPushButton("Add Item")
        self.btn_add.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.btn_add.clicked.connect(self._add_item)
        self.btn_edit = QPushButton("Edit Item")
        self.btn_edit.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_edit.clicked.connect(self._edit_item)
        self.btn_history = QPushButton("View Timeline")
        self.btn_history.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_history.clicked.connect(self._show_timeline)
        self.btn_qr = QPushButton("Generate QR")
        self.btn_qr.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_qr.clicked.connect(self._generate_qr)
        action_bar.addWidget(self.btn_add)
        action_bar.addWidget(self.btn_edit)
        action_bar.addWidget(self.btn_history)
        action_bar.addWidget(self.btn_qr)
        action_bar.addStretch(1)
        layout.addLayout(action_bar)
        return page

    def _gallery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setIconSize(QSize(100, 100))
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        layout.addWidget(QLabel("Item Image Gallery"))
        layout.addWidget(self.gallery)
        return page

    def _recommendations_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("AI-like Recommendations"))
        self.reco_list = QListWidget()
        layout.addWidget(self.reco_list)
        return page

    def _connect_services(self) -> None:
        self.backup_manager.backup_completed.connect(
            lambda path: self.status.showMessage(f"Backup created: {path}", 6000)
        )
        self.backup_manager.backup_failed.connect(
            lambda message: QMessageBox.critical(self, "Backup Failed", message)
        )

    def _apply_role_permissions(self) -> None:
        if self.current_user.role == UserRole.VIEWER:
            self.btn_add.setEnabled(False)
            self.btn_edit.setEnabled(False)
        if self.current_user.role == UserRole.STAFF:
            self.btn_add.setEnabled(True)

    def _switch_page(self, index: int) -> None:
        if not hasattr(self, "pages"):
            return
        self.pages.setCurrentIndex(index)

    def _toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        QApplication.instance().setStyleSheet(DARK_QSS if self.dark_mode else LIGHT_QSS)
        self.status.showMessage(f"{'Dark' if self.dark_mode else 'Light'} mode enabled", 2500)

    def _refresh_items(self) -> None:
        filters = {
            "query": self.search_edit.text().strip() if hasattr(self, "search_edit") else "",
            "category": self.category_filter.currentData() if hasattr(self, "category_filter") else None,
            "available": self.availability_filter.currentData() if hasattr(self, "availability_filter") else None,
        }
        rows = self.db.list_items(filters)
        self.item_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.item_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.item_table.setItem(i, 1, QTableWidgetItem(row["identifier"]))
            self.item_table.setItem(i, 2, QTableWidgetItem(row["title"]))
            self.item_table.setItem(i, 3, QTableWidgetItem(row["category"]))
            self.item_table.setItem(i, 4, QTableWidgetItem("Available" if row["available"] else "Borrowed"))
            self.item_table.setItem(i, 5, QTableWidgetItem(row["image_path"] or ""))
        self._refresh_gallery(rows)
        self._refresh_recommendations()

    def _refresh_gallery(self, rows: list) -> None:
        self.gallery.clear()
        for row in rows:
            image = row["image_path"]
            if image and Path(image).exists():
                item = QListWidgetItem(QIcon(image), row["title"])
                self.gallery.addItem(item)

    def _add_item(self) -> None:
        dialog = ItemEditorDialog()
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        try:
            self.db.upsert_item(actor_id=self.current_user.id, **payload)
            self._refresh_items()
            self.status.showMessage("Item added successfully", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Create failed", str(exc))

    def _edit_item(self) -> None:
        row = self.item_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select item", "Pick an item first.")
            return
        item_data = {
            "id": int(self.item_table.item(row, 0).text()),
            "identifier": self.item_table.item(row, 1).text(),
            "title": self.item_table.item(row, 2).text(),
            "category": self.item_table.item(row, 3).text(),
            "available": self.item_table.item(row, 4).text() == "Available",
            "image_path": self.item_table.item(row, 5).text(),
        }
        dialog = ItemEditorDialog(item_data)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        try:
            self.db.upsert_item(item_id=item_data["id"], actor_id=self.current_user.id, **payload)
            self._refresh_items()
            self.status.showMessage("Item updated", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Update failed", str(exc))

    def _selected_item_id(self) -> int | None:
        row = self.item_table.currentRow()
        if row < 0:
            return None
        return int(self.item_table.item(row, 0).text())

    def _show_timeline(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            return
        rows = [dict(x) for x in self.db.item_activity(item_id)]
        HistoryDialog(rows).exec()

    def _generate_qr(self) -> None:
        row = self.item_table.currentRow()
        if row < 0:
            return
        identifier = self.item_table.item(row, 1).text()
        path = self.qr_service.create_qr_for_identifier(identifier)
        self.status.showMessage(f"QR generated: {path}", 4000)

    def _refresh_dashboard(self) -> None:
        metrics = self.analytics_engine.inventory_health_metrics()
        self.metrics.setText(
            f"Total: {int(metrics['total_items'])} | Available: {int(metrics['available_items'])} | Utilization: {metrics['utilization_percent']}%"
        )
        df = self.analytics_engine.load_dataframe()
        fig = self.canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        if df.empty:
            ax.text(0.5, 0.5, "No analytics data yet", ha="center", va="center")
        else:
            trend = df.groupby(df["borrow_date"].dt.to_period("M")).size()
            trend.plot(ax=ax, marker="o")
            ax.set_title("Borrow Trends Over Time")
        fig.tight_layout()
        self.canvas.draw()

    def _refresh_recommendations(self) -> None:
        self.reco_list.clear()
        for item in self.recommendation_engine.recommend_items_for_user(self.current_user.id):
            self.reco_list.addItem(item)

    def _bulk_import(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV/Excel", "", "Data files (*.csv *.xlsx *.xls)"
        )
        if not file_path:
            return
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            required = {"identifier", "title", "category"}
            missing = required - set(df.columns)
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
            inserted = self.db.bulk_insert_items(df.to_dict(orient="records"), self.current_user.id)
            self.status.showMessage(f"Imported {inserted} items", 5000)
            self._refresh_items()
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def _export_excel(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "report.xlsx", "Excel (*.xlsx)")
        if not file_path:
            return
        rows = [dict(row) for row in self.db.list_items()]
        tx_rows = [dict(row) for row in self.db.analytics_dataframe()]
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Items", index=False)
            pd.DataFrame(tx_rows).to_excel(writer, sheet_name="Transactions", index=False)
        self.status.showMessage(f"Exported data to {file_path}", 4000)

    def _export_pdf(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "report.pdf", "PDF (*.pdf)")
        if not file_path:
            return
        try:
            output = self.reporting_service.generate_pdf_report(file_path)
            self.status.showMessage(f"PDF report created: {output}", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "PDF export failed", str(exc))

    def _notify_overdues(self) -> None:
        overdue = self.db.overdue_transactions()
        if not overdue:
            return
        QMessageBox.warning(self, "Overdue Alert", f"There are {len(overdue)} overdue transactions.")
