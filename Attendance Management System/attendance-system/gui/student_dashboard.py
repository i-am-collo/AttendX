"""
gui/student_dashboard.py
------------------------
Student dashboard: view open sessions, sign attendance, view history.
Auto-refreshes every 2 seconds.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

import gui.theme as T
from gui.widgets import (
    center_window, IconButton, build_treeview, populate_tree,
    StatCard, Badge, Toast
)
from database import queries
from utils.auth import Session


class StudentDashboard(tk.Toplevel):
    """Main window for a logged-in student."""

    AUTO_REFRESH_MS = 2000

    def __init__(self, parent, on_close_cb=None):
        super().__init__(parent)
        self.title("AttendX — Student Dashboard")
        self.configure(bg=T.BG_DARK)
        self._on_close_cb = on_close_cb
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        center_window(self, 1050, 720)

        self._user    = Session.user()
        self._profile = Session.profile()   # students row
        self._open_sessions: list[dict] = []
        self._refresh_after_id = None
        self._done = False

        self._build()
        self._start_refresh()

    # ══════════════════════════════════════════════════════════════════════
    #  LAYOUT
    # ══════════════════════════════════════════════════════════════════════

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=T.BG_DEEP, height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="🎓  AttendX", bg=T.BG_DEEP,
                 fg=T.ACCENT_LIGHT, font=T.FONT_H2).pack(side="left", padx=T.PAD_LG)
        tk.Label(topbar, text="Student Portal", bg=T.BG_DEEP,
                 fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(side="left")

        IconButton(topbar, "Logout", command=self._on_close,
                   bg=T.DANGER, hover_bg="#DC2626",
                   font=T.FONT_SMALL).pack(side="right", padx=T.PAD_SM)
        tk.Label(topbar,
                 text=f"👤  {self._profile['full_name']}  |  {self._profile['student_id']}",
                 bg=T.BG_DEEP, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(side="right", padx=T.PAD_MD)

        # ── Stat strip ────────────────────────────────────────────────────
        stat_bar = tk.Frame(self, bg=T.BG_DARK, padx=T.PAD_MD, pady=T.PAD_SM)
        stat_bar.pack(fill="x")

        self._stat_subjects  = StatCard(stat_bar, "📚", "0", "Subjects")
        self._stat_open      = StatCard(stat_bar, "🟢", "0", "Open Sessions")
        self._stat_signed    = StatCard(stat_bar, "✅", "0", "Signed Today")
        self._stat_total     = StatCard(stat_bar, "📋", "0", "Total Signed")

        for sc in (self._stat_subjects, self._stat_open,
                   self._stat_signed, self._stat_total):
            sc.pack(side="left", padx=(0, T.PAD_SM), ipadx=T.PAD_SM)

        # ── Notebook ──────────────────────────────────────────────────────
        nb = ttk.Notebook(self, style=T.STYLE_NOTEBOOK)
        nb.pack(fill="both", expand=True, padx=T.PAD_MD, pady=(0, T.PAD_SM))

        # Tab 1 – Open sessions (sign now)
        tab_open = tk.Frame(nb, bg=T.BG_DARK)
        nb.add(tab_open, text="  🟢  Open Sessions  ")
        self._build_open_sessions_tab(tab_open)

        # Tab 2 – All attendance history
        tab_hist = tk.Frame(nb, bg=T.BG_DARK)
        nb.add(tab_hist, text="  📋  My Attendance  ")
        self._build_history_tab(tab_hist)

        # Tab 3 – My subjects
        tab_subj = tk.Frame(nb, bg=T.BG_DARK)
        nb.add(tab_subj, text="  📚  My Subjects  ")
        self._build_subjects_tab(tab_subj)

        self._toast = Toast(self)

    # ── Open Sessions tab ─────────────────────────────────────────────────

    def _build_open_sessions_tab(self, parent):
        hdr = tk.Frame(parent, bg=T.BG_DARK)
        hdr.pack(fill="x", padx=T.PAD_SM, pady=(T.PAD_SM, 0))
        tk.Label(hdr, text="Open Attendance Sessions",
                bg=T.BG_DARK, fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(side="left")
        self._refresh_lbl = tk.Label(hdr, text="⟳ live",
                                    bg=T.BG_DARK, fg=T.SUCCESS, font=T.FONT_SMALL)
        self._refresh_lbl.pack(side="right")

        cols = [
            {"id": "no",       "text": "#",           "width": 40,  "anchor": "center"},
            {"id": "subject",  "text": "Subject",     "width": 200},
            {"id": "title",    "text": "Session",     "width": 180},
            {"id": "date",     "text": "Date",        "width": 100, "anchor": "center"},
            {"id": "time",     "text": "Time",        "width": 80,  "anchor": "center"},
            {"id": "lecturer", "text": "Lecturer",    "width": 160},
            {"id": "status",   "text": "Your Status", "width": 110, "anchor": "center"},
        ]
        frm = tk.Frame(parent, bg=T.BG_DARK)
        frm.pack(fill="both", expand=True, padx=T.PAD_SM, pady=T.PAD_SM)
        self._open_tree = build_treeview(frm, cols, height=16)
        self._open_tree.bind("<Double-1>", lambda _: self._sign_selected())

        btn_row = tk.Frame(parent, bg=T.BG_DARK)
        btn_row.pack(fill="x", padx=T.PAD_SM, pady=(0, T.PAD_SM))
        IconButton(btn_row, "✅  Sign Attendance",
                   command=self._sign_selected,
                   bg=T.SUCCESS, hover_bg="#059669",
                   font=T.FONT_H3).pack(side="left", ipady=3)
        tk.Label(btn_row,
                 text="  Double-click or select a row and press Sign",
                 bg=T.BG_DARK, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(side="left")

    # ── Attendance history tab ─────────────────────────────────────────────

    def _build_history_tab(self, parent):
        hdr = tk.Frame(parent, bg=T.BG_DARK)
        hdr.pack(fill="x", padx=T.PAD_SM, pady=(T.PAD_SM, 0))
        tk.Label(hdr, text="My Attendance History", bg=T.BG_DARK, fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(side="left")

        sf = tk.Frame(parent, bg=T.BG_DARK, padx=T.PAD_SM)
        sf.pack(fill="x")
        tk.Label(sf, text="🔍", bg=T.BG_DARK, fg=T.TEXT_MUTED).pack(side="left")
        self._hist_search = tk.StringVar()
        self._hist_search.trace_add("write", lambda *_: self._refresh_history())
        ttk.Entry(sf, textvariable=self._hist_search, style="TEntry").pack(side="left", fill="x", expand=True, padx=4)

        cols = [
            {"id": "no",      "text": "#",          "width": 40,  "anchor": "center"},
            {"id": "subject", "text": "Subject",    "width": 200},
            {"id": "session", "text": "Session",    "width": 180},
            {"id": "date",    "text": "Date",       "width": 100, "anchor": "center"},
            {"id": "time",    "text": "Start Time", "width": 80,  "anchor": "center"},
            {"id": "signed",  "text": "Signed At",  "width": 160},
            {"id": "method",  "text": "Method",     "width": 80,  "anchor": "center"},
        ]
        frm = tk.Frame(parent, bg=T.BG_DARK)
        frm.pack(fill="both", expand=True, padx=T.PAD_SM, pady=T.PAD_SM)
        self._hist_tree = build_treeview(frm, cols, height=18)

    # ── Subjects tab ───────────────────────────────────────────────────────

    def _build_subjects_tab(self, parent):
        hdr = tk.Frame(parent, bg=T.BG_DARK)
        hdr.pack(fill="x", padx=T.PAD_SM, pady=(T.PAD_SM, 0))
        tk.Label(hdr, text="My Enrolled Subjects", bg=T.BG_DARK, fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(side="left")

        cols = [
            {"id": "no",       "text": "#",          "width": 40, "anchor": "center"},
            {"id": "code",     "text": "Code",       "width": 130},
            {"id": "name",     "text": "Subject",    "width": 220},
            {"id": "lecturer", "text": "Lecturer",   "width": 180},
            {"id": "dept",     "text": "Department", "width": 200},
            {"id": "enrolled", "text": "Enrolled On","width": 120},
        ]
        frm = tk.Frame(parent, bg=T.BG_DARK)
        frm.pack(fill="both", expand=True, padx=T.PAD_SM, pady=T.PAD_SM)
        self._subj_tree = build_treeview(frm, cols, height=18)

    # ══════════════════════════════════════════════════════════════════════
    #  DATA REFRESHERS
    # ══════════════════════════════════════════════════════════════════════

    def _refresh_open_sessions(self):
        self._open_sessions = queries.get_open_sessions_for_student(self._profile["id"])
        rows = []
        for i, s in enumerate(self._open_sessions, 1):
            status = "✅ Signed" if s["already_signed"] else "⏳ Pending"
            rows.append([
                i, s["subject_name"], s["title"],
                s["date"], s["start_time"], s["lecturer_name"], status
            ])
        populate_tree(self._open_tree, rows)

    def _refresh_history(self):
        records = queries.get_student_attendance_history(self._profile["id"])
        search  = self._hist_search.get().lower()
        rows    = []
        for i, r in enumerate(records, 1):
            if search and search not in r["subject_name"].lower() \
                       and search not in r["session_title"].lower():
                continue
            rows.append([
                i, r["subject_name"], r["session_title"],
                r["date"], r["start_time"],
                r["signed_at"], r["method"].capitalize()
            ])
        populate_tree(self._hist_tree, rows)

    def _refresh_subjects(self):
        subjects = queries.get_subjects_for_student(self._profile["id"])
        rows = []
        for i, s in enumerate(subjects, 1):
            rows.append([
                i, s["subject_code"], s["name"],
                s["lecturer_name"], s["department"],
                s["enrolled_at"][:10]
            ])
        populate_tree(self._subj_tree, rows)

    def _refresh_stats(self):
        subjects      = queries.get_subjects_for_student(self._profile["id"])
        open_sessions = queries.get_open_sessions_for_student(self._profile["id"])
        all_sessions  = queries.get_all_sessions_for_student(self._profile["id"])
        signed_total  = sum(1 for s in all_sessions if s.get("signed"))

        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        signed_today = sum(
            1 for s in all_sessions
            if s.get("signed") and s["date"] == today
        )

        self._stat_subjects.update_value(str(len(subjects)))
        self._stat_open.update_value(str(len([s for s in open_sessions if not s["already_signed"]])))
        self._stat_signed.update_value(str(signed_today))
        self._stat_total.update_value(str(signed_total))

    # ── Auto-refresh ──────────────────────────────────────────────────────

    def _start_refresh(self):
        self._do_refresh()

    def _do_refresh(self):
        if self._done:
            return
        try:
            self._refresh_open_sessions()
            self._refresh_history()
            self._refresh_subjects()
            self._refresh_stats()
        except Exception:
            pass
        self._refresh_after_id = self.after(self.AUTO_REFRESH_MS, self._do_refresh)

    # ══════════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════════════════════════════════

    def _sign_selected(self):
        sel = self._open_tree.selection()
        if not sel:
            messagebox.showinfo("Select Session", "Please select a session to sign.", parent=self)
            return
        idx = self._open_tree.index(sel[0])
        if idx >= len(self._open_sessions):
            return
        session = self._open_sessions[idx]

        if session["already_signed"]:
            messagebox.showinfo("Already Signed",
                                "You have already signed this session! ✅", parent=self)
            return

        # Confirm
        resp = messagebox.askyesno(
            "Sign Attendance",
            f"Sign attendance for:\n\n"
            f"Subject: {session['subject_name']}\n"
            f"Session: {session['title']}\n"
            f"Date: {session['date']} {session['start_time']}\n\n"
            f"Confirm?",
            parent=self
        )
        if not resp:
            return

        # Re-check session is still open
        sess_db = queries.get_session_by_id(session["id"])
        if not sess_db or not sess_db["is_open"]:
            messagebox.showerror("Session Closed",
                                 "This session has been closed by the lecturer.", parent=self)
            return

        success = queries.sign_attendance(session["id"], self._profile["id"])
        if success:
            self._toast.show("✅ Attendance signed successfully!", "success")
            # Notify lecturer
            from database.queries import get_connection
            conn = get_connection()
            row = conn.execute("""
                SELECT u.id FROM subjects sub
                JOIN lecturers l ON l.id = sub.lecturer_id
                JOIN users u ON u.id = l.user_id
                WHERE sub.id = ?
            """, (session["id"] if "subject_id" not in session else None,)).fetchone()
            # simpler: find via subject_code
            conn2 = get_connection()
            row2 = conn2.execute("""
                SELECT u.id AS uid FROM attendance_sessions ats
                JOIN subjects sub ON sub.id = ats.subject_id
                JOIN lecturers l ON l.id = sub.lecturer_id
                JOIN users u ON u.id = l.user_id
                WHERE ats.id = ?
            """, (session["id"],)).fetchone()
            conn2.close()
            if row2:
                from database.queries import add_notification
                add_notification(
                    row2["uid"],
                    f"{self._profile['full_name']} signed attendance for '{session['title']}'"
                )
        else:
            messagebox.showerror("Error", "Failed to sign attendance (already signed or session closed).", parent=self)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _on_close(self):
        self._done = True
        if self._refresh_after_id:
            self.after_cancel(self._refresh_after_id)
        self.destroy()
        if self._on_close_cb:
            self._on_close_cb()
