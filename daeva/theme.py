"""Cores e folha de estilo do app (tema escuro, pensado para ficar ao lado do jogo)."""

BG = "#0d1420"
SURFACE = "#141d2b"
RAISE = "#1b2638"
LINE = "#26344c"
FG = "#e5eaf2"
MUTED = "#8696ae"
ACCENT = "#e4ad55"
ACCENT_INK = "#1a1206"
OK = "#5bc6a3"
WARN = "#ef8a5c"
LIVE = "#7fb2ff"

QSS = f"""
* {{ font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; color: {FG}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: {SURFACE}; color: {MUTED}; padding: 7px 16px; border: 1px solid {LINE};
  border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; }}
QTabBar::tab:selected {{ background: {RAISE}; color: {FG}; }}
QLabel#title {{ font-size: 15pt; font-weight: 600; letter-spacing: 0.5px; }}
QLabel#muted, QLabel.muted {{ color: {MUTED}; font-size: 9pt; }}
QLabel#section {{ color: {MUTED}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1.2px; }}
QLabel#next {{ color: {MUTED}; }}
QFrame#row {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px; }}
QFrame#row[state="live"] {{ border-color: {LIVE}; }}
QFrame#row[state="soon"] {{ border-color: {ACCENT}; }}
QFrame#row[state="ready"] {{ border-color: {OK}; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#stat {{ background: {RAISE}; border-radius: 9px; }}
QLabel#bigval {{ font-size: 18pt; font-weight: 600; }}
QLabel#name {{ font-size: 13pt; font-weight: 600; }}
QLabel#countdown {{ font-size: 12pt; font-weight: 600; font-family: "Cascadia Mono", Consolas, monospace; }}
QLabel#tag {{ color: {MUTED}; border: 1px solid {LINE}; border-radius: 4px; padding: 0 5px; font-size: 8pt; }}
QLabel#tagUnc {{ color: {MUTED}; border: 1px dashed {MUTED}; border-radius: 4px; padding: 0 5px; font-size: 8pt; }}
QLabel#up {{ color: {OK}; font-size: 9pt; }}
QLabel#err {{ color: {WARN}; font-size: 9pt; }}
QPushButton {{ background: {RAISE}; border: 1px solid {LINE}; border-radius: 7px; padding: 5px 11px; }}
QPushButton:hover {{ border-color: {MUTED}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QPushButton#primary {{ background: {ACCENT}; color: {ACCENT_INK}; border-color: {ACCENT}; font-weight: 600; }}
QPushButton#seg {{ border-radius: 6px; padding: 4px 12px; }}
QPushButton#seg:checked {{ background: {ACCENT}; color: {ACCENT_INK}; border-color: {ACCENT}; font-weight: 600; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {LINE}; background: {RAISE}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QComboBox, QSpinBox, QLineEdit, QTimeEdit {{ background: {RAISE}; border: 1px solid {LINE}; border-radius: 7px; padding: 5px 8px; }}
QComboBox QAbstractItemView {{ background: {RAISE}; selection-background-color: {ACCENT}; selection-color: {ACCENT_INK}; }}
QToolTip {{ background: {RAISE}; color: {FG}; border: 1px solid {LINE}; padding: 4px; }}
QScrollBar:vertical {{ background: {BG}; width: 8px; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QDialog {{ background: {SURFACE}; }}
"""
