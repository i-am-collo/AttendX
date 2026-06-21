"""
gui/theme.py
------------
Centralized design tokens for the dark-mode UI.
All colours, fonts, radii, and spacing live here — one place to change everything.
"""

# ── Palette ─────────────────────────────────────────────────────────────────
BG_DEEP       = "#0D0D1A"   # Deepest background
BG_DARK       = "#12121F"   # Main window background
BG_CARD       = "#1A1A2E"   # Card / panel background
BG_CARD2      = "#16213E"   # Alternate card
BG_INPUT      = "#1E1E32"   # Input field background
BG_HOVER      = "#252540"   # Hover state

ACCENT        = "#7C3AED"   # Primary accent — violet
ACCENT_HOVER  = "#6D28D9"
ACCENT_LIGHT  = "#A78BFA"   # Light accent for badges / chips
ACCENT_GLOW   = "#7C3AED40" # Glow (with alpha)

SUCCESS       = "#10B981"   # Green
SUCCESS_DARK  = "#065F46"
WARNING       = "#F59E0B"   # Amber
DANGER        = "#EF4444"   # Red
DANGER_DARK   = "#7F1D1D"
INFO          = "#3B82F6"   # Blue

TEXT_PRIMARY  = "#F1F5F9"   # Near-white
TEXT_SECONDARY= "#94A3B8"   # Muted slate
TEXT_MUTED    = "#475569"   # Very muted
TEXT_ACCENT   = "#C4B5FD"   # Violet-tinted text

BORDER        = "#2D2D4A"   # Subtle border
BORDER_FOCUS  = "#7C3AED"   # Focused border

# ── Fonts ────────────────────────────────────────────────────────────────────
FONT_FAMILY   = "Segoe UI"   # Windows; falls back gracefully on Linux/Mac

FONT_GIANT    = (FONT_FAMILY, 28, "bold")
FONT_H1       = (FONT_FAMILY, 20, "bold")
FONT_H2       = (FONT_FAMILY, 15, "bold")
FONT_H3       = (FONT_FAMILY, 13, "bold")
FONT_BODY     = (FONT_FAMILY, 11)
FONT_BODY_MED = (FONT_FAMILY, 11, "bold")
FONT_SMALL    = (FONT_FAMILY, 9)
FONT_MONO     = ("Consolas", 10)
FONT_BADGE    = (FONT_FAMILY, 8, "bold")

# ── Geometry ─────────────────────────────────────────────────────────────────
PAD_XS  = 4
PAD_SM  = 8
PAD_MD  = 16
PAD_LG  = 24
PAD_XL  = 40

RADIUS  = 8   # used in Canvas-drawn rounded rects

# ── ttk Style Names ───────────────────────────────────────────────────────────
STYLE_TREE        = "Dark.Treeview"
STYLE_TREE_HEAD   = "Dark.Treeview.Heading"
STYLE_NOTEBOOK    = "Dark.TNotebook"
STYLE_TAB         = "Dark.TNotebook.Tab"
STYLE_SCROLLBAR   = "Dark.Vertical.TScrollbar"
STYLE_HSCROLLBAR  = "Dark.Horizontal.TScrollbar"


