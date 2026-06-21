"""
seed_demo.py
------------
Populates the database with demo lecturer, students, subject, and session data
so you can test the app immediately without manual registration.

Run once after first launch:
    python seed_demo.py

Demo credentials:
  Lecturer : username=dr_smith   password=Password1
  Student 1: username=alice_j    password=Password1
  Student 2: username=bob_k      password=Password1
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.schema import initialize_database
from database import queries
from utils.auth import hash_password
from datetime import date, datetime

initialize_database()


def seed():
    print("Seeding demo data...")

    pw = hash_password("Password1")

    # ── Lecturer ────────────────────────────────────────────────────────
    existing = queries.get_user_by_username("dr_smith")
    if existing:
        print("  Demo data already exists. Skipping.")
        return

    lec_uid = queries.create_user("dr_smith", "smith@university.edu", pw, "lecturer")
    lec_id  = queries.create_lecturer(lec_uid, "Dr. Alice Smith", "School of Computing")

    # ── Subject ─────────────────────────────────────────────────────────
    sub_code = "SUB-DEMO0001"
    if not queries.subject_code_exists(sub_code):
        sub_id = queries.create_subject(sub_code, "Introduction to Computer Science", lec_id)
    else:
        sub_id = queries.get_subject_by_code(sub_code)["id"]

    # ── Students ─────────────────────────────────────────────────────────
    for uname, email, fname, program in [
        ("alice_j",  "alice@student.edu",  "Alice Johnson",  "BSc Computer Science"),
        ("bob_k",    "bob@student.edu",    "Bob Kariuki",    "BSc Software Engineering"),
        ("carol_m",  "carol@student.edu",  "Carol Mwangi",   "BSc Information Technology"),
    ]:
        if queries.get_user_by_username(uname):
            continue
        uid = queries.create_user(uname, email, pw, "student")
        stu_id = queries.create_student(uid, fname, f"STU-2024{uid:04d}", program)
        queries.enroll_student(stu_id, sub_id)
        print(f"  Created student: {uname}")

    # ── Session ──────────────────────────────────────────────────────────
    today = date.today().strftime("%Y-%m-%d")
    now   = datetime.now().strftime("%H:%M")
    sess_id = queries.create_session(sub_id, "Week 1 — Introduction", today, now)
    print(f"  Created open session id={sess_id}")

    print("\n✅ Demo seeding complete!")
    print("─" * 50)
    print("  Lecturer : dr_smith     / Password1")
    print("  Student 1: alice_j      / Password1")
    print("  Student 2: bob_k        / Password1")
    print("  Student 3: carol_m      / Password1")
    print(f"  Subject code: {sub_code}")
    print("─" * 50)


if __name__ == "__main__":
    seed()
