"""
database/queries.py
-------------------
All database query functions, organized by entity.
Every function returns plain dicts / lists-of-dicts for easy use in the GUI layer.
"""

from __future__ import annotations
import sqlite3
from typing import Optional
from database.schema import get_connection


# ═══════════════════════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════════════════════

def create_user(username: str, email: str, hashed_password: str, role: str) -> int:
    """Insert a user row and return the new user id."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
            (username, email, hashed_password, role)
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════════════════════
#  LECTURERS
# ═══════════════════════════════════════════════════════════════════════════════

def create_lecturer(user_id: int, full_name: str, department: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO lecturers (user_id, full_name, department) VALUES (?,?,?)",
            (user_id, full_name, department)
        )
        return cur.lastrowid


def get_lecturer_by_user_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM lecturers WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENTS
# ═══════════════════════════════════════════════════════════════════════════════

def create_student(user_id: int, full_name: str, student_id: str, program: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO students (user_id, full_name, student_id, program) VALUES (?,?,?,?)",
            (user_id, full_name, student_id, program)
        )
        return cur.lastrowid


def get_student_by_user_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_id_exists(student_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    conn.close()
    return row is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  SUBJECTS
# ═══════════════════════════════════════════════════════════════════════════════

def create_subject(subject_code: str, name: str, lecturer_id: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO subjects (subject_code, name, lecturer_id) VALUES (?,?,?)",
            (subject_code, name, lecturer_id)
        )
        return cur.lastrowid


def get_subject_by_code(code: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM subjects WHERE subject_code = ?", (code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_subjects_by_lecturer(lecturer_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM subjects WHERE lecturer_id = ? ORDER BY created_at DESC",
        (lecturer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def subject_code_exists(code: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM subjects WHERE subject_code = ?", (code,)
    ).fetchone()
    conn.close()
    return row is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  ENROLLMENT  (student_subjects)
# ═══════════════════════════════════════════════════════════════════════════════

def enroll_student(student_id: int, subject_id: int):
    """Enroll student in a subject (ignore if already enrolled)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO student_subjects (student_id, subject_id) VALUES (?,?)",
            (student_id, subject_id)
        )


