from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"


@dataclass(slots=True)
class User:
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool = True


@dataclass(slots=True)
class Item:
    id: int
    identifier: str
    title: str
    category: str
    available: bool
    image_path: Optional[str]
    created_at: datetime


@dataclass(slots=True)
class BorrowTransaction:
    id: int
    item_id: int
    user_id: int
    borrowed_by: int
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    fine_amount: float
