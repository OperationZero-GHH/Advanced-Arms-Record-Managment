from __future__ import annotations

import re


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9\-_]{3,64}$")


def validate_required(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required.")


def validate_identifier(identifier: str) -> None:
    validate_required(identifier, "Identifier")
    if not IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            "Identifier must be 3-64 chars and contain only letters, numbers, - or _."
        )


def validate_positive_amount(amount: float, field_name: str) -> None:
    if amount < 0:
        raise ValueError(f"{field_name} must be a positive number.")