def apply_global_ttk_theme(style):
    """
    Configure ttk.Style with our dark theme.
    Call once at application startup: apply_global_ttk_theme(ttk.Style())
    """
    import tkinter.ttk as ttk

    style.theme_use("clam")

    # ── Frame / Label ────────────────────────────────────────────────────────
    style.configure("TFrame",       background=BG_DARK)
    style.configure("Card.TFrame",  background=BG_CARD)
    style.configure("TLabel",       background=BG_DARK,   foreground=TEXT_PRIMARY,   font=FONT_BODY)
    style.configure("Card.TLabel",  background=BG_CARD,   foreground=TEXT_PRIMARY)
    style.configure("Muted.TLabel", background=BG_DARK,   foreground=TEXT_SECONDARY, font=FONT_SMALL)
    style.configure("H1.TLabel",    background=BG_DARK,   foreground=TEXT_PRIMARY,   font=FONT_H1)
    style.configure("H2.TLabel",    background=BG_DARK,   foreground=TEXT_PRIMARY,   font=FONT_H2)
    style.configure("Accent.TLabel",background=BG_DARK,   foreground=ACCENT_LIGHT,   font=FONT_H2)

    # ── Entry ────────────────────────────────────────────────────────────────
    style.configure("TEntry",
        fieldbackground = BG_INPUT,
        background      = BG_INPUT,
        foreground      = TEXT_PRIMARY,
        insertcolor     = TEXT_PRIMARY,
        bordercolor     = BORDER,
        lightcolor      = BG_INPUT,
        darkcolor       = BG_INPUT,
        font            = FONT_BODY,
        padding         = (PAD_SM, PAD_XS),
    )
    style.map("TEntry",
        bordercolor=[("focus", BORDER_FOCUS)],
        lightcolor =[("focus", BORDER_FOCUS)],
    )

    # ── Button ───────────────────────────────────────────────────────────────
    style.configure("TButton",
        background  = ACCENT,
        foreground  = TEXT_PRIMARY,
        font        = FONT_H3,
        padding     = (PAD_MD, PAD_SM),
        relief      = "flat",
        borderwidth = 0,
    )
    style.map("TButton",
        background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
        relief    =[("pressed", "flat")],
    )

    style.configure("Ghost.TButton",
        background  = BG_CARD,
        foreground  = TEXT_PRIMARY,
        font        = FONT_BODY,
        padding     = (PAD_SM, PAD_XS),
        relief      = "flat",
        borderwidth = 0,
    )
    style.map("Ghost.TButton",
        background=[("active", BG_HOVER)],
    )

    style.configure("Danger.TButton",
        background  = DANGER,
        foreground  = TEXT_PRIMARY,
        font        = FONT_BODY,
        padding     = (PAD_SM, PAD_XS),
        relief      = "flat",
    )
    style.map("Danger.TButton",
        background=[("active", "#DC2626")],
    )

    style.configure("Success.TButton",
        background  = SUCCESS,
        foreground  = "#FFFFFF",
        font        = FONT_BODY,
        padding     = (PAD_SM, PAD_XS),
        relief      = "flat",
    )
    style.map("Success.TButton",
        background=[("active", "#059669")],
    )

    # ── Combobox ─────────────────────────────────────────────────────────────
    style.configure("TCombobox",
        fieldbackground = BG_INPUT,
        background      = BG_INPUT,
        foreground      = TEXT_PRIMARY,
        selectbackground= ACCENT,
        selectforeground= TEXT_PRIMARY,
        arrowcolor      = TEXT_SECONDARY,
        font            = FONT_BODY,
    )

    # ── Treeview ─────────────────────────────────────────────────────────────
    style.configure(STYLE_TREE,
        background       = BG_CARD,
        fieldbackground  = BG_CARD,
        foreground       = TEXT_PRIMARY,
        font             = FONT_BODY,
        rowheight        = 38,
        borderwidth      = 0,
    )
    style.configure(STYLE_TREE_HEAD,
        background  = BG_CARD2,
        foreground  = ACCENT_LIGHT,
        font        = FONT_H3,
        relief      = "flat",
        padding     = (PAD_SM, PAD_SM),
    )
    style.map(STYLE_TREE,
        background=[("selected", ACCENT)],
        foreground=[("selected", TEXT_PRIMARY)],
    )

    # ── Notebook / Tabs ───────────────────────────────────────────────────────
    style.configure(STYLE_NOTEBOOK, background=BG_DARK, borderwidth=0, tabmargins=[0, PAD_SM, 0, 0])
    style.configure(STYLE_TAB,
        background  = BG_DARK,
        foreground  = TEXT_SECONDARY,
        font        = FONT_BODY_MED,
        padding     = (PAD_LG, PAD_SM),
        borderwidth = 0,
    )
    style.map(STYLE_TAB,
        background=[("selected", BG_CARD),  ("active", BG_HOVER)],
        foreground=[("selected", ACCENT_LIGHT), ("active", TEXT_PRIMARY)],
    )

    # ── Scrollbar ────────────────────────────────────────────────────────────
    style.configure(STYLE_SCROLLBAR,
        background  = BG_HOVER,
        troughcolor = BG_DEEP,
        arrowcolor  = TEXT_MUTED,
        borderwidth = 0,
        width       = 12,
    )
    style.map(STYLE_SCROLLBAR,
        background=[("active", ACCENT)],
    )
    style.configure(STYLE_HSCROLLBAR,
        background  = BG_HOVER,
        troughcolor = BG_DEEP,
        arrowcolor  = TEXT_MUTED,
        borderwidth = 0,
        width       = 12,
    )
    style.map(STYLE_HSCROLLBAR,
        background=[("active", ACCENT)],
    )

    # ── Separator ────────────────────────────────────────────────────────────
    style.configure("TSeparator", background=BORDER)

    # ── Progressbar ──────────────────────────────────────────────────────────
    style.configure("TProgressbar",
        troughcolor = BG_INPUT,
        background  = ACCENT,
        thickness   = 8,
    )
