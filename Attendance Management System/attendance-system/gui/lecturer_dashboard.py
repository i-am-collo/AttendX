"""
gui/lecturer_dashboard.py
--------------------------
Modern sidebar-based admin dashboard for lecturers.

Architecture
------------
- Fixed top navbar (brand, hamburger on mobile, active-subject switcher,
  notifications, profile).
- Fixed left sidebar (240px) with single-purpose navigation: Dashboard,
  Subjects, Sessions, Students, Attendance, Analytics, Settings, Logout.
- One scrollable/resizable content page visible at a time (stack-based
  page switching via grid + tkraise, the Tk equivalent of a SPA router).
- Responsive: sidebar collapses to an icon rail on medium widths and
  becomes a hamburger-triggered overlay drawer on narrow/mobile widths.

Features preserved from the previous single-page version:
- Subject management (create / select)
- Session management (create / open / close, QR code)
- Live attendance table (auto-refreshing)
- Student roster
- Per-subject analytics
- Export to Excel / PDF
- Notification bell
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import date

import gui.theme as T
from gui.widgets import (
    center_window, IconButton, build_treeview, populate_tree,
    StatCard, Badge, Toast, ScrollableFrame
)
from database import queries
from utils.auth import Session, generate_subject_code
from utils.export import export_to_excel, export_to_pdf, get_default_export_path


class LecturerDashboard(tk.Toplevel):
    """Main window for a logged-in lecturer — sidebar-based admin layout."""

    AUTO_REFRESH_MS = 2000

    # Layout constants
    SIDEBAR_WIDTH       = 240
    SIDEBAR_ICON_WIDTH  = 72
    NAVBAR_HEIGHT       = 64
    BREAKPOINT_ICON     = 1100   # below this -> icon-only sidebar
    BREAKPOINT_HIDE     = 860    # below this -> sidebar hidden behind hamburger

    # Sidebar nav items: (id, icon, label, requires_subject)
    NAV_ITEMS = [
        ("dashboard",  "🏠", "Dashboard",  False),
        ("subjects",   "📚", "Subjects",   False),
        ("sessions",   "🗓", "Sessions",   True),
        ("students",   "👥", "Students",   True),
        ("attendance", "✅", "Attendance", True),
        ("analytics",  "📊", "Analytics",  True),
        ("settings",   "⚙",  "Settings",   False),
    ]

    def __init__(self, parent, on_close_cb=None):
        super().__init__(parent)
        self.title("AttendX — Lecturer Dashboard")
        self.configure(bg=T.BG_DARK)
        self._on_close_cb = on_close_cb
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.minsize(880, 600)
        center_window(self, 1280, 800)

        self._user    = Session.user()
        self._profile = Session.profile()   # lecturers row
        self._subjects: list[dict] = []
        self._sel_subject: dict | None = None
        self._sel_session: dict | None = None
        self._sessions_data: list[dict] = []

        self._current_page = "dashboard"
        self._sidebar_mode: str | None = None
        self._mobile_drawer_open = False
        self._nav_rows: dict[str, dict] = {}
        self._pages: dict[str, tk.Frame] = {}
        self._page_inner: dict[str, tk.Frame] = {}
        self._page_placeholder: dict[str, tk.Frame] = {}
        self._subject_cards: list[tk.Frame] = []
        self._selected_subject_index: int | None = None

        self._refresh_after_id = None
        self._done = False

        self._build()
        self._load_subjects()
        self._select_page("dashboard")
        self._apply_sidebar_mode("full")
        self._start_refresh()

    # ══════════════════════════════════════════════════════════════════════
    #  TOP-LEVEL LAYOUT
    # ══════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_navbar()

        body = tk.Frame(self, bg=T.BG_DARK)
        body.pack(fill="both", expand=True)
        self._body = body

        self._sidebar = tk.Frame(body, bg=T.BG_CARD, width=self.SIDEBAR_WIDTH)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar(self._sidebar)

        self._content = tk.Frame(body, bg=T.BG_DARK)
        self._content.pack(side="left", fill="both", expand=True)

        self._page_container = tk.Frame(self._content, bg=T.BG_DARK)
        self._page_container.pack(fill="both", expand=True, padx=T.PAD_LG, pady=T.PAD_LG)
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._build_dashboard_page()
        self._build_subjects_page()
        self._build_sessions_page()
        self._build_students_page()
        self._build_attendance_page()
        self._build_analytics_page()
        self._build_settings_page()

        self._toast = Toast(self)
        self.bind("<Configure>", self._handle_resize)

    # ── Navbar ───────────────────────────────────────────────────────────────

    def _build_navbar(self):
        navbar = tk.Frame(self, bg=T.BG_DEEP, height=self.NAVBAR_HEIGHT)
        navbar.pack(fill="x")
        navbar.pack_propagate(False)
        self._navbar = navbar

        left = tk.Frame(navbar, bg=T.BG_DEEP)
        left.pack(side="left", fill="y")

        self._hamburger_btn = tk.Button(
            left, text="☰", bg=T.BG_DEEP, fg=T.TEXT_PRIMARY,
            activebackground=T.BG_HOVER, activeforeground=T.TEXT_PRIMARY,
            font=(T.FONT_FAMILY, 15), relief="flat", bd=0, cursor="hand2",
            command=self._toggle_mobile_drawer,
        )
        # Packed/unpacked dynamically by _apply_sidebar_mode()

        brand = tk.Frame(left, bg=T.BG_DEEP)
        brand.pack(side="left", padx=T.PAD_LG)
        tk.Label(brand, text="🎓  AttendX", bg=T.BG_DEEP,
                 fg=T.ACCENT_LIGHT, font=T.FONT_H2).pack(anchor="w")
        tk.Label(brand, text="Lecturer Portal", bg=T.BG_DEEP,
                 fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(anchor="w")

        right = tk.Frame(navbar, bg=T.BG_DEEP)
        right.pack(side="right", fill="y", padx=T.PAD_LG)

        tk.Label(right, text=f"👤  {self._profile['full_name']}",
                 bg=T.BG_DEEP, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(
            side="right", padx=(T.PAD_MD, 0))

        self._notif_btn = tk.Button(
            right, text="🔔", bg=T.BG_DEEP, fg=T.TEXT_PRIMARY,
            activebackground=T.BG_HOVER, activeforeground=T.TEXT_PRIMARY,
            font=(T.FONT_FAMILY, 13), relief="flat", bd=0, cursor="hand2",
            command=self._show_notifications,
        )
        self._notif_btn.pack(side="right", padx=(T.PAD_SM, 0))
        self._notif_badge = tk.Label(right, text="", bg=T.BG_DEEP,
                                      fg=T.DANGER, font=T.FONT_BADGE)
        self._notif_badge.pack(side="right")

        subj_box = tk.Frame(right, bg=T.BG_DEEP)
        subj_box.pack(side="right", padx=(0, T.PAD_LG))
        tk.Label(subj_box, text="Subject", bg=T.BG_DEEP,
                 fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(side="left", padx=(0, T.PAD_XS))
        self._subject_combo_var = tk.StringVar()
        self._subject_combo = ttk.Combobox(
            subj_box, textvariable=self._subject_combo_var,
            state="readonly", style="TCombobox", width=20,
        )
        self._subject_combo.pack(side="left")
        self._subject_combo.bind("<<ComboboxSelected>>", self._on_subject_combo_pick)
        IconButton(subj_box, "+", command=self._create_subject_dialog,
                   bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                   font=T.FONT_SMALL, padx=10, pady=4).pack(side="left", padx=(T.PAD_XS, 0))

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self, sidebar):
        nav_area = tk.Frame(sidebar, bg=T.BG_CARD)
        nav_area.pack(side="top", fill="both", expand=True, pady=(T.PAD_MD, 0))
        self._nav_area = nav_area

        for item_id, icon, label, requires_subject in self.NAV_ITEMS:
            self._build_nav_row(nav_area, item_id, icon, label, requires_subject)

        footer = tk.Frame(sidebar, bg=T.BG_CARD)
        footer.pack(side="bottom", fill="x", pady=(0, T.PAD_MD))
        ttk.Separator(footer, orient="horizontal").pack(fill="x", pady=(0, T.PAD_SM))
        self._build_nav_row(footer, "logout", "🚪", "Logout", False, danger=True)

    def _build_nav_row(self, parent, item_id, icon, label, requires_subject, danger=False):
        row = tk.Frame(parent, bg=T.BG_CARD, cursor="hand2")
        row.pack(fill="x", padx=T.PAD_SM, pady=2)

        accent = tk.Frame(row, bg=T.BG_CARD, width=3)
        accent.pack(side="left", fill="y")

        inner = tk.Frame(row, bg=T.BG_CARD, padx=T.PAD_SM, pady=10)
        inner.pack(side="left", fill="x", expand=True)

        icon_lbl = tk.Label(inner, text=icon, bg=T.BG_CARD,
                             fg=T.TEXT_SECONDARY, font=(T.FONT_FAMILY, 14))
        icon_lbl.pack(side="left")

        text_lbl = tk.Label(inner, text=label, bg=T.BG_CARD,
                             fg=T.TEXT_SECONDARY, font=T.FONT_BODY_MED, anchor="w")
        text_lbl.pack(side="left", padx=(T.PAD_SM, 0), fill="x", expand=True)

        widgets = {
            "row": row, "accent": accent, "inner": inner,
            "icon": icon_lbl, "text": text_lbl, "danger": danger,
        }
        self._nav_rows[item_id] = widgets

        handler = (lambda _e=None: self._on_close()) if item_id == "logout" \
            else (lambda _e=None, n=item_id: self._select_page(n))
        for w in (row, accent, inner, icon_lbl, text_lbl):
            w.bind("<Button-1>", handler)
            w.bind("<Enter>", lambda _e, i=item_id: self._style_nav_row(i, hover=True))
            w.bind("<Leave>", lambda _e, i=item_id: self._style_nav_row(i, hover=False))

        self._style_nav_row(item_id)

    def _style_nav_row(self, item_id, hover=False):
        w = self._nav_rows[item_id]
        active = (item_id == self._current_page)
        danger = w["danger"]

        if active:
            bg = T.ACCENT
            fg = T.TEXT_PRIMARY
            accent_bg = T.ACCENT_LIGHT
            font = T.FONT_BODY_MED
        elif hover:
            bg = T.DANGER_DARK if danger else T.BG_HOVER
            fg = T.TEXT_PRIMARY
            accent_bg = T.BG_CARD
            font = T.FONT_BODY_MED
        else:
            bg = T.BG_CARD
            fg = T.DANGER if danger else T.TEXT_SECONDARY
            accent_bg = T.BG_CARD
            font = T.FONT_BODY_MED if danger else T.FONT_BODY

        for key in ("row", "inner", "icon", "text"):
            w[key].config(bg=bg)
        w["icon"].config(fg=fg)
        w["text"].config(fg=fg, font=font)
        w["accent"].config(bg=accent_bg)

    def _set_sidebar_icon_only(self, icon_only: bool):
        for w in self._nav_rows.values():
            if icon_only:
                w["text"].pack_forget()
                w["icon"].pack(side="left", expand=True, fill="both")
                w["icon"].config(anchor="center")
            else:
                w["icon"].config(anchor="w")
                w["icon"].pack(side="left", expand=False)
                if not w["text"].winfo_ismapped():
                    w["text"].pack(side="left", padx=(T.PAD_SM, 0), fill="x", expand=True)

    # ══════════════════════════════════════════════════════════════════════
    #  RESPONSIVE BEHAVIOUR
    # ══════════════════════════════════════════════════════════════════════

    def _handle_resize(self, event):
        if event.widget is not self:
            return
        width = event.width
        if width < self.BREAKPOINT_HIDE:
            mode = "hidden"
        elif width < self.BREAKPOINT_ICON:
            mode = "icon"
        else:
            mode = "full"
        if mode != self._sidebar_mode:
            self._apply_sidebar_mode(mode)

    def _apply_sidebar_mode(self, mode):
        self._sidebar_mode = mode
        self._close_mobile_drawer()

        if mode == "hidden":
            if self._sidebar.winfo_ismapped():
                self._sidebar.pack_forget()
            self._hamburger_btn.pack(side="left", padx=(T.PAD_MD, 0))
        else:
            self._hamburger_btn.pack_forget()
            if not self._sidebar.winfo_ismapped():
                self._sidebar.pack(side="left", fill="y", before=self._content)
            width_px = self.SIDEBAR_WIDTH if mode == "full" else self.SIDEBAR_ICON_WIDTH
            self._sidebar.config(width=width_px)
            self._set_sidebar_icon_only(mode == "icon")

    def _toggle_mobile_drawer(self):
        if self._mobile_drawer_open:
            self._close_mobile_drawer()
        else:
            self._open_mobile_drawer()

    def _open_mobile_drawer(self):
        self._mobile_drawer_open = True
        self._set_sidebar_icon_only(False)
        self._scrim = tk.Frame(self._body, bg=T.BG_DEEP)
        self._scrim.place(x=0, y=0, relwidth=1, relheight=1)
        self._scrim.bind("<Button-1>", lambda _e: self._close_mobile_drawer())
        self._sidebar.config(width=self.SIDEBAR_WIDTH)
        self._sidebar.place(in_=self._body, x=0, y=0, width=self.SIDEBAR_WIDTH, relheight=1)
        self._sidebar.lift()

    def _close_mobile_drawer(self):
        if not self._mobile_drawer_open:
            return
        self._mobile_drawer_open = False
        if hasattr(self, "_scrim") and self._scrim.winfo_exists():
            self._scrim.destroy()
        if self._sidebar_mode == "hidden":
            self._sidebar.place_forget()

    # ══════════════════════════════════════════════════════════════════════
    #  SHARED UI HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _add_page(self, name) -> tk.Frame:
        page = tk.Frame(self._page_container, bg=T.BG_DARK)
        page.grid(row=0, column=0, sticky="nsew")
        self._pages[name] = page
        return page

    def _page_header(self, parent, title, subtitle="", build_actions=None):
        hdr = tk.Frame(parent, bg=T.BG_DARK)
        hdr.pack(fill="x", pady=(0, T.PAD_LG))

        left = tk.Frame(hdr, bg=T.BG_DARK)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=title, bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=T.FONT_GIANT).pack(anchor="w")
        subtitle_lbl = tk.Label(left, text=subtitle, bg=T.BG_DARK,
                                 fg=T.TEXT_SECONDARY, font=T.FONT_BODY)
        subtitle_lbl.pack(anchor="w", pady=(4, 0))

        right = tk.Frame(hdr, bg=T.BG_DARK)
        right.pack(side="right")
        if build_actions:
            build_actions(right)
        return subtitle_lbl

    def _card(self, parent, **kw):
        kw.setdefault("bg", T.BG_CARD)
        kw.setdefault("padx", T.PAD_LG)
        kw.setdefault("pady", T.PAD_LG)
        kw.setdefault("highlightbackground", T.BORDER)
        kw.setdefault("highlightthickness", 1)
        return tk.Frame(parent, **kw)

    def _make_subject_placeholder(self, parent, page_name):
        ph = tk.Frame(parent, bg=T.BG_DARK)
        box = tk.Frame(ph, bg=T.BG_DARK)
        box.place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(box, text="📚", bg=T.BG_DARK, font=(T.FONT_FAMILY, 36)).pack()
        tk.Label(box, text="No subject selected", bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H2).pack(pady=(T.PAD_SM, 2))
        tk.Label(box, text="Choose or create a subject to continue.",
                 bg=T.BG_DARK, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(pady=(0, T.PAD_MD))
        IconButton(box, "Go to Subjects",
                   command=lambda: self._select_page("subjects"),
                   font=T.FONT_SMALL).pack()
        return ph

    def _make_responsive_pane(self, parent, build_left, build_right,
                               breakpoint=760, left_weight=3, right_weight=2):
        """Two-column area that stacks vertically below `breakpoint` px."""
        container = tk.Frame(parent, bg=T.BG_DARK)
        left = build_left(container)
        right = build_right(container)
        state = {"stacked": None}

        def relayout(width):
            stacked = width < breakpoint
            if state["stacked"] == stacked:
                return
            state["stacked"] = stacked
            left.grid_forget()
            right.grid_forget()
            if stacked:
                container.grid_columnconfigure(0, weight=1, uniform="")
                container.grid_columnconfigure(1, weight=0, uniform="")
                container.grid_rowconfigure(0, weight=0)
                container.grid_rowconfigure(1, weight=1)
                left.grid(row=0, column=0, sticky="nsew", pady=(0, T.PAD_MD))
                right.grid(row=1, column=0, sticky="nsew")
            else:
                container.grid_columnconfigure(0, weight=left_weight, uniform="pane")
                container.grid_columnconfigure(1, weight=right_weight, uniform="pane")
                container.grid_rowconfigure(0, weight=1)
                container.grid_rowconfigure(1, weight=0)
                left.grid(row=0, column=0, sticky="nsew", padx=(0, T.PAD_MD))
                right.grid(row=0, column=1, sticky="nsew")

        container.bind("<Configure>", lambda e: relayout(e.width))
        return container

    def _draw_bar_chart(self, canvas, data, max_value=100.0):
        """Lightweight horizontal bar chart drawn directly on a Canvas."""
        canvas.delete("all")
        width = canvas.winfo_width()
        if width <= 1:
            width = 360
        if not data:
            canvas.config(height=60)
            canvas.create_text(width // 2, 30, text="No data yet",
                                fill=T.TEXT_MUTED, font=T.FONT_SMALL)
            return

        row_h, label_w, value_w = 30, 120, 50
        bar_x0 = label_w
        bar_x1 = max(width - value_w, bar_x0 + 60)
        height = len(data) * row_h + 12
        canvas.config(height=height)

        for i, (label, value) in enumerate(data):
            y = i * row_h + 6
            mid = y + row_h // 2
            canvas.create_text(4, mid, text=label, anchor="w",
                                fill=T.TEXT_SECONDARY, font=T.FONT_SMALL,
                                width=label_w - 8)
            canvas.create_rectangle(bar_x0, y + 5, bar_x1, y + row_h - 5,
                                     fill=T.BG_INPUT, outline="")
            frac = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
            bar_end = bar_x0 + (bar_x1 - bar_x0) * frac
            color = T.SUCCESS if value >= 75 else (T.WARNING if value >= 40 else T.DANGER)
            if bar_end > bar_x0:
                canvas.create_rectangle(bar_x0, y + 5, bar_end, y + row_h - 5,
                                         fill=color, outline="")
            canvas.create_text(bar_x1 + 8, mid, text=f"{value:.0f}%", anchor="w",
                                fill=T.TEXT_PRIMARY, font=T.FONT_SMALL)

    # ══════════════════════════════════════════════════════════════════════
    #  PAGE NAVIGATION
    # ══════════════════════════════════════════════════════════════════════

    def _select_page(self, name):
        self._close_mobile_drawer()
        self._current_page = name
        for item_id in self._nav_rows:
            self._style_nav_row(item_id)

        page = self._pages.get(name)
        if page is None:
            return
        page.tkraise()

        if name == "dashboard":
            self._refresh_dashboard()
        elif name == "subjects":
            self._render_subject_cards()
        elif name == "sessions":
            self._refresh_sessions_table()
        elif name == "students":
            self._refresh_student_roster()
        elif name == "attendance":
            self._refresh_attendance_table()
        elif name == "analytics":
            self._refresh_analytics()

    def _toggle_subject_placeholders(self):
        has_subject = self._sel_subject is not None
        for name in ("sessions", "students", "attendance", "analytics"):
            inner = self._page_inner.get(name)
            placeholder = self._page_placeholder.get(name)
            if inner is None or placeholder is None:
                continue
            if has_subject:
                placeholder.pack_forget()
                inner.pack(fill="both", expand=True)
            else:
                inner.pack_forget()
                placeholder.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════════
    #  DASHBOARD PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_dashboard_page(self):
        page = self._add_page("dashboard")

        def actions(parent):
            IconButton(parent, "+  New Session", command=self._create_session_dialog,
                       font=T.FONT_SMALL, padx=12, pady=7).pack(side="left", padx=(0, T.PAD_SM))
            IconButton(parent, "View Analytics", command=lambda: self._select_page("analytics"),
                       bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                       font=T.FONT_SMALL, padx=12, pady=7).pack(side="left")

        self._dash_subtitle = self._page_header(
            page, f"Welcome back, {self._profile['full_name'].split()[0]} 👋",
            "Here's what's happening across your subjects today.", actions
        )

        kpi_row = tk.Frame(page, bg=T.BG_DARK)
        kpi_row.pack(fill="x", pady=(0, T.PAD_LG))
        self._kpi_students = StatCard(kpi_row, "👥", "0", "Total Students")
        self._kpi_sessions = StatCard(kpi_row, "🗓", "0", "Total Sessions")
        self._kpi_present  = StatCard(kpi_row, "✅", "0", "Present Today")
        self._kpi_rate      = StatCard(kpi_row, "📈", "—", "Avg Attendance")
        for idx, card in enumerate((self._kpi_students, self._kpi_sessions,
                                     self._kpi_present, self._kpi_rate)):
            kpi_row.grid_columnconfigure(idx, weight=1, uniform="kpi")
            card.grid(row=0, column=idx, sticky="ew",
                      padx=(0 if idx == 0 else T.PAD_SM, 0), ipady=4)

        def build_left(parent):
            card = self._card(parent, bg=T.BG_CARD)
            tk.Label(card, text="Recent Sessions", bg=T.BG_CARD,
                     fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w", pady=(0, T.PAD_SM))
            cols = [
                {"id": "subject", "text": "Subject", "width": 140},
                {"id": "title",   "text": "Session",  "width": 150},
                {"id": "date",    "text": "Date",     "width": 90, "anchor": "center"},
                {"id": "status",  "text": "Status",   "width": 80, "anchor": "center"},
            ]
            tree_holder = tk.Frame(card, bg=T.BG_CARD)
            tree_holder.pack(fill="both", expand=True)
            self._dash_recent_tree = build_treeview(tree_holder, cols, height=7)
            return card

        def build_right(parent):
            card = self._card(parent, bg=T.BG_CARD)
            tk.Label(card, text="Attendance Summary", bg=T.BG_CARD,
                     fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w", pady=(0, T.PAD_SM))
            self._dash_summary_canvas = tk.Canvas(card, bg=T.BG_CARD, height=120,
                                                    highlightthickness=0)
            self._dash_summary_canvas.pack(fill="x")
            self._dash_summary_canvas.bind(
                "<Configure>", lambda _e: self._draw_bar_chart(
                    self._dash_summary_canvas, getattr(self, "_dash_summary_data", []))
            )
            ttk.Separator(card, orient="horizontal").pack(fill="x", pady=T.PAD_SM)
            quick = tk.Frame(card, bg=T.BG_CARD)
            quick.pack(fill="x")
            tk.Label(quick, text="Quick Actions", bg=T.BG_CARD,
                     fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w", pady=(0, T.PAD_XS))
            IconButton(quick, "+  New Subject", command=self._create_subject_dialog,
                       bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                       font=T.FONT_SMALL).pack(fill="x", pady=(0, T.PAD_XS))
            IconButton(quick, "👥  Manage Students", command=lambda: self._select_page("students"),
                       bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                       font=T.FONT_SMALL).pack(fill="x")
            return card

        pane = self._make_responsive_pane(page, build_left, build_right)
        pane.pack(fill="both", expand=True)

    def _refresh_dashboard(self):
        today = date.today().strftime("%Y-%m-%d")
        unique_students = set()
        total_sessions = 0
        present_today = 0
        pct_values = []
        recent = []

        for subj in self._subjects:
            students = queries.get_students_in_subject(subj["id"])
            for s in students:
                unique_students.add(s["id"])
            sessions = queries.get_sessions_by_subject(subj["id"])
            total_sessions += len(sessions)
            for s in sessions:
                recent.append((subj, s))
                if s["date"] == today:
                    present_today += len(queries.get_session_attendance(s["id"]))
            stats = queries.get_attendance_stats_for_subject(subj["id"])
            total = stats["total_sessions"]
            if total > 0:
                for r in stats["records"]:
                    pct_values.append(r["attended"] / total * 100)

        self._kpi_students.update_value(str(len(unique_students)))
        self._kpi_sessions.update_value(str(total_sessions))
        self._kpi_present.update_value(str(present_today))
        self._kpi_rate.update_value(f"{(sum(pct_values) / len(pct_values)):.0f}%" if pct_values else "—")

        recent.sort(key=lambda t: (t[1]["date"], t[1].get("start_time", "")), reverse=True)
        rows = []
        for subj, s in recent[:8]:
            status = "🟢 Open" if s["is_open"] else "🔴 Closed"
            rows.append([subj["name"], s["title"], s["date"], status])
        if hasattr(self, "_dash_recent_tree"):
            populate_tree(self._dash_recent_tree, rows)

        per_subject = []
        for subj in self._subjects:
            stats = queries.get_attendance_stats_for_subject(subj["id"])
            total = stats["total_sessions"]
            if total > 0 and stats["records"]:
                avg = sum(r["attended"] for r in stats["records"]) / len(stats["records"])
                per_subject.append((subj["name"][:14], (avg / total) * 100))
        self._dash_summary_data = per_subject[:6]
        if hasattr(self, "_dash_summary_canvas"):
            self._draw_bar_chart(self._dash_summary_canvas, self._dash_summary_data)

    # ══════════════════════════════════════════════════════════════════════
    #  SUBJECTS PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_subjects_page(self):
        page = self._add_page("subjects")

        def actions(parent):
            IconButton(parent, "+  New Subject", command=self._create_subject_dialog,
                       font=T.FONT_SMALL, padx=14, pady=8).pack(side="right")

        self._page_header(page, "Subjects", "All courses you are teaching.", actions)

        scroll = ScrollableFrame(page, bg=T.BG_DARK)
        scroll.pack(fill="both", expand=True)
        self._subjects_list_frame = scroll.inner

        self._subjects_empty_lbl = tk.Label(
            scroll.inner, text="You haven't created any subjects yet.\nClick \"+ New Subject\" to get started.",
            bg=T.BG_DARK, fg=T.TEXT_MUTED, font=T.FONT_BODY, justify="left"
        )

    def _render_subject_cards(self):
        for card in self._subject_cards:
            card.destroy()
        self._subject_cards = []
        self._subjects_empty_lbl.pack_forget()

        if not self._subjects:
            self._subjects_empty_lbl.pack(anchor="w", pady=T.PAD_LG)
            return

        for index, subject in enumerate(self._subjects):
            active = (index == self._selected_subject_index)
            card = self._card(
                self._subjects_list_frame, bg=T.BG_CARD,
                highlightbackground=T.ACCENT if active else T.BORDER,
                highlightthickness=2 if active else 1,
            )
            card.pack(fill="x", pady=(0, T.PAD_SM))

            left = tk.Frame(card, bg=T.BG_CARD)
            left.pack(side="left", fill="x", expand=True)
            tk.Label(left, text=subject["name"], bg=T.BG_CARD,
                     fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w")
            tk.Label(left, text=subject.get("subject_code", ""), bg=T.BG_CARD,
                     fg=T.ACCENT_LIGHT, font=T.FONT_SMALL).pack(anchor="w", pady=(2, 4))

            students = queries.get_students_in_subject(subject["id"])
            sessions = queries.get_sessions_by_subject(subject["id"])
            tk.Label(left, text=f"{len(students)} students  •  {len(sessions)} sessions",
                     bg=T.BG_CARD, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")

            right = tk.Frame(card, bg=T.BG_CARD)
            right.pack(side="right")
            if active:
                Badge(right, "Active", preset="success").pack(side="right", pady=2)
            else:
                IconButton(right, "Select", command=lambda i=index: self._select_subject(i),
                           bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                           font=T.FONT_SMALL, padx=10, pady=5).pack(side="right")
            IconButton(right, "Sessions →",
                       command=lambda i=index: (self._select_subject(i), self._select_page("sessions")),
                       bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.TEXT_SECONDARY,
                       font=T.FONT_SMALL, padx=10, pady=5).pack(side="right", padx=(0, T.PAD_SM))

            self._subject_cards.append(card)

    # ══════════════════════════════════════════════════════════════════════
    #  SESSIONS PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_sessions_page(self):
        page = self._add_page("sessions")
        self._page_placeholder["sessions"] = self._make_subject_placeholder(page, "sessions")

        inner = tk.Frame(page, bg=T.BG_DARK)
        self._page_inner["sessions"] = inner

        def actions(parent):
            self._session_search_var = tk.StringVar()
            self._session_search_var.trace_add("write", lambda *_: self._refresh_sessions_table())
            ttk.Entry(parent, textvariable=self._session_search_var,
                      style="TEntry", width=22).pack(side="left", padx=(0, T.PAD_SM))
            IconButton(parent, "+  New Session", command=self._create_session_dialog,
                       font=T.FONT_SMALL, padx=14, pady=8).pack(side="left")

        self._sessions_subtitle = self._page_header(inner, "Sessions", "", actions)

        act_row = tk.Frame(inner, bg=T.BG_DARK)
        act_row.pack(side="bottom", fill="x", pady=(T.PAD_SM, 0))
        IconButton(act_row, "Open Session", command=lambda: self._toggle_session(True),
                   bg=T.SUCCESS, hover_bg="#059669", font=T.FONT_SMALL,
                   padx=12, pady=7).pack(side="left", padx=(0, T.PAD_XS))
        IconButton(act_row, "Close Session", command=lambda: self._toggle_session(False),
                   bg=T.WARNING, hover_bg="#D97706", font=T.FONT_SMALL,
                   padx=12, pady=7).pack(side="left", padx=T.PAD_XS)
        IconButton(act_row, "Show QR Code", command=self._show_qr,
                   bg=T.INFO, hover_bg="#2563EB", font=T.FONT_SMALL,
                   padx=12, pady=7).pack(side="left", padx=T.PAD_XS)

        cols = [
            {"id": "title",  "text": "Title",  "width": 220},
            {"id": "date",   "text": "Date",   "width": 120, "anchor": "center"},
            {"id": "status", "text": "Status", "width": 120, "anchor": "center"},
        ]
        table_card = self._card(inner, bg=T.BG_CARD)
        table_card.pack(fill="both", expand=True)
        self._session_tree = build_treeview(table_card, cols, height=16)
        self._session_tree.bind("<<TreeviewSelect>>", self._on_session_select)

    def _refresh_sessions_table(self):
        if not self._sel_subject:
            return
        search = self._session_search_var.get().lower() if hasattr(self, "_session_search_var") else ""
        rows = []
        for s in self._sessions_data:
            if search and search not in s["title"].lower() and search not in s["date"]:
                continue
            status = "🟢 Open" if s["is_open"] else "🔴 Closed"
            rows.append([s["title"], s["date"], status])
        populate_tree(self._session_tree, rows)

        if self._sel_session:
            for item in self._session_tree.get_children():
                vals = self._session_tree.item(item, "values")
                if vals[0] == self._sel_session["title"] and vals[1] == self._sel_session["date"]:
                    self._session_tree.selection_set(item)
                    break

    # ══════════════════════════════════════════════════════════════════════
    #  STUDENTS PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_students_page(self):
        page = self._add_page("students")
        self._page_placeholder["students"] = self._make_subject_placeholder(page, "students")

        inner = tk.Frame(page, bg=T.BG_DARK)
        self._page_inner["students"] = inner

        def actions(parent):
            self._stu_search_var = tk.StringVar()
            self._stu_search_var.trace_add("write", lambda *_: self._refresh_student_roster())
            ttk.Entry(parent, textvariable=self._stu_search_var,
                      style="TEntry", width=26).pack(side="left")

        self._students_subtitle = self._page_header(inner, "Students", "", actions)

        cols = [
            {"id": "no",       "text": "#",         "width": 40,  "anchor": "center"},
            {"id": "name",     "text": "Full Name",  "width": 220},
            {"id": "reg_no",   "text": "Reg. No",    "width": 150},
            {"id": "program",  "text": "Program",    "width": 200},
            {"id": "enrolled", "text": "Enrolled",   "width": 160},
        ]
        table_card = self._card(inner, bg=T.BG_CARD)
        table_card.pack(fill="both", expand=True)
        self._stu_tree = build_treeview(table_card, cols, height=18)

    def _refresh_student_roster(self):
        if not self._sel_subject:
            return
        students = queries.get_students_in_subject(self._sel_subject["id"])
        search = self._stu_search_var.get().lower() if hasattr(self, "_stu_search_var") else ""
        rows = []
        for i, s in enumerate(students, 1):
            if search and search not in s["full_name"].lower() and search not in s["student_id"].lower():
                continue
            rows.append([i, s["full_name"], s["student_id"], s["program"], s["enrolled_at"][:10]])
        populate_tree(self._stu_tree, rows)

    # ══════════════════════════════════════════════════════════════════════
    #  ATTENDANCE PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_attendance_page(self):
        page = self._add_page("attendance")
        self._page_placeholder["attendance"] = self._make_subject_placeholder(page, "attendance")

        inner = tk.Frame(page, bg=T.BG_DARK)
        self._page_inner["attendance"] = inner

        def actions(parent):
            self._session_choice_var = tk.StringVar()
            self._session_choice = ttk.Combobox(
                parent, textvariable=self._session_choice_var,
                state="readonly", style="TCombobox", width=24,
            )
            self._session_choice.pack(side="left", padx=(0, T.PAD_SM))
            self._session_choice.bind("<<ComboboxSelected>>", self._on_session_choice)
            self._live_status_lbl = Badge(parent, "Select a session")
            self._live_status_lbl.pack(side="left", padx=(0, T.PAD_SM))
            self._refresh_lbl = tk.Label(parent, text="● live", bg=T.BG_DARK,
                                          fg=T.SUCCESS, font=T.FONT_SMALL)
            self._refresh_lbl.pack(side="left")

        self._attendance_subtitle = self._page_header(inner, "Live Attendance", "", actions)

        search_frame = tk.Frame(inner, bg=T.BG_DARK)
        search_frame.pack(fill="x", pady=(0, T.PAD_SM))
        tk.Label(search_frame, text="🔍", bg=T.BG_DARK, fg=T.TEXT_MUTED).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_attendance_table())
        ttk.Entry(search_frame, textvariable=self._search_var,
                  style="TEntry").pack(side="left", fill="x", expand=True, padx=(T.PAD_XS, 0))

        exp_row = tk.Frame(inner, bg=T.BG_DARK)
        exp_row.pack(side="bottom", fill="x", pady=(T.PAD_SM, 0))
        IconButton(exp_row, "⬇  Export Excel", command=lambda: self._export("xlsx"),
                   bg=T.SUCCESS, hover_bg="#059669",
                   font=T.FONT_SMALL, padx=12, pady=7).pack(side="left", padx=(0, T.PAD_SM))
        IconButton(exp_row, "⬇  Export PDF", command=lambda: self._export("pdf"),
                   bg=T.INFO, hover_bg="#2563EB",
                   font=T.FONT_SMALL, padx=12, pady=7).pack(side="left")

        attend_cols = [
            {"id": "no",      "text": "#",         "width": 40,  "anchor": "center"},
            {"id": "name",    "text": "Full Name",  "width": 200},
            {"id": "reg_no",  "text": "Reg. No",    "width": 130},
            {"id": "program", "text": "Program",    "width": 160},
            {"id": "method",  "text": "Method",     "width": 100, "anchor": "center"},
            {"id": "time",    "text": "Signed At",  "width": 160},
        ]
        table_card = self._card(inner, bg=T.BG_CARD)
        table_card.pack(fill="both", expand=True)
        self._attend_tree = build_treeview(table_card, attend_cols, height=14)

    def _refresh_attendance_table(self):
        if not self._sel_session:
            populate_tree(self._attend_tree, [])
            return
        records = queries.get_session_attendance(self._sel_session["id"])
        search = self._search_var.get().lower() if hasattr(self, "_search_var") else ""
        rows = []
        for i, r in enumerate(records, 1):
            if search and search not in r["full_name"].lower() and search not in r["reg_no"].lower():
                continue
            rows.append([i, r["full_name"], r["reg_no"], r["program"],
                         r["method"].capitalize(), r["signed_at"]])
        populate_tree(self._attend_tree, rows)

    # ══════════════════════════════════════════════════════════════════════
    #  ANALYTICS PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_analytics_page(self):
        page = self._add_page("analytics")
        self._page_placeholder["analytics"] = self._make_subject_placeholder(page, "analytics")

        inner = tk.Frame(page, bg=T.BG_DARK)
        self._page_inner["analytics"] = inner

        def actions(parent):
            IconButton(parent, "🔄  Refresh", command=self._refresh_analytics,
                       bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                       font=T.FONT_SMALL, padx=12, pady=7).pack(side="right")

        self._analytics_subtitle = self._page_header(
            inner, "Analytics", "Per-student attendance for the selected subject.", actions
        )

        kpi_row = tk.Frame(inner, bg=T.BG_DARK)
        kpi_row.pack(fill="x", pady=(0, T.PAD_LG))
        self._an_kpi_sessions = StatCard(kpi_row, "🗓", "0", "Sessions Held")
        self._an_kpi_rate     = StatCard(kpi_row, "📈", "—", "Avg Attendance")
        self._an_kpi_top      = StatCard(kpi_row, "🏆", "—", "Top Performer")
        self._an_kpi_risk     = StatCard(kpi_row, "⚠️", "0", "At Risk (<50%)")
        for idx, card in enumerate((self._an_kpi_sessions, self._an_kpi_rate,
                                     self._an_kpi_top, self._an_kpi_risk)):
            kpi_row.grid_columnconfigure(idx, weight=1, uniform="an_kpi")
            card.grid(row=0, column=idx, sticky="ew",
                      padx=(0 if idx == 0 else T.PAD_SM, 0), ipady=4)

        chart_card = self._card(inner, bg=T.BG_CARD)
        chart_card.pack(fill="x", pady=(0, T.PAD_LG))
        tk.Label(chart_card, text="Attendance by Student", bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w", pady=(0, T.PAD_SM))
        self._analytics_chart_canvas = tk.Canvas(chart_card, bg=T.BG_CARD, height=140,
                                                    highlightthickness=0)
        self._analytics_chart_canvas.pack(fill="x")
        self._analytics_chart_canvas.bind(
            "<Configure>", lambda _e: self._draw_bar_chart(
                self._analytics_chart_canvas, getattr(self, "_analytics_chart_data", []))
        )

        cols = [
            {"id": "name",     "text": "Student",          "width": 200},
            {"id": "reg",      "text": "Reg. No",          "width": 130},
            {"id": "attended", "text": "Sessions Attended","width": 150, "anchor": "center"},
            {"id": "total",    "text": "Total Sessions",   "width": 130, "anchor": "center"},
            {"id": "pct",      "text": "Attendance %",     "width": 130, "anchor": "center"},
        ]
        table_card = self._card(inner, bg=T.BG_CARD)
        table_card.pack(fill="both", expand=True)
        self._analytics_tree = build_treeview(table_card, cols, height=12)

    def _refresh_analytics(self):
        if not self._sel_subject:
            return
        stats = queries.get_attendance_stats_for_subject(self._sel_subject["id"])
        total = stats["total_sessions"]
        rows = []
        pct_values = []
        for r in stats["records"]:
            pct = (r["attended"] / total * 100) if total > 0 else 0
            pct_values.append((r["full_name"], pct))
            rows.append([r["full_name"], r["reg_no"], r["attended"], total, f"{pct:.1f}%"])
        populate_tree(self._analytics_tree, rows)

        self._an_kpi_sessions.update_value(str(total))
        if pct_values:
            avg = sum(p for _, p in pct_values) / len(pct_values)
            self._an_kpi_rate.update_value(f"{avg:.0f}%")
            top_name = max(pct_values, key=lambda t: t[1])[0]
            self._an_kpi_top.update_value(top_name.split()[0] if top_name else "—")
            at_risk = sum(1 for _, p in pct_values if p < 50)
            self._an_kpi_risk.update_value(str(at_risk))
        else:
            self._an_kpi_rate.update_value("—")
            self._an_kpi_top.update_value("—")
            self._an_kpi_risk.update_value("0")

        chart_data = sorted(pct_values, key=lambda t: t[1], reverse=True)[:8]
        self._analytics_chart_data = [(name[:14], pct) for name, pct in chart_data]
        self._draw_bar_chart(self._analytics_chart_canvas, self._analytics_chart_data)

    # ══════════════════════════════════════════════════════════════════════
    #  SETTINGS PAGE
    # ══════════════════════════════════════════════════════════════════════

    def _build_settings_page(self):
        page = self._add_page("settings")
        self._page_header(page, "Settings", "Your account information.")

        profile_card = self._card(page, bg=T.BG_CARD)
        profile_card.pack(fill="x", pady=(0, T.PAD_LG))
        tk.Label(profile_card, text="Profile", bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w", pady=(0, T.PAD_SM))

        fields = [
            ("Full Name", self._profile.get("full_name", "—")),
            ("Department", self._profile.get("department", "—") or "—"),
            ("Username", self._user.get("username", "—")),
            ("Email", self._user.get("email", "—")),
            ("Role", str(self._user.get("role", "—")).capitalize()),
            ("Member Since", str(self._user.get("created_at", "—"))[:10]),
        ]
        for label, value in fields:
            row = tk.Frame(profile_card, bg=T.BG_CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                     font=T.FONT_SMALL, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
                     font=T.FONT_BODY_MED, anchor="w").pack(side="left")

        about_card = self._card(page, bg=T.BG_CARD)
        about_card.pack(fill="x", pady=(0, T.PAD_LG))
        tk.Label(about_card, text="About", bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H3).pack(anchor="w", pady=(0, T.PAD_SM))
        tk.Label(about_card, text="AttendX — Attendance Management System",
                 bg=T.BG_CARD, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        tk.Label(about_card, text="Lecturer Portal · Dark Purple Theme",
                 bg=T.BG_CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(anchor="w", pady=(2, 0))

        IconButton(page, "🚪  Sign Out", command=self._on_close,
                   bg=T.DANGER, hover_bg="#DC2626",
                   font=T.FONT_SMALL, padx=14, pady=8).pack(anchor="w")

    # ══════════════════════════════════════════════════════════════════════
    #  SUBJECT / SESSION SELECTION
    # ══════════════════════════════════════════════════════════════════════

    def _load_subjects(self):
        self._subjects = queries.get_subjects_by_lecturer(self._profile["id"])
        choices = [f"{s['name']} ({s['subject_code']})" for s in self._subjects]
        self._subject_combo.config(values=choices)

        if self._subjects and self._selected_subject_index is None:
            self._select_subject(0)
        elif not self._subjects:
            self._sel_subject = None
            self._sel_session = None
            self._toggle_subject_placeholders()

        self._refresh_dashboard()
        if self._current_page == "subjects":
            self._render_subject_cards()

    def _select_subject(self, index):
        if index is None or index >= len(self._subjects):
            return
        self._selected_subject_index = index
        self._sel_subject = self._subjects[index]
        self._sel_session = None
        self._subject_combo_var.set(
            f"{self._sel_subject['name']} ({self._sel_subject['subject_code']})"
        )
        self._toggle_subject_placeholders()
        self._subject_data_refresh()
        if self._current_page == "subjects":
            self._render_subject_cards()

    def _on_subject_combo_pick(self, _event):
        idx = self._subject_combo.current()
        if 0 <= idx < len(self._subjects):
            self._select_subject(idx)

    def _subject_data_refresh(self):
        """Pull fresh DB data for the active subject and update every
        subject-dependent page (cheap UI re-population)."""
        if not self._sel_subject:
            return
        self._sessions_data = queries.get_sessions_by_subject(self._sel_subject["id"])

        if hasattr(self, "_sessions_subtitle"):
            self._sessions_subtitle.config(
                text=f"Subject: {self._sel_subject['name']} ({self._sel_subject['subject_code']})"
            )
        if hasattr(self, "_students_subtitle"):
            self._students_subtitle.config(
                text=f"Enrolled in {self._sel_subject['name']}"
            )
        if hasattr(self, "_attendance_subtitle"):
            self._attendance_subtitle.config(
                text=f"Subject: {self._sel_subject['name']} ({self._sel_subject['subject_code']})"
            )
        if hasattr(self, "_analytics_subtitle"):
            self._analytics_subtitle.config(
                text=f"Per-student attendance for {self._sel_subject['name']}"
            )

        self._refresh_sessions_table()
        self._refresh_session_combo()
        self._refresh_student_roster()
        self._refresh_attendance_table()
        if self._current_page == "analytics":
            self._refresh_analytics()

    def _refresh_session_combo(self):
        choices = [f"{s['title']} - {s['date']}" for s in self._sessions_data]
        self._session_choice.config(values=choices)
        if self._sel_session:
            self._session_choice_var.set(f"{self._sel_session['title']} - {self._sel_session['date']}")
        else:
            self._session_choice_var.set("")

    def _on_session_choice(self, _event):
        idx = self._session_choice.current()
        if idx < 0 or idx >= len(self._sessions_data):
            return
        self._sel_session = self._sessions_data[idx]
        status = "🟢 OPEN" if self._sel_session["is_open"] else "🔴 CLOSED"
        self._live_status_lbl.set(status, "success" if self._sel_session["is_open"] else "danger")
        self._refresh_attendance_table()

    def _on_session_select(self, _event):
        sel = self._session_tree.selection()
        if not sel:
            return
        idx = self._session_tree.index(sel[0])
        if idx < len(self._sessions_data):
            self._sel_session = self._sessions_data[idx]
            status = "🟢 OPEN" if self._sel_session["is_open"] else "🔴 CLOSED"
            self._live_status_lbl.set(status, "success" if self._sel_session["is_open"] else "danger")
            self._session_choice_var.set(f"{self._sel_session['title']} - {self._sel_session['date']}")
            self._refresh_attendance_table()

    def _refresh_notifications(self):
        count = queries.unread_count(self._user["id"])
        self._notif_badge.config(text=f"({count})" if count else "")

    # ── Auto-refresh ───────────────────────────────────────────────────────

    def _start_refresh(self):
        self._do_refresh()

    def _do_refresh(self):
        if self._done:
            return
        try:
            self._refresh_notifications()
            if self._sel_subject:
                self._subject_data_refresh()
            if self._current_page == "dashboard":
                self._refresh_dashboard()
        except Exception:
            pass
        self._refresh_after_id = self.after(self.AUTO_REFRESH_MS, self._do_refresh)

    # ══════════════════════════════════════════════════════════════════════
    #  ACTIONS (dialogs, export, QR, notifications)
    # ══════════════════════════════════════════════════════════════════════

    def _create_subject_dialog(self):
        """Popup to create a new subject."""
        dlg = tk.Toplevel(self)
        dlg.title("New Subject")
        dlg.configure(bg=T.BG_DARK)
        dlg.resizable(False, False)
        center_window(dlg, 400, 360)
        dlg.grab_set()

        outer = tk.Frame(dlg, bg=T.BG_DARK, padx=T.PAD_LG, pady=T.PAD_LG)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="Create Subject", bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H2).pack(anchor="w", pady=(0, T.PAD_MD))

        card = tk.Frame(outer, bg=T.BG_CARD,
                         highlightbackground=T.BORDER, highlightthickness=1,
                         padx=T.PAD_LG, pady=T.PAD_LG)
        card.pack(fill="x")

        tk.Label(card, text="Subject Name", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        name_var = tk.StringVar()
        ttk.Entry(card, textvariable=name_var, style="TEntry").pack(fill="x", pady=(2, T.PAD_SM))

        tk.Label(card, text="Subject Code (auto-generated)", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        code_var = tk.StringVar(value=generate_subject_code())
        code_frame = tk.Frame(card, bg=T.BG_CARD)
        code_frame.pack(fill="x", pady=(2, T.PAD_SM))
        ttk.Entry(code_frame, textvariable=code_var, style="TEntry").pack(side="left", fill="x", expand=True)
        IconButton(code_frame, "⟳", command=lambda: code_var.set(generate_subject_code()),
                   bg=T.BG_CARD2, hover_bg=T.BORDER, fg=T.ACCENT_LIGHT,
                   font=T.FONT_SMALL).pack(side="left", padx=(4, 0))

        err_var = tk.StringVar()
        tk.Label(card, textvariable=err_var, bg=T.BG_CARD,
                 fg=T.DANGER, font=T.FONT_SMALL).pack(fill="x")

        def do_create():
            name = name_var.get().strip()
            code = code_var.get().strip().upper()
            if not name:
                err_var.set("⚠  Subject name required.")
                return
            if not code:
                err_var.set("⚠  Subject code required.")
                return
            if queries.subject_code_exists(code):
                err_var.set("⚠  Code already exists. Regenerate.")
                return
            try:
                queries.create_subject(code, name, self._profile["id"])
                messagebox.showinfo("Created", f"✅ Subject '{name}' created!\nCode: {code}", parent=dlg)
                dlg.destroy()
                self._selected_subject_index = None
                self._load_subjects()
            except Exception as e:
                err_var.set(f"⚠  Error: {e}")

        IconButton(card, "Create Subject", command=do_create,
                   font=T.FONT_H3).pack(fill="x", ipady=4, pady=(T.PAD_SM, 0))
        dlg.bind("<Return>", lambda _: do_create())

    def _create_session_dialog(self):
        if not self._sel_subject:
            messagebox.showwarning("No Subject", "Please select a subject first.", parent=self)
            self._select_page("subjects")
            return
        from gui.create_session_page import CreateSessionDialog
        CreateSessionDialog(self, self._sel_subject,
                             on_created_callback=lambda _sid: self._subject_data_refresh())

    def _toggle_session(self, open_: bool):
        if not self._sel_session:
            messagebox.showwarning("No Session", "Please select a session first.", parent=self)
            return
        queries.toggle_session(self._sel_session["id"], open_)
        action = "opened" if open_ else "closed"
        self._toast.show(f"Session {action}.", "success")
        self._subject_data_refresh()

    def _show_qr(self):
        if not self._sel_session:
            messagebox.showwarning("No Session", "Please select a session.", parent=self)
            return
        from utils.qr_code import generate_session_qr
        path = generate_session_qr(
            self._sel_session["id"],
            self._sel_subject["subject_code"] if self._sel_subject else "UNK"
        )
        if not path:
            messagebox.showerror("QR Error", "Failed to generate QR code.\nEnsure qrcode and pillow are installed.", parent=self)
            return

        qr_win = tk.Toplevel(self)
        qr_win.title("Session QR Code")
        qr_win.configure(bg=T.BG_DARK)
        center_window(qr_win, 360, 420)
        qr_win.transient(self)
        qr_win.lift()
        qr_win.focus_force()
        qr_win.attributes("-topmost", True)
        qr_win.after(200, lambda: qr_win.attributes("-topmost", False))

        try:
            from PIL import Image, ImageTk
            img = Image.open(path).resize((280, 280), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(qr_win, image=photo, bg=T.BG_DARK)
            lbl.image = photo
            lbl.pack(pady=T.PAD_LG)
        except Exception:
            tk.Label(qr_win, text=f"QR saved to:\n{path}",
                     bg=T.BG_DARK, fg=T.TEXT_PRIMARY,
                     font=T.FONT_SMALL, wraplength=320).pack(pady=T.PAD_LG)

        tk.Label(qr_win,
                 text=f"Session: {self._sel_session['title']}\nStudents can scan to sign attendance.",
                 bg=T.BG_DARK, fg=T.TEXT_SECONDARY, font=T.FONT_SMALL,
                 justify="center").pack()

        IconButton(qr_win, "Close", command=qr_win.destroy,
                   font=T.FONT_SMALL).pack(pady=T.PAD_SM)

    def _export(self, fmt: str):
        if not self._sel_session or not self._sel_subject:
            messagebox.showwarning("No Session", "Select a session to export.", parent=self)
            return
        records = queries.get_session_attendance(self._sel_session["id"])
        if not records:
            messagebox.showinfo("Empty", "No attendance records to export.", parent=self)
            return

        default_path = get_default_export_path(
            self._sel_subject["subject_code"], self._sel_session["title"], fmt
        )
        filetypes = [("Excel files", "*.xlsx")] if fmt == "xlsx" else [("PDF files", "*.pdf")]
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=f".{fmt}",
            initialfile=os.path.basename(default_path), filetypes=filetypes
        )
        if not path:
            return
        try:
            if fmt == "xlsx":
                export_to_excel(records, self._sel_subject["name"], self._sel_session["title"], path)
            else:
                export_to_pdf(records, self._sel_subject["name"], self._sel_session["title"], path)
            self._toast.show(f"Exported to {os.path.basename(path)}", "success")
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self)

    def _show_notifications(self):
        notifs = queries.get_notifications(self._user["id"])
        queries.mark_notifications_read(self._user["id"])

        dlg = tk.Toplevel(self)
        dlg.title("Notifications")
        dlg.configure(bg=T.BG_DARK)
        center_window(dlg, 440, 400)

        tk.Label(dlg, text="Notifications", bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H2,
                 padx=T.PAD_MD, pady=T.PAD_SM).pack(anchor="w")

        sf = ScrollableFrame(dlg, bg=T.BG_DARK)
        sf.pack(fill="both", expand=True, padx=T.PAD_MD, pady=T.PAD_SM)

        if not notifs:
            tk.Label(sf.inner, text="No notifications yet.",
                     bg=T.BG_DARK, fg=T.TEXT_MUTED, font=T.FONT_BODY).pack(pady=T.PAD_LG)
        for n in notifs:
            row = tk.Frame(sf.inner, bg=T.BG_CARD,
                           highlightbackground=T.BORDER, highlightthickness=1,
                           padx=T.PAD_SM, pady=T.PAD_SM)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=n["message"], bg=T.BG_CARD,
                     fg=T.TEXT_PRIMARY, font=T.FONT_SMALL,
                     wraplength=380, justify="left").pack(anchor="w")
            tk.Label(row, text=n["created_at"], bg=T.BG_CARD,
                     fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(anchor="e")

        self._refresh_notifications()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _on_close(self):
        self._done = True
        if self._refresh_after_id:
            self.after_cancel(self._refresh_after_id)
        self.destroy()
        if self._on_close_cb:
            self._on_close_cb()
