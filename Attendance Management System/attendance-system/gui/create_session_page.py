"""
gui/create_session_page.py
--------------------------
Dialog window for creating a new attendance session.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

import gui.theme as T
from gui.widgets import center_window, IconButton, LabelledEntry
from database import queries


class CreateSessionDialog(tk.Toplevel):
    """Modal dialog to create an attendance session for a given subject."""

    def __init__(self, parent, subject: dict, on_created_callback=None):
        super().__init__(parent)
        self.title("New Attendance Session")
        self.configure(bg=T.BG_DARK)
        self.resizable(False, False)
        center_window(self, 420, 420)
        self.grab_set()
        self.focus_set()

        self._subject   = subject
        self._callback  = on_created_callback
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self, bg=T.BG_DARK, padx=T.PAD_LG, pady=T.PAD_LG)
        outer.pack(fill="both", expand=True)

        # Header
        tk.Label(outer, text="Create Attendance Session",
                 bg=T.BG_DARK, fg=T.TEXT_PRIMARY, font=T.FONT_H2).pack(anchor="w")
        tk.Label(outer,
                 text=f"Subject: {self._subject['name']}  ({self._subject['subject_code']})",
                 bg=T.BG_DARK, fg=T.ACCENT_LIGHT, font=T.FONT_SMALL).pack(anchor="w", pady=(2, T.PAD_MD))

        card = tk.Frame(outer, bg=T.BG_CARD,
                        highlightbackground=T.BORDER, highlightthickness=1,
                        padx=T.PAD_LG, pady=T.PAD_LG)
        card.pack(fill="x")

        # Session title
        self._title_entry = LabelledEntry(card, "Session Title",
                                          placeholder="e.g. Week 3 Lecture")
        self._title_entry.config(bg=T.BG_CARD)
        self._title_entry.pack(fill="x", pady=(0, T.PAD_SM))

        # Date
        tk.Label(card, text="Date", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        self._date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        ttk.Entry(card, textvariable=self._date_var,
                  style="TEntry").pack(fill="x", pady=(2, T.PAD_SM))

        # Time
        tk.Label(card, text="Start Time (HH:MM)", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        self._time_var = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        ttk.Entry(card, textvariable=self._time_var,
                  style="TEntry").pack(fill="x", pady=(2, T.PAD_MD))

        # Error
        self._error_var = tk.StringVar()
        tk.Label(card, textvariable=self._error_var,
                 bg=T.BG_CARD, fg=T.DANGER, font=T.FONT_SMALL,
                 wraplength=360).pack(fill="x", pady=(0, T.PAD_SM))

        IconButton(card, "  Create Session  →", command=self._create,
                   font=T.FONT_H3).pack(fill="x", ipady=4)

        tk.Button(outer, text="Cancel", bg=T.BG_DARK,
                  fg=T.TEXT_SECONDARY, font=T.FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  command=self.destroy).pack(pady=(T.PAD_SM, 0))

        self.bind("<Return>", lambda _: self._create())

    # ── Actions ────────────────────────────────────────────────────────────

    def _create(self):
        self._error_var.set("")
        title      = self._title_entry.get().strip()
        date_str   = self._date_var.get().strip()
        time_str   = self._time_var.get().strip()

        if not title:
            self._error_var.set("⚠  Session title is required.")
            return

        # Validate date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self._error_var.set("⚠  Date must be YYYY-MM-DD.")
            return

        # Validate time
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            self._error_var.set("⚠  Time must be HH:MM (24-hour).")
            return

        try:
            session_id = queries.create_session(
                self._subject["id"], title, date_str, time_str
            )
            messagebox.showinfo(
                "Session Created",
                f"✅ Session '{title}' created successfully!\n"
                f"Students can now sign attendance.",
                parent=self
            )
            if self._callback:
                self._callback(session_id)
            self.destroy()
        except Exception as e:
            self._error_var.set(f"⚠  Failed to create session: {e}")
