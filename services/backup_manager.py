from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from utils.file_utils import safe_copy

LOGGER = logging.getLogger(__name__)


class BackupManager(QObject):
    backup_completed = pyqtSignal(str)
    backup_failed = pyqtSignal(str)

    def __init__(self, db_path: str, backup_dir: str) -> None:
        super().__init__()
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_backup_async)

    def schedule(self, interval_minutes: int = 30) -> None:
        self.timer.start(interval_minutes * 60 * 1000)

    def run_backup_async(self) -> None:
        thread = threading.Thread(target=self._run_backup, daemon=True)
        thread.start()

    def _run_backup(self) -> None:
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"records_backup_{stamp}.db"
            result = safe_copy(self.db_path, self.backup_dir, backup_name)
            self.backup_completed.emit(str(result))
        except Exception as exc:
            LOGGER.exception("Backup failed")
            self.backup_failed.emit(str(exc))