def get_students_in_subject(subject_id: int) -> list[dict]:
    """Return all students enrolled in a subject with full details."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.full_name, s.student_id, s.program,
               ss.enrolled_at
        FROM   student_subjects ss
        JOIN   students s ON s.id = ss.student_id
        WHERE  ss.subject_id = ?
        ORDER  BY s.full_name
    """, (subject_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_subjects_for_student(student_id: int) -> list[dict]:
    """Return subjects a student is enrolled in, with lecturer name."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT sub.id, sub.subject_code, sub.name,
               l.full_name AS lecturer_name, l.department,
               ss.enrolled_at
        FROM   student_subjects ss
        JOIN   subjects sub ON sub.id = ss.subject_id
        JOIN   lecturers l  ON l.id  = sub.lecturer_id
        WHERE  ss.student_id = ?
        ORDER  BY sub.name
    """, (student_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_student_enrolled(student_id: int, subject_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM student_subjects WHERE student_id=? AND subject_id=?",
        (student_id, subject_id)
    ).fetchone()
    conn.close()
    return row is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE SESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_session(subject_id: int, title: str, date: str, start_time: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO attendance_sessions (subject_id, title, date, start_time) VALUES (?,?,?,?)",
            (subject_id, title, date, start_time)
        )
        return cur.lastrowid


def get_sessions_by_subject(subject_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM attendance_sessions WHERE subject_id=? ORDER BY created_at DESC",
        (subject_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_by_id(session_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM attendance_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def toggle_session(session_id: int, is_open: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE attendance_sessions SET is_open=? WHERE id=?",
            (1 if is_open else 0, session_id)
        )


def get_open_sessions_for_student(student_id: int) -> list[dict]:
    """Open sessions for subjects the student is enrolled in."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT  ats.id, ats.title, ats.date, ats.start_time,
                sub.name AS subject_name, sub.subject_code,
                l.full_name AS lecturer_name,
                CASE WHEN ar.id IS NOT NULL THEN 1 ELSE 0 END AS already_signed
        FROM    attendance_sessions ats
        JOIN    subjects sub ON sub.id = ats.subject_id
        JOIN    lecturers l  ON l.id  = sub.lecturer_id
        JOIN    student_subjects ss ON ss.subject_id = sub.id AND ss.student_id = ?
        LEFT JOIN attendance_records ar ON ar.session_id = ats.id AND ar.student_id = ?
        WHERE   ats.is_open = 1
        ORDER   BY ats.created_at DESC
    """, (student_id, student_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sessions_for_student(student_id: int) -> list[dict]:
    """All sessions (open & closed) for student's subjects."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT  ats.id, ats.title, ats.date, ats.start_time, ats.is_open,
                sub.name AS subject_name, sub.subject_code,
                CASE WHEN ar.id IS NOT NULL THEN 1 ELSE 0 END AS signed
        FROM    attendance_sessions ats
        JOIN    subjects sub ON sub.id = ats.subject_id
        JOIN    student_subjects ss ON ss.subject_id = sub.id AND ss.student_id = ?
        LEFT JOIN attendance_records ar ON ar.session_id = ats.id AND ar.student_id = ?
        ORDER   BY ats.created_at DESC
    """, (student_id, student_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE RECORDS
# ═══════════════════════════════════════════════════════════════════════════════

def sign_attendance(session_id: int, student_id: int, method: str = "manual") -> bool:
    """Sign attendance. Returns False if already signed."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO attendance_records (session_id, student_id, method) VALUES (?,?,?)",
                (session_id, student_id, method)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def has_signed(session_id: int, student_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM attendance_records WHERE session_id=? AND student_id=?",
        (session_id, student_id)
    ).fetchone()
    conn.close()
    return row is not None


def get_session_attendance(session_id: int) -> list[dict]:
    """Return all signed records for a session."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT  ar.id, ar.signed_at, ar.method,
                s.full_name, s.student_id AS reg_no, s.program
        FROM    attendance_records ar
        JOIN    students s ON s.id = ar.student_id
        WHERE   ar.session_id = ?
        ORDER   BY ar.signed_at
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_attendance_history(student_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT  ar.signed_at, ar.method,
                ats.title AS session_title, ats.date, ats.start_time,
                sub.name AS subject_name, sub.subject_code
        FROM    attendance_records ar
        JOIN    attendance_sessions ats ON ats.id = ar.session_id
        JOIN    subjects sub ON sub.id = ats.subject_id
        WHERE   ar.student_id = ?
        ORDER   BY ar.signed_at DESC
    """, (student_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_stats_for_subject(subject_id: int) -> dict:
    """Return per-student attendance counts for a subject."""
    conn = get_connection()
    total_sessions = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance_sessions WHERE subject_id=?",
        (subject_id,)
    ).fetchone()["c"]

    rows = conn.execute("""
        SELECT  s.full_name, s.student_id AS reg_no,
                COUNT(ar.id) AS attended
        FROM    student_subjects ss
        JOIN    students s  ON s.id = ss.student_id
        LEFT JOIN attendance_records ar ON ar.student_id = s.id
            AND ar.session_id IN (
                SELECT id FROM attendance_sessions WHERE subject_id = ?
            )
        WHERE   ss.subject_id = ?
        GROUP   BY s.id
        ORDER   BY s.full_name
    """, (subject_id, subject_id)).fetchall()
    conn.close()
    return {"total_sessions": total_sessions, "records": [dict(r) for r in rows]}


# ═══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def add_notification(user_id: int, message: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, message) VALUES (?,?)",
            (user_id, message)
        )


def get_notifications(user_id: int, unread_only: bool = False) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM notifications WHERE user_id=?"
    if unread_only:
        query += " AND is_read=0"
    query += " ORDER BY created_at DESC LIMIT 50"
    rows = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notifications_read(user_id: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,)
        )


def unread_count(user_id: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id=? AND is_read=0",
        (user_id,)
    ).fetchone()
    conn.close()
    return row["c"]
