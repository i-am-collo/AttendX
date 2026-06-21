"""
gui/register_page.py
--------------------
Registration window for both Students and Lecturers.

Fixes applied vs original:
  1. Password/Confirm fields use plain ttk.Entry(show="●") — no placeholder
     on masked fields (placeholder text appeared as dots).
  2. Department field is now validated (cannot be empty).
  3. Removed the leftover `lecturer = queries.get_connection()` noise line.
  4. Window resizable=True with a scrollable inner frame so it never clips
     on smaller screens.
  5. Subject code input auto-uppercases on every keystroke.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import gui.theme as T
from gui.widgets import center_window, IconButton, LabelledEntry
from database import queries
from database.schema import get_connection
from utils.auth import (
    hash_password, validate_email, validate_password_strength,
    validate_username, generate_student_number,
)


class RegisterPage(tk.Toplevel):
    """Modal registration window."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("AttendX — Create Account")
        self.configure(bg=T.BG_DARK)
        self.resizable(True, True)
        center_window(self, 500, 700)
        self.minsize(460, 620)
        self.grab_set()
        self.focus_set()

        self._role = tk.StringVar(value="student")
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        # Scrollable canvas so the form never gets clipped
        canvas = tk.Canvas(self, bg=T.BG_DARK, highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical",
                               command=canvas.yview, style=T.STYLE_SCROLLBAR)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas, bg=T.BG_DARK)
        win_id = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=event.width)

        self._inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", _on_configure)

        def _on_mousewheel(e):
            if canvas.winfo_exists():  # Check if canvas still exists
                canvas.yview_scroll(int(-1*(e.delta/120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)

        self._build_form(self._inner)

    def _build_form(self, outer_frame):
        outer = tk.Frame(outer_frame, bg=T.BG_DARK, padx=T.PAD_XL, pady=T.PAD_LG)
        outer.pack(fill="both", expand=True)

        # ── Header ──────────────────────────────────────────────────────
        tk.Label(outer, text="Create Account", bg=T.BG_DARK,
                fg=T.TEXT_PRIMARY, font=T.FONT_H1).pack(anchor="w")
        tk.Label(outer, text="Register to access AttendX", bg=T.BG_DARK, fg=T.TEXT_SECONDARY,
                font=T.FONT_SMALL).pack(anchor="w", pady=(2, T.PAD_MD))

        # ── Role selector ────────────────────────────────────────────────
        role_frame = tk.Frame(outer, bg=T.BG_CARD,
                            highlightbackground=T.BORDER, highlightthickness=1,
                            padx=T.PAD_MD, pady=T.PAD_SM)
        role_frame.pack(fill="x", pady=(0, T.PAD_MD))
        tk.Label(role_frame, text="I am a:", bg=T.BG_CARD,
                fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        btn_row = tk.Frame(role_frame, bg=T.BG_CARD)
        btn_row.pack(fill="x", pady=(4, 0))
        for val, label in (("student", "🎒  Student"), ("lecturer", "🧑‍🏫  Lecturer")):
            tk.Radiobutton(
                btn_row, text=label, variable=self._role, value=val,
                bg=T.BG_CARD, fg=T.TEXT_PRIMARY, selectcolor=T.ACCENT,
                activebackground=T.BG_CARD, activeforeground=T.TEXT_PRIMARY,
                font=T.FONT_BODY, cursor="hand2",
                command=self._on_role_change,
            ).pack(side="left", padx=(0, T.PAD_LG))

        # ── Form card ────────────────────────────────────────────────────
        card = tk.Frame(outer, bg=T.BG_CARD,
                        highlightbackground=T.BORDER, highlightthickness=1,
                        padx=T.PAD_LG, pady=T.PAD_LG)
        card.pack(fill="x")

        # Common fields
        self._full_name = LabelledEntry(card, "Full Name *",
                                        placeholder="e.g. John Doe")
        self._full_name.config(bg=T.BG_CARD)
        self._full_name.pack(fill="x", pady=(0, T.PAD_SM))

        self._username_e = LabelledEntry(card, "Username *", placeholder="Letters, numbers, underscore")
        self._username_e.config(bg=T.BG_CARD)
        self._username_e.pack(fill="x", pady=(0, T.PAD_SM))

        self._email_e = LabelledEntry(card, "Email *", placeholder="you@example.com")
        self._email_e.config(bg=T.BG_CARD)
        self._email_e.pack(fill="x", pady=(0, T.PAD_SM))

        # ── Dynamic role fields container ────────────────────────────────
        self._role_frame = tk.Frame(card, bg=T.BG_CARD)
        self._role_frame.pack(fill="x")

        # ── Password fields (plain Entry — no placeholder on masked) ────
        tk.Label(card, text="Password *  (min 8 chars, 1 uppercase, 1 digit)",
                 bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                 font=T.FONT_SMALL).pack(anchor="w", pady=(T.PAD_SM, 0))
        self._pw_var = tk.StringVar()
        ttk.Entry(card, textvariable=self._pw_var, show="●",
                  style="TEntry", font=T.FONT_BODY).pack(fill="x", pady=(2, T.PAD_SM))

        tk.Label(card, text="Confirm Password *",
                 bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                 font=T.FONT_SMALL).pack(anchor="w")
        self._cf_var = tk.StringVar()
        ttk.Entry(card, textvariable=self._cf_var, show="●",
                  style="TEntry", font=T.FONT_BODY).pack(fill="x", pady=(2, 0))

        # Error message
        self._error_var = tk.StringVar()
        tk.Label(card, textvariable=self._error_var,
                 bg=T.BG_CARD, fg=T.DANGER,
                 font=T.FONT_SMALL, wraplength=420,
                 justify="left").pack(fill="x", pady=(T.PAD_SM, 0))

        # Submit
        IconButton(card, "  Create Account  →",
                   command=self._on_register,
                   font=T.FONT_H3).pack(fill="x", ipady=4,
                                        pady=(T.PAD_SM, 0))

        # Back link
        tk.Button(outer, text="← Back to login",
                  bg=T.BG_DARK, fg=T.TEXT_SECONDARY,
                  font=T.FONT_SMALL, relief="flat", bd=0,
                  cursor="hand2", command=self.destroy).pack(pady=(T.PAD_SM, T.PAD_MD))

        # Build initial role-specific fields
        self._build_student_fields()
        self.bind("<Return>", lambda _: self._on_register())

    # ── Role-specific fields ────────────────────────────────────────────────

    def _build_student_fields(self):
        for w in self._role_frame.winfo_children():
            w.destroy()

        self._program_e = LabelledEntry(self._role_frame, "Program / Course *",
                                        placeholder="e.g. BSc Computer Science")
        self._program_e.config(bg=T.BG_CARD)
        self._program_e.pack(fill="x", pady=(0, T.PAD_SM))

        tk.Label(self._role_frame,
                 text="Subject Code *  (given by your lecturer)",
                 bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                 font=T.FONT_SMALL).pack(anchor="w")
        self._code_var = tk.StringVar()
        # Auto-uppercase
        self._code_var.trace_add("write",
            lambda *_: self._code_var.set(self._code_var.get().upper())
            if self._code_var.get() != self._code_var.get().upper() else None)
        ttk.Entry(self._role_frame, textvariable=self._code_var,
                  style="TEntry", font=T.FONT_MONO).pack(fill="x",
                                                          pady=(2, T.PAD_SM))

    def _build_lecturer_fields(self):
        for w in self._role_frame.winfo_children():
            w.destroy()

        self._dept_e = LabelledEntry(self._role_frame, "Department *",
                                     placeholder="e.g. School of Computing")
        self._dept_e.config(bg=T.BG_CARD)
        self._dept_e.pack(fill="x", pady=(0, T.PAD_SM))

    def _on_role_change(self):
        if self._role.get() == "student":
            self._build_student_fields()
        else:
            self._build_lecturer_fields()

    # ── Registration logic ──────────────────────────────────────────────────

    def _on_register(self):
        self._error_var.set("")
        role      = self._role.get()
        full_name = self._full_name.get().strip()
        username  = self._username_e.get().strip()
        email     = self._email_e.get().strip()
        password  = self._pw_var.get()
        confirm   = self._cf_var.get()

        # ── Common field validation ─────────────────────────────────────
        if not all([full_name, username, email, password, confirm]):
            self._error_var.set("⚠  All fields marked * are required.")
            return

        ok, msg = validate_username(username)
        if not ok:
            self._error_var.set(f"⚠  {msg}")
            return

        if not validate_email(email):
            self._error_var.set("⚠  Invalid email address.")
            return

        ok, msg = validate_password_strength(password)
        if not ok:
            self._error_var.set(f"⚠  {msg}")
            return

        if password != confirm:
            self._error_var.set("⚠  Passwords do not match.")
            return

        # ── Duplicate checks ────────────────────────────────────────────
        if queries.get_user_by_username(username):
            self._error_var.set("⚠  Username is already taken.")
            return
        if queries.get_user_by_email(email):
            self._error_var.set("⚠  Email is already registered.")
            return

        # ── Role-specific validation ────────────────────────────────────
        subject    = None
        program    = ""
        department = ""

        if role == "student":
            program      = self._program_e.get().strip()
            subject_code = self._code_var.get().strip().upper()
            if not program:
                self._error_var.set("⚠  Program / course is required.")
                return
            if not subject_code:
                self._error_var.set("⚠  Subject code is required.")
                return
            subject = queries.get_subject_by_code(subject_code)
            if not subject:
                self._error_var.set(
                    f"⚠  Subject code '{subject_code}' not found.\n"
                    "Ask your lecturer for the correct code."
                )
                return
        else:
            department = self._dept_e.get().strip()
            if not department:
                self._error_var.set("⚠  Department is required.")
                return

        # ── Persist records ─────────────────────────────────────────────
        try:
            hashed  = hash_password(password)
            user_id = queries.create_user(username, email, hashed, role)

            if role == "student":
                # Generate unique student number
                reg_no = generate_student_number()
                while queries.get_student_id_exists(reg_no):
                    reg_no = generate_student_number()

                student_pk = queries.create_student(
                    user_id, full_name, reg_no, program
                )
                queries.enroll_student(student_pk, subject["id"])

                # Notify the lecturer
                conn = get_connection()
                row  = conn.execute(
                    """SELECT u.id
                       FROM   lecturers l
                       JOIN   users u ON u.id = l.user_id
                       WHERE  l.id = ?""",
                    (subject["lecturer_id"],)
                ).fetchone()
                conn.close()
                if row:
                    queries.add_notification(
                        row["id"],
                        f"New student '{full_name}' enrolled in "
                        f"{subject['name']} ({subject['subject_code']})"
                    )
            else:
                queries.create_lecturer(user_id, full_name, department)

            messagebox.showinfo(
                "Account Created ✅",
                f"Welcome, {full_name}!\n\n"
                f"Your account has been created.\n"
                f"You can now log in with username:  {username}",
                parent=self,
            )
            self.destroy()

        except Exception as exc:
            self._error_var.set(f"⚠  Registration failed: {exc}")
