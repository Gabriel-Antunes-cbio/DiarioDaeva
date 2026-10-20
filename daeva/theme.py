"""Temas do app: cores, fontes e folha de estilo.

Um layout só (textos da HUD, moldura de grimório, timer com linha pontilhada) e vários temas de cor e fonte.
As cores atuais ficam expostas como atributos do módulo (theme.FG, theme.MUTED...) para os widgets que
desenham na mão; `apply()` troca o tema e atualiza esses atributos.
"""
from __future__ import annotations

from pathlib import Path

# ----------------------------------------------------------------- temas
# bg: fundo · panel: painéis · line: bordas · soft: segunda moldura · ink: texto · muted: texto apagado
# label: rótulos HUD · gold: números e destaques · track: trilha pontilhada · dim: trilha vazia
# act/act_ink: botão principal · ok/warn: estados
THEMES: dict[str, dict] = {
    "ely": {"name": "Elyos", "light": True, "c": dict(
        bg="#EFE6D2", panel="#F8F1E1", line="#C9B48A", soft="#DCCBA4", ink="#2A2216", muted="#5E5038",
        label="#7A5A12", gold="#8A6414", track="#B08A3A", dim="#D6C59C", act="#1F4E86", act_ink="#FFFFFF",
        ok="#2A6B44", warn="#A4461E")},
    "asm": {"name": "Asmodiano", "c": dict(
        bg="#15101A", panel="#1F1726", line="#4A3858", soft="#33283F", ink="#EDE5F3", muted="#AFA3BE",
        label="#C9AEF7", gold="#E8607C", track="#E8607C", dim="#3A2E48", act="#E8607C", act_ink="#1C0D14",
        ok="#78D2A2", warn="#F2B25C")},
    "pix": {"name": "Pixel", "bw": 3, "c": dict(
        bg="#000000", panel="#000000", line="#FFFFFF", soft="#000000", ink="#FFFFFF", muted="#A8A8A8",
        label="#FFFFFF", gold="#FFE14A", track="#FFE14A", dim="#444444", act="#FF9A2E", act_ink="#000000",
        ok="#5CE05C", warn="#FF5A5A"),
        "fonts": dict(name="Pixelify Sans", num="Pixelify Sans", lbl="Silkscreen", body="VT323"), "body_scale": 1.35},
    "mad": {"name": "Madrugada", "c": dict(
        bg="#14120F", panel="#1A1814", line="#2E2A24", soft="#211E19", ink="#C9C0B0", muted="#8C8475",
        label="#A8977A", gold="#C7A56A", track="#A88B57", dim="#3A342B", act="#3A3226", act_ink="#D9C9A8",
        ok="#7FA488", warn="#C08A5E"),
        "fonts": dict(name="Barlow")},
    "oled": {"name": "OLED", "c": dict(
        bg="#000000", panel="#000000", line="#1E1E1E", soft="#0C0C0C", ink="#D6D6D6", muted="#7C7C7C",
        label="#6FB7A8", gold="#8FD3C4", track="#4E8F82", dim="#1C1C1C", act="#13261F", act_ink="#BFE8DD",
        ok="#6FBF8A", warn="#D8A060"),
        "fonts": dict(name="Barlow")},
    "term": {"name": "Terminal", "c": dict(
        bg="#040A05", panel="#06100A", line="#1F5C33", soft="#0C2414", ink="#5CF08A", muted="#2F9B55",
        label="#5CF08A", gold="#7CFFA4", track="#5CF08A", dim="#163D23", act="#5CF08A", act_ink="#040A05",
        ok="#5CF08A", warn="#F0D25C"),
        "fonts": dict(name="IBM Plex Mono", num="VT323", lbl="IBM Plex Mono", body="IBM Plex Mono"),
        "body_scale": 0.95, "num_scale": 1.35},
    "got": {"name": "Gótico", "c": dict(
        bg="#0E0A0B", panel="#170F11", line="#4A1A22", soft="#2A1216", ink="#EAD9D3", muted="#A88E89",
        label="#C24450", gold="#D23A4A", track="#8E1F2B", dim="#3A1A1E", act="#8E1F2B", act_ink="#F3E6E0",
        ok="#9DB58A", warn="#E07A4C"),
        "fonts": dict(name="UnifrakturMaguntia", num="IM FELL English", lbl="EB Garamond", body="EB Garamond"),
        "body_scale": 1.1},
    "sumi": {"name": "Sumi claro", "light": True, "c": dict(
        bg="#F2EDE3", panel="#FAF7F0", line="#3A3631", soft="#E6DFD2", ink="#1E1C19", muted="#6B655C",
        label="#1E1C19", gold="#1E1C19", track="#1E1C19", dim="#CFC7B8", act="#B3261E", act_ink="#FFFFFF",
        ok="#3C6E47", warn="#B3261E"),
        "fonts": dict(name="Shippori Mincho Medium", num="Shippori Mincho Medium")},
    "sumid": {"name": "Sumi escuro", "c": dict(
        bg="#1A1916", panel="#22201C", line="#6A645A", soft="#2A2824", ink="#EDE6D8", muted="#A39B8C",
        label="#EDE6D8", gold="#EDE6D8", track="#EDE6D8", dim="#3A3732", act="#C8372D", act_ink="#FFFFFF",
        ok="#7FB08A", warn="#E0584C"),
        "fonts": dict(name="Shippori Mincho Medium", num="Shippori Mincho Medium")},
}
DEFAULT_FONTS = dict(name="IM FELL English", num="Oxanium", lbl="Oxanium", body="Barlow")

