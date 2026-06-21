"""
database/schema.py
------------------
Defines and initializes all SQLite tables for the Attendance Management System.
"""

import sqlite3
import os
import sys


def _get_app_data_dir() -> str:
    """Return a persistent, writable per-user directory for AttendX's data.

    Using a path relative to __file__ works fine while running from source,
    but breaks once the app is packaged into a standalone executable
    (PyInstaller, cx_Freeze, etc.): __file__ then resolves to a temporary
    extraction folder that is recreated empty and deleted on every launch,
    so the database would silently reset every time the app starts. This
    instead resolves to a real OS-standard per-user data folder that exists
    both in development and in a packaged build.
    """
    app_name = "AttendX"
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    path = os.path.join(base, app_name)
    os.makedirs(path, exist_ok=True)
    return path


DB_PATH = os.path.join(_get_app_data_dir(), "attendance.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── users ──────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,          -- bcrypt hash
            role        TEXT    NOT NULL CHECK(role IN ('student','lecturer')),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── lecturers ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lecturers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            full_name   TEXT    NOT NULL,
            department  TEXT    NOT NULL DEFAULT ''
        )
    """)

    # ── students ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            full_name   TEXT    NOT NULL,
            student_id  TEXT    NOT NULL UNIQUE,   -- e.g. STU-20240001
            program     TEXT    NOT NULL DEFAULT ''
        )
    """)

    # ── subjects ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT   NOT NULL UNIQUE,   -- lecturer-generated unique code
            name        TEXT    NOT NULL,
            lecturer_id INTEGER NOT NULL REFERENCES lecturers(id) ON DELETE CASCADE,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── student_subjects (enrollment) ─────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_subjects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            enrolled_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(student_id, subject_id)
        )
    """)

    # ── attendance_sessions ────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            date        TEXT    NOT NULL,           -- ISO date YYYY-MM-DD
            start_time  TEXT    NOT NULL,
            is_open     INTEGER NOT NULL DEFAULT 1, -- 1=open, 0=closed
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── attendance_records ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            signed_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            method      TEXT    NOT NULL DEFAULT 'manual', -- manual | qr
            UNIQUE(session_id, student_id)
        )
    """)

    # ── notifications ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message     TEXT    NOT NULL,
            is_read     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")
