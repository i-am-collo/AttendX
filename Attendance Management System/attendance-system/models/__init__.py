"""
models/__init__.py
------------------
Lightweight domain-model dataclasses that wrap raw DB dicts.
Used optionally for type-safety in business logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    email: str
    role: str          # 'student' | 'lecturer'
    created_at: str

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            id=d["id"], username=d["username"],
            email=d["email"], role=d["role"], created_at=d["created_at"]
        )


@dataclass
class Lecturer:
    id: int
    user_id: int
    full_name: str
    department: str

    @classmethod
    def from_dict(cls, d: dict) -> "Lecturer":
        return cls(id=d["id"], user_id=d["user_id"],
                   full_name=d["full_name"], department=d.get("department", ""))


@dataclass
class Student:
    id: int
    user_id: int
    full_name: str
    student_id: str
    program: str

    @classmethod
    def from_dict(cls, d: dict) -> "Student":
        return cls(id=d["id"], user_id=d["user_id"], full_name=d["full_name"],
                   student_id=d["student_id"], program=d.get("program", ""))


@dataclass
class Subject:
    id: int
    subject_code: str
    name: str
    lecturer_id: int
    created_at: str

    @classmethod
    def from_dict(cls, d: dict) -> "Subject":
        return cls(id=d["id"], subject_code=d["subject_code"],
                   name=d["name"], lecturer_id=d["lecturer_id"],
                   created_at=d["created_at"])


@dataclass
class AttendanceSession:
    id: int
    subject_id: int
    title: str
    date: str
    start_time: str
    is_open: bool

    @classmethod
    def from_dict(cls, d: dict) -> "AttendanceSession":
        return cls(id=d["id"], subject_id=d["subject_id"],
                   title=d["title"], date=d["date"],
                   start_time=d["start_time"], is_open=bool(d["is_open"]))


@dataclass
class AttendanceRecord:
    id: int
    session_id: int
    student_id: int
    signed_at: str
    method: str = "manual"

    @classmethod
    def from_dict(cls, d: dict) -> "AttendanceRecord":
        return cls(id=d["id"], session_id=d["session_id"],
                   student_id=d["student_id"], signed_at=d["signed_at"],
                   method=d.get("method", "manual"))