# cor de destaque: (tom para tema claro, tom para tema escuro)
ACCENTS: dict[str, tuple[str, str, str]] = {
    "def": ("Padrão do tema", "", ""),
    "azul": ("Azul", "#1F4E86", "#6FA8FF"),
    "verde": ("Verde", "#2A6B44", "#5BD08F"),
    "rubi": ("Rubi", "#A3243E", "#F06A84"),
    "ambar": ("Âmbar", "#8A5A08", "#F2B547"),
    "violeta": ("Violeta", "#5B3FA8", "#B79CFF"),
}
SIZES = {"normal": ("Normal", 1.0), "grande": ("Grande", 1.15)}

# ----------------------------------------------------------------- cores atuais (para quem desenha na mão)
C: dict[str, str] = {}
BG = SURFACE = RAISE = LINE = FG = MUTED = ACCENT = ACCENT_INK = OK = WARN = LIVE = DIM = TRACK = ""
FONTS: dict[str, str] = dict(DEFAULT_FONTS)
SQUARE = True
BORDER = 1


def colors(theme_id: str, accent: str = "def") -> dict[str, str]:
    t = THEMES.get(theme_id) or THEMES["ely"]
    c = dict(t["c"])
    a = ACCENTS.get(accent)
    if a and a[1]:
        tone = a[1] if t.get("light") else a[2]
        c.update(gold=tone, track=tone, act=tone, act_ink="#FFFFFF" if t.get("light") else "#10101A")
    return c


def _set_globals(c: dict, fonts: dict, bw: int) -> None:
    global C, BG, SURFACE, RAISE, LINE, FG, MUTED, ACCENT, ACCENT_INK, OK, WARN, LIVE, DIM, TRACK, FONTS, BORDER
    C = c
    BG, SURFACE, RAISE, LINE, FG, MUTED = c["bg"], c["panel"], c["soft"], c["line"], c["ink"], c["muted"]
    ACCENT, ACCENT_INK, OK, WARN, LIVE = c["gold"], c["act_ink"], c["ok"], c["warn"], c["act"]
    DIM, TRACK = c["dim"], c["track"]
    FONTS, BORDER = fonts, bw


