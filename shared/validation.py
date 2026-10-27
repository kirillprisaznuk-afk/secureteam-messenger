"""Strict validation at the server boundary; bool is not an integer ID."""

import re

from shared.constants import MAX_MEMBERS, MESSAGE_MAX_LENGTH
from shared.models import Role


def text(value: object, label: str, minimum: int = 1, maximum: int = 100) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} must contain {minimum}–{maximum} characters")
    if not value.strip() or "\x00" in value:
        raise ValueError(f"Invalid {label.lower()}")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"Invalid {label.lower()} encoding") from exc
    return value


def username(value: object) -> str:
    value = text(value, "Username", 3, 32)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError("Username may contain letters, numbers, _, . and -")
    return value


def password(value: object, *, new: bool = True) -> str:
    return text(value, "Password", 12 if new else 1, 128)


def identifier(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise ValueError("Invalid identifier")
    return value


def role(value: object) -> str:
    if not isinstance(value, str) or value not in {r.value for r in Role}:
        raise ValueError("Invalid role")
    return value


def members(value: object) -> list[int]:
    if not isinstance(value, list) or len(value) > MAX_MEMBERS:
        raise ValueError(f"Members must be a list of at most {MAX_MEMBERS} user IDs")
    return sorted({identifier(item) for item in value})


def content(value: object) -> str:
    return text(value, "Message", maximum=MESSAGE_MAX_LENGTH)
