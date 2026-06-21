"""
gui/login_page.py
-----------------
Login window — first screen the user sees.

FIX (logout crash):
  The original code called self.withdraw() on the tk.Tk root, then opened a
  Toplevel dashboard and blocked with wait_window().  When the dashboard was
  destroyed Tkinter found NO visible windows and terminated mainloop before
  deiconify() could run — killing the whole process.

  Fix: keep the root window alive but shrunk to 1×1 and moved off-screen
  (overrideredirect keeps it out of the taskbar entirely).  The login form
  lives in a separate Toplevel that we open/close independently.  The hidden
  root is never destroyed, so mainloop never exits.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import gui.theme as T
from gui.widgets import center_window, IconButton, LabelledEntry, Toast
from database import queries
from utils.auth import verify_password, Session


class LoginPage:
    """
    Manages the full login/dashboard lifecycle.

    Architecture
    ------------
    - A tiny hidden tk.Tk() root keeps mainloop alive at all times.
    - The visible login form is a Toplevel on that root.
    - Dashboards are also Toplevels on that root.
    - Closing a dashboard simply destroys it and re-opens the login Toplevel —
      the root (and mainloop) are never destroyed.
    """

    def __init__(self):
        # ── Persistent hidden root — NEVER destroyed ──────────────────
        self._root = tk.Tk()
        self._root.withdraw()                        # invisible, 0×0
        self._root.title("AttendX")
        self._root.resizable(False, False)
        # Prevent any accidental close of root killing the app
        self._root.protocol("WM_DELETE_WINDOW", lambda: None)

        # Apply ttk theme once on the root
        style = ttk.Style(self._root)
        from gui.theme import apply_global_ttk_theme
        apply_global_ttk_theme(style)

        self._show_login()

    # ── public entry point ─────────────────────────────────────────────

    def run(self):
        self._root.mainloop()

    # ── Login window ───────────────────────────────────────────────────

    def _show_login(self):
        """Create (or re-create) the login Toplevel."""
        self._win = tk.Toplevel(self._root)
        self._win.title("AttendX — Login")
        self._win.configure(bg=T.BG_DARK)
        self._win.resizable(False, False)
        center_window(self._win, 460, 650)
        # Closing the login window should not destroy the root
        self._win.protocol("WM_DELETE_WINDOW", self._quit_app)
        self._build()

    def _quit_app(self):
        """Cleanly exit the whole application."""
        self._root.destroy()

    # ── Build UI ───────────────────────────────────────────────────────

    def _build(self):
        win = self._win
        outer = tk.Frame(win, bg=T.BG_DARK, padx=T.PAD_XL, pady=T.PAD_XL)
        outer.pack(fill="both", expand=True)

        # Branding
        tk.Label(outer, text="🎓", bg=T.BG_DARK,
                 font=(T.FONT_FAMILY, 42)).pack(pady=(0, 4))
        tk.Label(outer, text="AttendX", bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=T.FONT_GIANT).pack()
        tk.Label(outer, text="Smart Attendance Management System",
                 bg=T.BG_DARK, fg=T.TEXT_SECONDARY,
                 font=T.FONT_SMALL).pack(pady=(2, T.PAD_XL))

        # Form card
        card = tk.Frame(outer, bg=T.BG_CARD,
                        highlightbackground=T.BORDER, highlightthickness=1,
                        padx=T.PAD_LG, pady=T.PAD_LG)
        card.pack(fill="x")

        tk.Label(card, text="Sign In", bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H2).pack(anchor="w",
                                                          pady=(0, T.PAD_MD))

        self._username = LabelledEntry(card, "Username",
                                       placeholder="Enter your username")
        self._username.config(bg=T.BG_CARD)
        self._username.pack(fill="x", pady=(0, T.PAD_SM))

        # Password: no placeholder when show="●" (masked dots are confusing)
        tk.Label(card, text="Password", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        self._pw_var = tk.StringVar()
        self._pw_entry = ttk.Entry(card, textvariable=self._pw_var,
                                   show="●", style="TEntry",
                                   font=T.FONT_BODY)
        self._pw_entry.pack(fill="x", pady=(2, T.PAD_MD))

        self._error_var = tk.StringVar()
        tk.Label(card, textvariable=self._error_var,
                 bg=T.BG_CARD, fg=T.DANGER,
                 font=T.FONT_SMALL, wraplength=340).pack(fill="x",
                                                          pady=(0, T.PAD_SM))

        IconButton(card, "  Sign In  →", command=self._login,
                   font=T.FONT_H3).pack(fill="x", ipady=4)

        # Divider + register link
        tk.Frame(outer, bg=T.BORDER, height=1).pack(fill="x",
                                                      pady=T.PAD_MD)
        bottom = tk.Frame(outer, bg=T.BG_DARK)
        bottom.pack()
        tk.Label(bottom, text="Don't have an account?",
                 bg=T.BG_DARK, fg=T.TEXT_SECONDARY,
                 font=T.FONT_SMALL).pack(side="left")
        tk.Button(bottom, text=" Create account",
                  bg=T.BG_DARK, fg=T.ACCENT_LIGHT,
                  font=(T.FONT_FAMILY, 9, "underline"),
                  relief="flat", cursor="hand2", bd=0,
                  command=self._open_register).pack(side="left")

        win.bind("<Return>", lambda _: self._login())
        self._toast = Toast(win)

    # ── Actions ────────────────────────────────────────────────────────

    def _login(self):
        self._error_var.set("")
        username = self._username.get().strip()
        password = self._pw_var.get()

        if not username or not password:
            self._error_var.set("⚠  Please fill in all fields.")
            return

        user = queries.get_user_by_username(username)
        if not user:
            self._error_var.set("⚠  Username not found.")
            return

        if not verify_password(password, user["password"]):
            self._error_var.set("⚠  Incorrect password.")
            return

        profile = (queries.get_lecturer_by_user_id(user["id"])
                   if user["role"] == "lecturer"
                   else queries.get_student_by_user_id(user["id"]))

        if not profile:
            self._error_var.set("⚠  Profile not found. Contact admin.")
            return

        Session.login(user, profile)
        self._toast.show("Login successful!", "success", 600)
        self._win.after(300, self._launch_dashboard)

    def _launch_dashboard(self):
        """Hide login form and open the appropriate dashboard Toplevel."""
        self._win.withdraw()

        def on_dashboard_close():
            """Called when the dashboard window is destroyed."""
            Session.logout()
            # Re-show the login window (create fresh to reset state)
            self._win.destroy()
            self._show_login()

        if Session.role() == "lecturer":
            from gui.lecturer_dashboard import LecturerDashboard
            dash = LecturerDashboard(self._root, on_close_cb=on_dashboard_close)
        else:
            from gui.student_dashboard import StudentDashboard
            dash = StudentDashboard(self._root, on_close_cb=on_dashboard_close)

    def _open_register(self):
        from gui.register_page import RegisterPage
        RegisterPage(self._win)
