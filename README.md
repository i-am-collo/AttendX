# AttendX — Smart Attendance Management System

**A full-featured, dark-mode desktop application** built with Python, Tkinter, and SQLite.

---

## 📁 Project Structure

```
attendance-system/
├── main.py                     # Entry point
├── seed_demo.py                # One-time demo data seeder
├── requirements.txt
│
├── database/
│   ├── __init__.py
│   ├── schema.py               # Table definitions + DB init
│   └── queries.py              # All SQL operations
│
├── gui/
│   ├── __init__.py
│   ├── theme.py                # Color palette, fonts, ttk styles
│   ├── widgets.py              # Reusable components (Card, Badge, Toast, etc.)
│   ├── login_page.py           # Login window
│   ├── register_page.py        # Registration window (student + lecturer)
│   ├── lecturer_dashboard.py   # Full lecturer dashboard
│   ├── student_dashboard.py    # Student dashboard
│   └── create_session_page.py  # Session creation dialog
│
├── models/
│   └── __init__.py             # Domain dataclasses
│
├── utils/
│   ├── __init__.py
│   ├── auth.py                 # Password hashing, validation, session
│   ├── export.py               # Excel + PDF export
│   └── qr_code.py              # QR code generation
│
└── assets/                     # Icons / images (optional)
```

---

## ⚙️ Setup

### 1. Prerequisites
- Python 3.10 or higher
- `tkinter` (usually bundled with Python; on Ubuntu: `sudo apt install python3-tk`)

### 2. Install dependencies
```bash
cd attendance-system
pip install -r requirements.txt
```

### 3. Run the application
```bash
python main.py
```

### 4. (Optional) Load demo data
```bash
python seed_demo.py
```
This creates demo accounts you can log in with immediately:

| Role     | Username  | Password  |
|----------|-----------|-----------|
| Lecturer | dr_smith  | Password1 |
| Student  | alice_j   | Password1 |
| Student  | bob_k     | Password1 |
| Student  | carol_m   | Password1 |

---

## 🔄 Attendance Flow

```
1. Lecturer registers → creates a Subject (generates unique code e.g. SUB-A3X9K2PQ)
2. Student registers  → enters subject code → auto-enrolled
3. Lecturer dashboard shows enrolled students
4. Lecturer creates an Attendance Session → opens it
5. Session appears in Student dashboard
6. Student clicks "Sign Attendance"
7. Lecturer dashboard auto-refreshes every 2 seconds showing ✅ tick
```

---

## ✨ Features

### Authentication
- Secure password hashing (PBKDF2-HMAC-SHA256, 310,000 iterations)
- Role-based login (Student / Lecturer)
- Input validation (email, password strength, username format)

### Lecturer Features
- Create subjects with auto-generated unique codes
- Create attendance sessions (title, date, time)
- Open / close sessions
- **Live attendance table** (auto-refreshes every 2 seconds)
- Student roster with search/filter
- QR code generation per session
- Analytics tab (per-student attendance %)
- Export to **Excel (.xlsx)** and **PDF**
- Notification bell for student enrollments & sign-ins

### Student Features
- Enroll in a subject using the subject code
- View all open sessions in real-time
- One-click attendance signing
- Duplicate prevention (can only sign once per session)
- Full attendance history
- My Subjects tab

### UI / UX
- Dark mode throughout (deep violet + charcoal palette)
- Segoe UI typography, clean hierarchy
- ttk.Treeview tables with alternating row colors
- Badge chips (Open/Closed, Signed/Pending)
- Toast notifications (bottom status bar)
- Stat cards (KPI strip)
- Responsive frames, sidebar navigation

---

## 🔧 Configuration

All design tokens (colors, fonts, spacing) are in `gui/theme.py`.  
All SQL queries are in `database/queries.py` — easy to audit or extend.

---

## 📦 Dependencies

| Package    | Purpose           |
|------------|-------------------|
| openpyxl   | Excel export      |
| reportlab  | PDF export        |
| qrcode     | QR generation     |
| Pillow     | QR display in GUI |

All are pip-installable; no system libraries needed (except tkinter).

---

## 🗄️ Database Schema

SQLite file: `database/attendance.db` (auto-created on first run)

| Table                | Description                        |
|---------------------|------------------------------------|
| users               | Login credentials + role           |
| lecturers           | Lecturer profile                   |
| students            | Student profile + reg number       |
| subjects            | Subjects with unique codes         |
| student_subjects    | Enrollment (many-to-many)          |
| attendance_sessions | Sessions per subject               |
| attendance_records  | Signed records (unique per student)|
| notifications       | In-app notification feed           |
