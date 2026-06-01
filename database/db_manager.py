from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from database.models import User, UserRole
from utils.security import hash_password, verify_password
from utils.validators import validate_identifier, validate_required

LOGGER = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            self._apply_migrations(conn)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        migrations: list[tuple[int, str]] = [
            (
                1,
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','staff','viewer')),
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    available INTEGER NOT NULL DEFAULT 1,
                    image_path TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    borrowed_by INTEGER NOT NULL,
                    borrow_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    return_date TEXT,
                    fine_amount REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(item_id) REFERENCES items(id),
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(borrowed_by) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS item_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    notes TEXT,
                    created_by INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES items(id),
                    FOREIGN KEY(created_by) REFERENCES users(id)
                );
                """,
            ),
            (
                2,
                """
                CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
                CREATE INDEX IF NOT EXISTS idx_items_available ON items(available);
                CREATE INDEX IF NOT EXISTS idx_items_identifier ON items(identifier);
                CREATE INDEX IF NOT EXISTS idx_transactions_due_date ON transactions(due_date);
                CREATE INDEX IF NOT EXISTS idx_transactions_return_date ON transactions(return_date);
                CREATE INDEX IF NOT EXISTS idx_item_activity_item_created ON item_activity(item_id, created_at);
                """,
            ),
        ]
        for version, sql in migrations:
            if version in applied:
                continue
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.utcnow().isoformat()),
            )
            conn.commit()
            LOGGER.info("Applied migration %s", version)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            LOGGER.exception("Database transaction failed")
            raise
        finally:
            conn.close()

    def seed_default_users(self) -> None:
        with self.connection() as conn:
            existing = conn.execute("SELECT COUNT(*) as total FROM users").fetchone()["total"]
            if existing:
                return
            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT INTO users (username, full_name, role, password_hash, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("admin", "System Administrator", UserRole.ADMIN.value, hash_password("admin123"), 1, now),
            )
            conn.execute(
                """
                INSERT INTO users (username, full_name, role, password_hash, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("staff", "Default Staff", UserRole.STAFF.value, hash_password("staff123"), 1, now),
            )

    def authenticate(self, username: str, password: str) -> Optional[User]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id, username, full_name, role, password_hash, is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None or not row["is_active"]:
                return None
            if not verify_password(password, row["password_hash"]):
                return None
            return User(
                id=row["id"],
                username=row["username"],
                full_name=row["full_name"],
                role=UserRole(row["role"]),
                is_active=bool(row["is_active"]),
            )

    def list_items(self, filters: dict[str, Any] | None = None) -> list[sqlite3.Row]:
        filters = filters or {}
        clauses = []
        params: list[Any] = []
        if query := filters.get("query"):
            like = f"%{query}%"
            clauses.append("(title LIKE ? OR identifier LIKE ?)")
            params.extend([like, like])
        if category := filters.get("category"):
            clauses.append("category = ?")
            params.append(category)
        if "available" in filters and filters["available"] is not None:
            clauses.append("available = ?")
            params.append(1 if filters["available"] else 0)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT id, identifier, title, category, available, image_path, created_at
            FROM items
            {where_clause}
            ORDER BY created_at DESC
        """
        with self.connection() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def upsert_item(
        self,
        *,
        identifier: str,
        title: str,
        category: str,
        available: bool,
        image_path: str | None,
        actor_id: int,
        item_id: int | None = None,
    ) -> int:
        validate_identifier(identifier)
        validate_required(title, "Title")
        validate_required(category, "Category")
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            if item_id is None:
                cur = conn.execute(
                    """
                    INSERT INTO items (identifier, title, category, available, image_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (identifier, title, category, 1 if available else 0, image_path, now),
                )
                new_id = int(cur.lastrowid)
                self._log_item_activity(conn, new_id, "created", "Item created", actor_id)
                return new_id

            conn.execute(
                """
                UPDATE items
                SET identifier = ?, title = ?, category = ?, available = ?, image_path = ?
                WHERE id = ?
                """,
                (identifier, title, category, 1 if available else 0, image_path, item_id),
            )
            self._log_item_activity(conn, item_id, "updated", "Item updated", actor_id)
            return item_id

    def borrow_item(self, item_id: int, user_id: int, borrowed_by: int, due_date: str) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE items SET available = 0 WHERE id = ?", (item_id,))
            conn.execute(
                """
                INSERT INTO transactions (item_id, user_id, borrowed_by, borrow_date, due_date, return_date, fine_amount)
                VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (item_id, user_id, borrowed_by, datetime.utcnow().isoformat(), due_date),
            )
            self._log_item_activity(conn, item_id, "borrowed", f"Borrowed by user #{user_id}", borrowed_by)

    def return_item(self, transaction_id: int, per_day_fine: float = 1.5) -> float:
        with self.connection() as conn:
            tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
            if not tx or tx["return_date"] is not None:
                return 0.0
            due = datetime.fromisoformat(tx["due_date"])
            now = datetime.utcnow()
            overdue_days = max(0, (now.date() - due.date()).days)
            fine = float(overdue_days * per_day_fine)
            conn.execute(
                "UPDATE transactions SET return_date = ?, fine_amount = ? WHERE id = ?",
                (now.isoformat(), fine, transaction_id),
            )
            conn.execute("UPDATE items SET available = 1 WHERE id = ?", (tx["item_id"],))
            self._log_item_activity(conn, tx["item_id"], "returned", f"Fine applied: {fine:.2f}", tx["borrowed_by"])
            return fine

    def overdue_transactions(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT t.*, i.title, i.identifier, u.full_name
                FROM transactions t
                JOIN items i ON i.id = t.item_id
                JOIN users u ON u.id = t.user_id
                WHERE t.return_date IS NULL AND date(t.due_date) < date('now')
                ORDER BY t.due_date ASC
                """
            ).fetchall()

    def item_activity(self, item_id: int) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT a.action, a.notes, a.created_at, u.full_name as actor_name
                FROM item_activity a
                LEFT JOIN users u ON u.id = a.created_by
                WHERE a.item_id = ?
                ORDER BY a.created_at DESC
                """,
                (item_id,),
            ).fetchall()

    def analytics_dataframe(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT
                    t.id,
                    t.item_id,
                    t.user_id,
                    t.borrow_date,
                    t.due_date,
                    t.return_date,
                    t.fine_amount,
                    i.title,
                    i.category
                FROM transactions t
                JOIN items i ON i.id = t.item_id
                """
            ).fetchall()

    def categories(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT DISTINCT category FROM items ORDER BY category").fetchall()
            return [row["category"] for row in rows]

    def identifiers_for_autocomplete(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT identifier FROM items ORDER BY identifier").fetchall()
            return [row["identifier"] for row in rows]

    def bulk_insert_items(self, records: list[dict[str, Any]], actor_id: int) -> int:
        inserted = 0
        with self.connection() as conn:
            for record in records:
                try:
                    validate_identifier(record["identifier"])
                    validate_required(record["title"], "Title")
                    validate_required(record["category"], "Category")
                    cur = conn.execute(
                        """
                        INSERT INTO items (identifier, title, category, available, image_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record["identifier"],
                            record["title"],
                            record["category"],
                            1 if bool(record.get("available", True)) else 0,
                            record.get("image_path"),
                            datetime.utcnow().isoformat(),
                        ),
                    )
                    inserted += 1
                    self._log_item_activity(conn, int(cur.lastrowid), "bulk_import", "Imported via file", actor_id)
                except Exception as exc:
                    LOGGER.warning("Skipping invalid bulk row: %s", exc)
        return inserted

    def _log_item_activity(
        self, conn: sqlite3.Connection, item_id: int, action: str, notes: str, actor_id: int | None
    ) -> None:
        conn.execute(
            """
            INSERT INTO item_activity (item_id, action, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, action, notes, actor_id, datetime.utcnow().isoformat()),
        )
