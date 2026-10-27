"""Argon2id authentication and bounded per-IP login throttling."""

import hashlib
import hmac
import re
import threading
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from server import config
from shared import validation

PASSWORD_HASHER = PasswordHasher()  # Maintained library's RFC 9106 low-memory profile.
_DUMMY_HASH = PASSWORD_HASHER.hash("unused dummy verification value")


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(stored: str, password: str) -> bool:
    if re.fullmatch(r"[0-9a-f]{64}", stored):
        # Compatibility only: successful login upgrades this hash transactionally.
        return hmac.compare_digest(stored, hashlib.sha256(password.encode()).hexdigest())
    try:
        return PASSWORD_HASHER.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


class AuthManager:
    def __init__(self, database):
        self.db = database
        self.lock = threading.Lock()
        self.attempts: dict[str, tuple[int, float]] = {}
        self.hash_slots = threading.BoundedSemaphore(config.AUTH_HASH_CONCURRENCY)

    def login(self, username: object, password: object, ip_address: str) -> dict:
        # Reserve an attempt before hashing so concurrent sockets cannot bypass the limit.
        now = time.monotonic()
        with self.lock:
            self.attempts = {
                ip: entry
                for ip, entry in self.attempts.items()
                if now - entry[1] < config.BLOCK_TIME
            }
            count, started = self.attempts.get(ip_address, (0, now))
            if (
                count >= config.MAX_LOGIN_ATTEMPTS
                or len(self.attempts) >= config.MAX_AUTH_TRACKED_IPS
            ):
                return {"success": False, "code": "RATE_LIMITED", "error": "Try again later"}
            self.attempts[ip_address] = (count + 1, started)
        try:
            username = validation.text(username, "Username", maximum=128)
            password = validation.password(password, new=False)
        except ValueError:
            return {"success": False, "code": "INVALID_CREDENTIALS", "error": "Invalid credentials"}
        if not self.hash_slots.acquire(blocking=False):
            return {"success": False, "code": "BUSY", "error": "Authentication busy; retry later"}
        try:
            row = self.db.get_user_by_username(username)
            valid = verify_password(row["password_hash"] if row else _DUMMY_HASH, password)
            if not valid or not row or row["is_blocked"]:
                return {
                    "success": False,
                    "code": "INVALID_CREDENTIALS",
                    "error": "Invalid credentials",
                }
            stored = row["password_hash"]
            if not stored.startswith("$argon2id$") or PASSWORD_HASHER.check_needs_rehash(stored):
                self.db.upgrade_password(row["id"], stored, hash_password(password))
            with self.lock:
                self.attempts.pop(ip_address, None)
            return {
                "success": True,
                "user_id": row["id"],
                "username": row["username"],
                "role": row["role"],
            }
        finally:
            self.hash_slots.release()
