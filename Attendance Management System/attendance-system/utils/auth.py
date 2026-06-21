"""
utils/auth.py
-------------
Authentication helpers: password hashing (bcrypt), session management,
input validation, and unique ID / code generation.
"""

import hashlib
import os
import re
import uuid
import string
import random
from datetime import datetime


# ── Password Hashing (using hashlib PBKDF2 — no external dependency needed) ──

def hash_password(password: str) -> str:
    """Return a salted PBKDF2-HMAC-SHA256 hash string."""
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key  = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return key.hex() == key_hex
    except Exception:
        return False


# ── Unique ID Generators ────────────────────────────────────────────────────

def generate_subject_code() -> str:
    """Generate a random 8-character alphanumeric subject code, e.g. SUB-A3X9K2PQ"""
    chars   = string.ascii_uppercase + string.digits
    suffix  = "".join(random.choices(chars, k=8))
    return f"SUB-{suffix}"


def generate_student_number() -> str:
    """Generate a student registration number, e.g. STU-20240001"""
    year    = datetime.now().year
    suffix  = random.randint(1000, 9999)
    return f"STU-{year}{suffix}"


# ── Input Validation ────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    pattern = r"^[\w.\-+]+@[\w\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Returns (is_valid, message).
    Requires: 8+ chars, at least one digit, one uppercase, one lowercase.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    return True, "OK"


def validate_username(username: str) -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores."
    return True, "OK"


# ── Simple Session Store (in-memory, single-user per instance) ──────────────

class Session:
    """Lightweight in-memory session — holds logged-in user info."""
    _current: dict | None = None

    @classmethod
    def login(cls, user: dict, profile: dict):
        cls._current = {"user": user, "profile": profile}

    @classmethod
    def logout(cls):
        cls._current = None

    @classmethod
    def get(cls) -> dict | None:
        return cls._current

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._current is not None

    @classmethod
    def user(cls) -> dict | None:
        return cls._current["user"] if cls._current else None

    @classmethod
    def profile(cls) -> dict | None:
        return cls._current["profile"] if cls._current else None

    @classmethod
    def role(cls) -> str | None:
        return cls._current["user"]["role"] if cls._current else None
