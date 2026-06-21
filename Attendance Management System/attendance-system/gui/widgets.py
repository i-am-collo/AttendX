"""
gui/widgets.py
--------------
Reusable, styled custom widgets used across all pages.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import gui.theme as T


# ── Helper: center a Toplevel on screen ────────────────────────────────────

def center_window(win: tk.Tk | tk.Toplevel, w: int, h: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x  = (sw - w) // 2
    y  = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# ── Separator ──────────────────────────────────────────────────────────────

def HSep(parent, **grid_kw):
    sep = ttk.Separator(parent, orient="horizontal")
    sep.grid(sticky="ew", **grid_kw)
    return sep


# ── Card Frame ─────────────────────────────────────────────────────────────

class Card(tk.Frame):
    """Rounded-corner card drawn on a Canvas background."""
    def __init__(self, parent, bg=T.BG_CARD, border_color=T.BORDER, **kw):
        super().__init__(parent, bg=bg, padx=T.PAD_MD, pady=T.PAD_MD, **kw)
        self.config(
            highlightbackground=border_color,
            highlightthickness=1,
        )


# ── Badge ──────────────────────────────────────────────────────────────────

class Badge(tk.Label):
    """Small coloured pill badge."""
    _PRESETS = {
        "success": (T.SUCCESS_DARK, T.SUCCESS),
        "danger":  (T.DANGER_DARK,  T.DANGER),
        "info":    ("#1E3A5F",       T.INFO),
        "warning": ("#78350F",       T.WARNING),
        "accent":  ("#3B1F7A",       T.ACCENT_LIGHT),
        "muted":   (T.BG_CARD2,      T.TEXT_SECONDARY),
    }

    def __init__(self, parent, text: str = "", preset: str = "accent", **kw):
        bg, fg = self._PRESETS.get(preset, (T.BG_CARD2, T.TEXT_PRIMARY))
        super().__init__(
            parent,
            text        = f"  {text}  ",
            font        = T.FONT_BADGE,
            bg          = bg,
            fg          = fg,
            padx        = 6,
            pady        = 2,
            relief      = "flat",
            **kw
        )

    def set(self, text: str, preset: str | None = None):
        self.config(text=f"  {text}  ")
        if preset:
            bg, fg = self._PRESETS.get(preset, (T.BG_CARD2, T.TEXT_PRIMARY))
            self.config(bg=bg, fg=fg)


# ── Icon Button ────────────────────────────────────────────────────────────

class IconButton(tk.Button):
    def __init__(self, parent, text="", command=None,
                 bg=T.ACCENT, hover_bg=T.ACCENT_HOVER,
                 fg=T.TEXT_PRIMARY, font=T.FONT_H3, **kw):
        # Set defaults but allow the caller to override them
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 7)

        super().__init__(
            parent,
            text             = text,
            command          = command,
            bg               = bg,
            fg               = fg,
            activebackground = hover_bg,
            activeforeground = fg,
            font             = font,
            relief           = "flat",
            cursor           = "hand2",
            bd               = 0,
            **kw
        )
        self._bg       = bg
        self._hover_bg = hover_bg
        self.bind("<Enter>", lambda _: self.config(bg=self._hover_bg))
        self.bind("<Leave>", lambda _: self.config(bg=self._bg))


# ── Labelled Entry ─────────────────────────────────────────────────────────

class LabelledEntry(tk.Frame):
    """Label + Entry combo used in forms."""
    def __init__(self, parent, label: str, show: str = "",
                 placeholder: str = "", **kw):
        super().__init__(parent, bg=T.BG_DARK, **kw)
        self._placeholder = placeholder

        tk.Label(self, text=label, bg=T.BG_DARK,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")

        self.var   = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, show=show,
                               style="TEntry", font=T.FONT_BODY)
        self.entry.pack(fill="x", pady=(2, 0))

        if placeholder:
            self._set_placeholder()
            self.entry.bind("<FocusIn>",  self._clear_placeholder)
            self.entry.bind("<FocusOut>", self._restore_placeholder)

    def _set_placeholder(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self._placeholder)
        self.entry.config(foreground=T.TEXT_MUTED)

    def _clear_placeholder(self, _=None):
        if self.get() == self._placeholder:
            self.entry.delete(0, "end")
            self.entry.config(foreground=T.TEXT_PRIMARY)

    def _restore_placeholder(self, _=None):
        if not self.entry.get():
            self._set_placeholder()

    def get(self) -> str:
        val = self.var.get()
        return "" if val == self._placeholder else val

    def set(self, value: str):
        self.var.set(value)


# ── Toast Notification ──────────────────────────────────────────────────────

class Toast:
    """Temporary status bar message shown at the bottom of a window."""
    def __init__(self, parent: tk.Misc):
        self._label = tk.Label(
            parent,
            text   = "",
            bg     = T.BG_CARD2,
            fg     = T.TEXT_PRIMARY,
            font   = T.FONT_SMALL,
            anchor = "w",
            padx   = T.PAD_SM,
        )
        self._label.pack(side="bottom", fill="x")
        self._after_id = None

    def show(self, message: str, kind: str = "info", duration_ms: int = 3500):
        colors = {
            "info":    T.INFO,
            "success": T.SUCCESS,
            "warning": T.WARNING,
            "error":   T.DANGER,
        }
        self._label.config(text=f"  {message}", fg=colors.get(kind, T.INFO))
        if self._after_id:
            self._label.after_cancel(self._after_id)
        self._after_id = self._label.after(duration_ms, lambda: self._label.config(text=""))


# ── Scrollable Frame ───────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    """A vertically scrollable container."""
    def __init__(self, parent, bg=T.BG_DARK, **kw):
        super().__init__(parent, bg=bg, **kw)

        canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                  command=canvas.yview,
                                  style=T.STYLE_SCROLLBAR)
        self.inner = tk.Frame(canvas, bg=bg)

        self.inner.bind("<Configure>", lambda _: canvas.configure(
            scrollregion=canvas.bbox("all")
        ))

        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left",   fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))


# ── Treeview Builder ────────────────────────────────────────────────────────

def build_treeview(parent, columns: list[dict], height: int = 14) -> ttk.Treeview:
    """
    columns: list of {"id": str, "text": str, "width": int, "anchor": str}
    Returns a fully configured Treeview with a scrollbar.
    """
    frame = tk.Frame(parent, bg=T.BG_CARD)
    frame.pack(fill="both", expand=True)

    col_ids = [c["id"] for c in columns]
    tree = ttk.Treeview(frame, columns=col_ids, show="headings",
                        height=height, style=T.STYLE_TREE)

    for c in columns:
        tree.heading(c["id"], text=c["text"])
        tree.column(c["id"], width=c.get("width", 120),
                    anchor=c.get("anchor", "w"), stretch=True)

    vsb = ttk.Scrollbar(frame, orient="vertical",
                        command=tree.yview, style=T.STYLE_SCROLLBAR)
    hsb = ttk.Scrollbar(frame, orient="horizontal",
                        command=tree.xview, style=T.STYLE_HSCROLLBAR)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    # Alternating row colours
    tree.tag_configure("even", background=T.BG_CARD)
    tree.tag_configure("odd",  background=T.BG_CARD2)
    tree.tag_configure("signed",   background="#0D3321", foreground=T.SUCCESS)
    tree.tag_configure("unsigned", background=T.BG_CARD,  foreground=T.TEXT_PRIMARY)
    tree.tag_configure("hover", background=T.BG_HOVER, foreground=T.TEXT_PRIMARY)

    tree._last_hover_item = None

    def _on_motion(event):
        item = tree.identify_row(event.y)
        if item == tree._last_hover_item:
            return
        if tree._last_hover_item and tree.exists(tree._last_hover_item):
            index = tree.index(tree._last_hover_item)
            tree.item(tree._last_hover_item, tags=("even" if index % 2 == 0 else "odd",))
        if item:
            tree.item(item, tags=("hover",))
        tree._last_hover_item = item

    def _on_leave(_event):
        item = tree._last_hover_item
        if item and tree.exists(item):
            index = tree.index(item)
            tree.item(item, tags=("even" if index % 2 == 0 else "odd",))
        tree._last_hover_item = None

    tree.bind("<Motion>", _on_motion)
    tree.bind("<Leave>", _on_leave)

    return tree


def populate_tree(tree: ttk.Treeview, rows: list[list]):
    """Clear and repopulate a Treeview."""
    for item in tree.get_children():
        tree.delete(item)
    for i, row in enumerate(rows):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", values=row, tags=(tag,))


# ── Section Header ─────────────────────────────────────────────────────────

def section_header(parent, title: str, subtitle: str = "", bg=T.BG_DARK):
    frm = tk.Frame(parent, bg=bg)
    tk.Label(frm, text=title, bg=bg,
             fg=T.TEXT_PRIMARY, font=T.FONT_H2).pack(anchor="w")
    if subtitle:
        tk.Label(frm, text=subtitle, bg=bg,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
    return frm


# ── Stat Card ───────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    """Mini KPI card: icon · value · label."""
    def __init__(self, parent, icon: str, value: str,
                 label: str, bg=T.BG_CARD, accent=T.ACCENT_LIGHT, **kw):
        super().__init__(parent, bg=bg, padx=T.PAD_MD, pady=T.PAD_SM,
                         relief="flat",
                         highlightbackground=T.BORDER, highlightthickness=1, **kw)
        self._bg = bg
        self._hover_bg = T.BG_HOVER
        tk.Label(self, text=icon, bg=bg, fg=accent, font=(T.FONT_FAMILY, 15)).pack(anchor="w")
        self.val_lbl = tk.Label(self, text=value, bg=bg,
                                fg=T.TEXT_PRIMARY, font=T.FONT_H2)
        self.val_lbl.pack(anchor="w", pady=(2, 0))
        tk.Label(self, text=label, bg=bg,
                 fg=T.TEXT_SECONDARY, font=T.FONT_SMALL).pack(anchor="w")
        self.bind("<Enter>", self._hover)
        self.bind("<Leave>", self._unhover)
        for child in self.winfo_children():
            child.bind("<Enter>", self._hover)
            child.bind("<Leave>", self._unhover)

    def update_value(self, value: str):
        self.val_lbl.config(text=value)

    def _hover(self, _event):
        self.config(bg=self._hover_bg)
        for child in self.winfo_children():
            child.config(bg=self._hover_bg)

    def _unhover(self, _event):
        self.config(bg=self._bg)
        for child in self.winfo_children():
            child.config(bg=self._bg)