def build_qss(theme_id: str = "ely", size: str = "normal", compact: bool = False, accent: str = "def") -> str:
    t = THEMES.get(theme_id) or THEMES["ely"]
    c = colors(theme_id, accent)
    f = dict(DEFAULT_FONTS, **t.get("fonts", {}))
    bw = int(t.get("bw", 1))
    _set_globals(c, f, bw)
    s = SIZES.get(size, SIZES["normal"])[1]
    body = 10 * s * t.get("body_scale", 1.0)
    num = s * t.get("num_scale", 1.0)
    pad = 6 if compact else 10
    fam = lambda k: f'"{f[k]}", "Segoe UI", sans-serif'  # noqa: E731
    return f"""
* {{ font-family: {fam('body')}; font-size: {body:.1f}pt; color: {c['ink']}; }}
QMainWindow, QWidget#root {{ background: {c['bg']}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c['bg']}; border: none; }}
QTabWidget::pane {{ border: none; border-top: {bw}px solid {c['line']}; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {c['muted']}; font-family: {fam('lbl')}; font-weight: 600;
  font-size: {8.5 * s:.1f}pt; padding: {pad - 3}px {9 if compact else 11}px; border: none;
  border-bottom: 2px solid transparent; margin-bottom: -{bw}px; }}
QTabBar::tab:selected {{ color: {c['ink']}; border-bottom: 2px solid {c['track']}; }}
QTabBar::tab:hover {{ color: {c['ink']}; }}
QTabBar QToolButton {{ background: {c['panel']}; border: {bw}px solid {c['line']}; }}
QLabel#title {{ font-family: {fam('name')}; font-size: {16 * s:.1f}pt; color: {c['ink']}; }}
QLabel#who, QLabel#muted, QLabel.muted {{ color: {c['muted']}; font-size: {9 * s * t.get('body_scale', 1.0):.1f}pt; }}
QLabel#section {{ color: {c['label']}; font-family: {fam('lbl')}; font-size: {8 * s:.1f}pt; font-weight: 600;
  letter-spacing: 1.6px; }}
QLabel#next {{ color: {c['muted']}; }}
QLabel#name {{ font-family: {fam('name')}; font-size: {13 * s:.1f}pt; color: {c['ink']}; }}
QLabel#heroName {{ font-family: {fam('name')}; font-size: {17 * s:.1f}pt; color: {c['ink']}; }}
QLabel#bigcount {{ font-family: {fam('num')}; font-size: {(26 if compact else 34) * num:.1f}pt; font-weight: 700;
  color: {c['gold']}; }}
QLabel#bigval {{ font-family: {fam('num')}; font-size: {17 * num:.1f}pt; font-weight: 700; color: {c['ink']}; }}
QLabel#countdown {{ font-family: {fam('num')}; font-size: {12 * num:.1f}pt; font-weight: 700; color: {c['gold']}; }}
QLabel#evtime {{ font-family: {fam('num')}; font-size: {10.5 * num:.1f}pt; font-weight: 700; color: {c['gold']}; }}
QLabel#evtime[warn="true"] {{ color: {c['warn']}; }}
QLabel#tag {{ color: {c['muted']}; border: 1px solid {c['line']}; padding: 0 5px; font-family: {fam('lbl')};
  font-size: {7.5 * s:.1f}pt; font-weight: 700; }}
QLabel#tagUnc {{ color: {c['muted']}; border: 1px dashed {c['muted']}; padding: 0 5px; font-family: {fam('lbl')};
  font-size: {7.5 * s:.1f}pt; font-weight: 700; }}
QLabel#tagFill {{ color: {c['act_ink']}; background: {c['gold']}; padding: 1px 6px; font-family: {fam('lbl')};
  font-size: {7.5 * s:.1f}pt; font-weight: 700; }}
QLabel#up {{ color: {c['ok']}; font-size: {9 * s:.1f}pt; }}
QLabel#err {{ color: {c['warn']}; font-size: {9 * s:.1f}pt; }}
QLabel#ok {{ color: {c['ok']}; font-family: {fam('lbl')}; font-size: {8 * s:.1f}pt; font-weight: 700; }}
QFrame#row {{ background: {c['panel']}; border: {bw}px solid {c['line']}; }}
QFrame#row[state="live"] {{ border-color: {c['act'] if c['act'] != c['panel'] else c['gold']}; }}
QFrame#row[state="soon"] {{ border-color: {c['gold']}; }}
QFrame#row[state="ready"] {{ border-color: {c['ok']}; }}
QFrame#card {{ background: {c['panel']}; border: {bw}px solid {c['line']}; }}
QFrame#hero {{ background: {c['panel']}; border: {bw}px solid {c['line']}; }}
QFrame#heroInner {{ background: {c['panel']}; border: 1px solid {c['soft'] if c['soft'] != c['panel'] else c['line']}; }}
QFrame#stat {{ background: {c['panel']}; border: {bw}px solid {c['line']}; }}
QPushButton {{ background: transparent; border: {bw}px solid {c['line']}; padding: {pad - 5}px 11px;
  font-family: {fam('lbl')}; font-weight: 600; font-size: {8.5 * s:.1f}pt; color: {c['ink']}; }}
QPushButton:hover {{ border-color: {c['muted']}; }}
QPushButton:disabled {{ color: {c['muted']}; }}
QPushButton#primary {{ background: {c['act']}; color: {c['act_ink']}; border-color: {c['act']}; }}
QPushButton#seg:checked {{ background: {c['act']}; color: {c['act_ink']}; border-color: {c['act']}; }}
QPushButton#step {{ padding: {pad - 6}px 9px; min-width: 26px; }}
QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: {bw}px solid {c['line']}; background: {c['panel']}; }}
QCheckBox::indicator:checked {{ background: {c['track']}; border-color: {c['track']}; }}
QComboBox, QSpinBox, QLineEdit, QTimeEdit {{ background: {c['panel']}; border: {bw}px solid {c['line']};
  padding: 4px 7px; color: {c['ink']}; }}
QComboBox QAbstractItemView {{ background: {c['panel']}; color: {c['ink']}; selection-background-color: {c['act']};
  selection-color: {c['act_ink']}; border: 1px solid {c['line']}; }}
QSlider::groove:horizontal {{ height: 4px; background: {c['dim']}; }}
QSlider::handle:horizontal {{ width: 12px; margin: -5px 0; background: {c['track']}; }}
QSlider::sub-page:horizontal {{ background: {c['track']}; }}
QToolTip {{ background: {c['panel']}; color: {c['ink']}; border: 1px solid {c['line']}; padding: 4px; }}
QScrollBar:vertical {{ background: {c['bg']}; width: 8px; }}
QScrollBar::handle:vertical {{ background: {c['line']}; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QDialog, QMessageBox, QInputDialog {{ background: {c['panel']}; }}
QMenu {{ background: {c['panel']}; border: 1px solid {c['line']}; }}
QMenu::item:selected {{ background: {c['act']}; color: {c['act_ink']}; }}
"""


# estado inicial (antes de `apply`), para os testes e módulos que leem as cores na importação
build_qss()
QSS = build_qss()


def font_files() -> list[Path]:
    from .sound import resource
    return sorted(resource("assets/fonts").glob("*.ttf"))


def load_fonts() -> int:
    """Registra as fontes embutidas. Precisa de um QApplication já criado."""
    from PySide6.QtGui import QFontDatabase
    ok = 0
    for f in font_files():
        if QFontDatabase.addApplicationFont(str(f)) >= 0:
            ok += 1
    return ok


def apply(app, settings: dict) -> str:
    qss = build_qss(settings.get("theme", "ely"), settings.get("text_size", "normal"),
                    bool(settings.get("compact")), settings.get("accent", "def"))
    app.setStyleSheet(qss)
    return qss
