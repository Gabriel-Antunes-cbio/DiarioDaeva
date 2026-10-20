"""Janela principal: abas Hoje, Bosses, Personagens, Títulos, BiS e Ajustes, alertas e ícone na bandeja."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSlider, QSpinBox, QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
)

from . import GITHUB_REPO, __version__, progress, theme
from .widgets import DottedBar, GrimFrame, Leader, Pips, Trail
from .chart import GrowthChart, fmt_int
from .group import GroupError, get_kills, normalize_url, ping, post_kill
from .profiles import ProfileError, fetch_details, fetch_profile, parse_link
from .titles_tab import TitlesTab
from .bis_tab import BisTab
from .schedule import (
    EVENT_BY_ID, EVENTS, FIELD_BOSSES, FIELD_BY_ID, REGIONS, AlertTracker, fmt_left, next_occurrence, now_utc,
)
from .sound import SOUND_EXTS, SOUND_KINDS, play_alert, resource
from .store import Store, data_dir, parse_iso

WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MANUAL_REFRESH_GAP = timedelta(minutes=5)


def local_when(dt: datetime) -> str:
    d = dt.astimezone()
    return f"{WEEKDAYS[d.weekday()]} {d:%H:%M}"


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def restyle(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


# ======================================================================= workers
class _Signals(QObject):
    done = Signal(str, object, str)  # char_id, ProfileData | None, error
    details = Signal(str, object)    # char_id, dict


class FetchJob(QRunnable):
    def __init__(self, char_id: str, url: str):
        super().__init__()
        self.char_id, self.url = char_id, url
        self.signals = _Signals()

    def run(self):
        try:
            link = parse_link(self.url)
            data = fetch_profile(link)
            self.signals.done.emit(self.char_id, data, "")
        except ProfileError as e:
            self.signals.done.emit(self.char_id, None, str(e))
            return
        except Exception as e:  # nunca derrubar o app por causa de um site
            self.signals.done.emit(self.char_id, None, f"Erro inesperado ao ler o perfil: {e}")
            return
        try:
            self.signals.details.emit(self.char_id, fetch_details(link))
        except Exception:
            pass


class _UpdSignals(QObject):
    found = Signal(str, str)


class UpdateCheck(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = _UpdSignals()

    def run(self):
        if not GITHUB_REPO:
            return
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                                         headers={"User-Agent": "DiarioDeDaeva", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                info = json.loads(r.read().decode("utf-8"))
            tag = str(info.get("tag_name", "")).lstrip("vV")
            if tag and _ver(tag) > _ver(__version__):
                self.signals.found.emit(tag, info.get("html_url", f"https://github.com/{GITHUB_REPO}/releases"))
        except Exception:
            pass


class _GroupSignals(QObject):
    done = Signal(str, object, str)  # tipo, resultado, erro


class GroupJob(QRunnable):
    """Conversa com o bot do grupo fora da interface. kind: 'get' | 'post' | 'ping'."""

    def __init__(self, kind: str, url: str, key: str, payload: dict | None = None):
        super().__init__()
        self.kind, self.url, self.key, self.payload = kind, url, key, payload or {}
        self.signals = _GroupSignals()

    def run(self):
        try:
            if self.kind == "ping":
                ping(self.url, self.key)
                res = None
            elif self.kind == "post":
                p = self.payload
                res = post_kill(self.url, self.key, p["boss"], p["respawn_at"], p["by"], p.get("killed_at"))
            else:
                res = get_kills(self.url, self.key)
            self.signals.done.emit(self.kind, res, "")
        except GroupError as e:
            self.signals.done.emit(self.kind, None, str(e))
        except Exception as e:
            self.signals.done.emit(self.kind, None, f"Erro inesperado ao falar com o bot: {e}")


def _ver(s: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in s.split("."))


# ======================================================================= rows
class EventRow(QFrame):
    def __init__(self, title: str, subtitle: str, tags: list[tuple[str, str]], alert_on: bool, on_toggle):
        super().__init__()
        self.setObjectName("row")
        g = QGridLayout(self)
        g.setContentsMargins(12, 10, 12, 10)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(3)
        left = QVBoxLayout()
        left.setSpacing(3)
        left.addWidget(label(title, "name"))
        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        for text, kind in tags:
            tag_row.addWidget(label(text, kind))
        tag_row.addStretch(1)
        left.addLayout(tag_row)
        if subtitle:
            left.addWidget(label(subtitle, "muted", wrap=True))
        self.note = label("", "muted", wrap=True)
        self.note.hide()
        left.addWidget(self.note)
        g.addLayout(left, 0, 0, 2, 1)
        self.countdown = label("—", "countdown")
        self.countdown.setAlignment(Qt.AlignRight)
        self.when = label("", "muted")
        self.when.setAlignment(Qt.AlignRight)
        g.addWidget(self.countdown, 0, 1)
        g.addWidget(self.when, 1, 1)
        self.alert = QCheckBox("Alerta")
        self.alert.setChecked(alert_on)
        self.alert.setToolTip("Tocar som e notificar antes do início")
        self.alert.toggled.connect(on_toggle)
        g.addWidget(self.alert, 2, 1, Qt.AlignRight)
        g.setColumnStretch(0, 1)
        self.extra = QHBoxLayout()
        self.extra.setSpacing(6)
        g.addLayout(self.extra, 2, 0)

    def set_state(self, state: str):
        if self.property("state") != state:
            self.setProperty("state", state)
            restyle(self)


class RemainingDialog(QDialog):
    """Pergunta quanto falta para o boss nascer, do jeito que o mapa do jogo mostra."""

    def __init__(self, boss_name: str, respawn_h: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(boss_name)
        v = QVBoxLayout(self)
        v.addWidget(label(f"Quanto falta para o <b>{boss_name}</b> nascer?", wrap=True))
        row = QHBoxLayout()
        self.hours = QSpinBox(minimum=0, maximum=48, suffix=" h")
        self.minutes = QSpinBox(minimum=0, maximum=59, suffix=" min")
        self.hours.setValue(min(respawn_h, 48) // 2)
        row.addWidget(self.hours)
        row.addWidget(self.minutes)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(label("Copie do mapa do jogo: Exploração → Field Boss mostra a contagem de cada boss.",
                          "muted", wrap=True))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Salvar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def remaining(self) -> timedelta:
        return timedelta(hours=self.hours.value(), minutes=self.minutes.value())


# ======================================================================= window
class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.tracker = AlertTracker()
        self.pool = QThreadPool.globalInstance()
        self.fetching: set[str] = set()
        self.last_manual: dict[str, datetime] = {}
        self.chart_metric = "cp"
        self.event_rows: dict[str, EventRow] = {}
        self.key_widgets: dict[str, tuple] = {}
        self.field_rows: dict[str, EventRow] = {}
        self._really_quit = False
        self._tray_hint_shown = False

        self.setWindowTitle("Diário de Daeva")
        self.setWindowIcon(QIcon(str(resource("assets/icon.png"))))
        self.resize(460, 780)
        self.setMinimumWidth(380)

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(10)
        ident = QVBoxLayout()
        ident.setSpacing(0)
        ident.addWidget(label("Diário de Daeva", "title"))
        self.who_label = label("", "who")
        ident.addWidget(self.who_label)
        head.addLayout(ident, 1)
        self.update_btn = QPushButton("Nova versão disponível")
        self.update_btn.setObjectName("primary")
        self.update_btn.hide()
        head.addWidget(self.update_btn)
        self.group_dot = label("", "ok")
        head.addWidget(self.group_dot, 0, Qt.AlignTop)
        v.addLayout(head)
        self.next_label = label("", "next", wrap=True)
        v.addWidget(self.next_label)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        today = self._build_today_tab()
        self.tabs.addTab(today, "HOJE")
        self.tabs.addTab(self._build_bosses_tab(), "BOSSES")
        self.tabs.addTab(self._build_chars_tab(), "PERSONAGENS")
        self.titles_tab = TitlesTab(self.store, self.current_char)
        self.tabs.addTab(self.titles_tab, "TÍTULOS")
        self.bis_tab = BisTab(self.current_char)
        self.tabs.addTab(self.bis_tab, "BIS")
        self.tabs.addTab(self._build_settings_tab(), "AJUSTES")
        self.tabs.currentChanged.connect(lambda _: self._bis_refresh())
        v.addWidget(self.tabs, 1)

        self._build_tray()
        self._apply_on_top()

        self.tick = QTimer(self, interval=1000, timeout=self.on_tick)
        self.tick.start()
        self.refresh_timer = QTimer(self, interval=15 * 60 * 1000, timeout=self.auto_refresh)
        self.refresh_timer.start()
        QTimer.singleShot(1500, self.auto_refresh)
        QTimer.singleShot(4000, self.check_update)
        self.group_last_ok: datetime | None = None
        self.group_error = ""
        self.group_busy = False
        self.group_timer = QTimer(self, interval=30 * 1000, timeout=self.group_sync)
        self.group_timer.start()
        QTimer.singleShot(2000, self.group_sync)
        self.update_group_line()
        self.on_tick()
        self.render_character()

    # ------------------------------------------------------------- hoje
    def _build_today_tab(self) -> QWidget:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(10)

        self.hero = GrimFrame()
        b = self.hero.body
        top = QHBoxLayout()
        top.addWidget(label("PRÓXIMO SPAWN", "section"))
        top.addStretch(1)
        self.h_tag = label("", "tagFill")
        top.addWidget(self.h_tag)
        b.addLayout(top)
        self.h_name = label("—", "heroName")
        b.addWidget(self.h_name)
        self.h_count = label("—", "bigcount")
        b.addWidget(self.h_count)
        self.h_trail = Trail()
        b.addWidget(self.h_trail)
        times = QHBoxLayout()
        self.h_left = label("", "muted", wrap=True)
        self.h_right = label("", "muted", wrap=True)
        self.h_right.setAlignment(Qt.AlignRight)
        times.addWidget(self.h_left)
        times.addStretch(1)
        times.addWidget(self.h_right)
        b.addLayout(times)
        btns = QHBoxLayout()
        self.h_kill = QPushButton("MORREU AGORA", objectName="primary")
        self.h_ask = QPushButton("QUANTO FALTA")
        self.h_kill.clicked.connect(lambda: self.hero_boss and self.mark_killed(self.hero_boss))
        self.h_ask.clicked.connect(lambda: self.hero_boss and self.ask_remaining(self.hero_boss))
        btns.addWidget(self.h_kill, 1)
        btns.addWidget(self.h_ask, 1)
        b.addLayout(btns)
        self.hero_boss = None
        v.addWidget(self.hero)

        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        self.t_cp = self._stat("COMBAT POWER")
        self.t_gs = self._stat("GEAR SCORE")
        tiles.addWidget(self.t_cp[0])
        tiles.addWidget(self.t_gs[0])
        v.addLayout(tiles)

        self.today_energy = QFrame(objectName="card")
        ev = QVBoxLayout(self.today_energy)
        ev.setContentsMargins(14, 10, 14, 10)
        ev.setSpacing(5)
        er = QHBoxLayout()
        er.addWidget(label("ENERGIA ODYLE", "section"))
        er.addStretch(1)
        self.te_value = label("—", "countdown")
        er.addWidget(self.te_value)
        ev.addLayout(er)
        self.te_bar = DottedBar()
        ev.addWidget(self.te_bar)
        self.te_note = label("", "muted", wrap=True)
        ev.addWidget(self.te_note)
        v.addWidget(self.today_energy)

        queue = QFrame(objectName="card")
        qv = QVBoxLayout(queue)
        qv.setContentsMargins(14, 10, 14, 10)
        qv.setSpacing(6)
        qv.addWidget(label("FILA DE EVENTOS", "section"))
        self.queue_rows = []
        for _ in range(6):
            r = QHBoxLayout()
            r.setSpacing(8)
            t = label("", "evtime")
            t.setMinimumWidth(64)
            n = label("")
            w = label("", "muted")
            r.addWidget(t)
            r.addWidget(n)
            r.addWidget(Leader(), 1)
            r.addWidget(w)
            qv.addLayout(r)
            self.queue_rows.append((t, n, w))
        v.addWidget(queue)

        self.title_card = QFrame(objectName="card")
        tv = QVBoxLayout(self.title_card)
        tv.setContentsMargins(14, 10, 14, 10)
        tv.setSpacing(5)
        tr = QHBoxLayout()
        tr.addWidget(label("TÍTULO ALVO", "section"))
        tr.addStretch(1)
        self.tt_bonus = label("", "muted")
        tr.addWidget(self.tt_bonus)
        tv.addLayout(tr)
        tn = QHBoxLayout()
        self.tt_name = label("", "name")
        self.tt_prog = label("", "countdown")
        tn.addWidget(self.tt_name, 1)
        tn.addWidget(self.tt_prog)
        tv.addLayout(tn)
        self.tt_bar = DottedBar()
        tv.addWidget(self.tt_bar)
        v.addWidget(self.title_card)
        v.addStretch(1)
        return self._scroll(inner)

    def _pick_hero(self, now: datetime, tz: str):
        """O que aparece no destaque da Hoje: o próximo boss de campo ou boss grande com alerta ligado."""
        alerts = self.store.settings["alerts"]
        cands = []
        for bb in FIELD_BOSSES:
            due = self.store.respawn_time(bb.id)
            if due and due > now - timedelta(minutes=30) and (alerts.get(bb.id) or bb.big):
                cands.append((due, "field", bb))
        for ev in EVENTS:
            if ev.kind == "big" and alerts.get(ev.id):
                occ = next_occurrence(ev, now, tz)
                if occ:
                    cands.append((occ.start, "event", ev))
        if cands:
            return min(cands, key=lambda x: x[0])
        c = self.current_char()
        bid = "gartua_imortal" if c and str(c.get("faction", "")).lower().startswith("asmo") else "gartua"
        return (None, "field", FIELD_BY_ID[bid])

    def update_today(self, now: datetime, tz: str, lead: int):
        when, kind, obj = self._pick_hero(now, tz)
        alerts = self.store.settings["alerts"]
        self.h_name.setText(obj.name)
        self.h_tag.setText(f"ALERTA {lead} MIN")
        self.h_tag.setVisible(bool(alerts.get(obj.id)))
        is_field = kind == "field"
        self.hero_boss = obj if is_field else None
        self.h_kill.setVisible(is_field)
        self.h_ask.setVisible(is_field)
        if when is None:
            self.h_count.setText("—")
            self.h_trail.set_progress(0)
            self.h_left.setText("sem registro")
            self.h_right.setText("use Morreu agora ou Quanto falta")
        else:
            left = when - now
            secs = max(0, int(left.total_seconds()))
            self.h_count.setText(f"{secs // 3600}:{secs // 60 % 60:02d}:{secs % 60:02d}" if secs else "nasceu?")
            if is_field:
                total = obj.respawn_h * 3600
                self.h_trail.set_progress(1 - secs / total if total else 1)
                self.h_left.setText(f"morte · {(when - timedelta(hours=obj.respawn_h)).astimezone():%H:%M}")
                self.h_right.setText(f"nasce · {when.astimezone():%H:%M}")
            else:
                self.h_trail.set_progress(1 - secs / (6 * 3600))
                self.h_left.setText(obj.detail or obj.en)
                self.h_right.setText(f"começa · {local_when(when)}")

        c = self.current_char()
        for (frame, _t, val, delta), key in ((self.t_cp, "cp"), (self.t_gs, "gear")):
            val.setText(fmt_int(c.get(key)) if c else "—")
            hist = (c or {}).get("history") or []
            if len(hist) >= 2 and hist[-1][key] != hist[0][key]:
                d = hist[-1][key] - hist[0][key]
                delta.setText(f"{'+' if d > 0 else ''}{fmt_int(d)} desde {parse_iso(hist[0]['t']).astimezone():%d/%m}")
            else:
                delta.setText("")
        if c:
            self.t_gs[1].setText((c.get("gear_label") or "Gear score").upper())

        # energia
        member = bool(self.store.settings.get("membership"))
        cap = progress.energy_cap(member)
        cur = progress.energy_now((c or {}).get("energy"), now, member)
        self.today_energy.setVisible(c is not None)
        if cur is None:
            self.te_value.setText(f"— / {cap}")
            self.te_bar.set_progress(0)
            self.te_note.setText("Informe a energia atual na aba Personagens; o app conta 5 por hora a partir daí.")
        else:
            self.te_value.setText(f"{cur} / {cap}")
            self.te_bar.set_progress(cur / cap)
            full = progress.energy_full_at(c.get("energy"), now, member)
            rewards = cur // progress.ENERGY_COST
            self.te_note.setText((f"Cheia em {fmt_left(full - now)} ({local_when(full)})" if full else "Cheia: gaste antes de perder energia")
                                 + f" · dá para {rewards} recompensa{'s' if rewards != 1 else ''}")

        # fila de eventos: os 5 próximos + o reset semanal sempre no fim
        occs = []
        for ev in EVENTS:
            if ev.id == "reset_weekly":
                continue
            occ = next_occurrence(ev, now, tz)
            if occ and not occ.live(now):
                occs.append((occ.start, ev))
        occs.sort(key=lambda x: x[0])
        rows = occs[:5]
        wk = next_occurrence(EVENT_BY_ID["reset_weekly"], now, tz)
        if wk:
            rows.append((wk.start, EVENT_BY_ID["reset_weekly"]))
        for (t, n, w), item in zip(self.queue_rows, rows + [None] * 6):
            if item is None:
                t.setText(""); n.setText(""); w.setText("")
                continue
            start, ev = item
            t.setText(fmt_left(start - now))
            warn = ev.kind == "reset"
            if t.property("warn") != warn:
                t.setProperty("warn", warn)
                restyle(t)
            n.setText(ev.name)
            w.setText(local_when(start))

        # título alvo
        tgt = self.store.target(c["id"]) if c else None
        a = self.titles_tab.by_id.get(tgt["id"]) if tgt and hasattr(self, "titles_tab") else None
        show = a is not None and not self.store.settings.get("compact")
        self.title_card.setVisible(show)
        if show:
            self.tt_name.setText(a.title)
            total = a.target_count
            prog = int(tgt.get("progress", 0))
            prog = min(prog, total) if total else prog
            self.tt_prog.setText(f"{prog}/{total}" if total else "")
            self.tt_bar.set_progress(prog / total if total else 0)
            self.tt_bonus.setText(a.achievement)

    # ------------------------------------------------------------- bosses tab
    def _scroll(self, inner: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setWidget(inner)
        return sa

    def _build_bosses_tab(self) -> QWidget:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(8)
        self.tz_label = label("", "section")
        v.addWidget(self.tz_label)
        for ev in EVENTS:
            tags = [(ev.en, "tag")]
            if ev.unconfirmed:
                tags.append(("não confirmado", "tagUnc"))
            row = EventRow(ev.name, ev.detail, tags, self.store.settings["alerts"].get(ev.id, False),
                           lambda on, k=ev.id: self.store.set_alert(k, on))
            self.event_rows[ev.id] = row
            if ev.id in progress.KEYS:
                self._add_keys(row, ev.id)
            v.addWidget(row)

        v.addSpacing(8)
        v.addWidget(label("BOSSES DE CAMPO · RENASCEM APÓS A MORTE", "section"))
        v.addWidget(label("Use “Quanto falta…” com a contagem do mapa do jogo (Exploração → Field Boss), "
                          "ou “Morreu agora” quando o boss cair na sua frente.", "muted", wrap=True))
        self.group_line = label("", "muted", wrap=True)
        v.addWidget(self.group_line)
        for b in FIELD_BOSSES:
            row = EventRow(b.name, b.where, [(f"respawn {b.respawn_h}h", "tag")],
                           self.store.settings["alerts"].get(b.id, False),
                           lambda on, k=b.id: self.store.set_alert(k, on))
            kill = QPushButton("Morreu agora")
            kill.setObjectName("primary")
            kill.clicked.connect(lambda _=False, bb=b: self.mark_killed(bb))
            at = QPushButton("Quanto falta…")
            at.setToolTip("Informe a contagem que aparece no mapa do jogo (Exploração → Field Boss)")
            at.clicked.connect(lambda _=False, bb=b: self.ask_remaining(bb))
            clear = QPushButton("Limpar")
            clear.clicked.connect(lambda _=False, k=b.id: self.set_respawn(k, None))
            for w in (kill, at, clear):
                row.extra.addWidget(w)
            row.extra.addStretch(1)
            row.clear_btn = clear
            self.field_rows[b.id] = row
            v.addWidget(row)
        v.addStretch(1)
        return self._scroll(inner)

    def _add_keys(self, row, kind: str):
        row.extra.addWidget(label("CHAVES", "section"))
        pips = Pips()
        cnt = label("", "countdown")
        minus = QPushButton("−1", objectName="step")
        plus = QPushButton("+1", objectName="step")
        tip = "Chaves do personagem escolhido na aba Personagens. Ajuste uma vez; depois o app soma as do reset diário."
        for w in (minus, plus):
            w.setToolTip(tip)
        minus.clicked.connect(lambda: self.change_keys(kind, -1))
        plus.clicked.connect(lambda: self.change_keys(kind, +1))
        for w in (pips, cnt):
            row.extra.addWidget(w)
        row.extra.addStretch(1)
        row.extra.addWidget(minus)
        row.extra.addWidget(plus)
        self.key_widgets[kind] = (row, pips, cnt, minus, plus)

    def _keys_info(self, kind: str, now: datetime):
        c = self.current_char()
        member = bool(self.store.settings.get("membership"))
        tz = REGIONS.get(self.store.settings.get("region", "la"), REGIONS["la"])[1]
        cur = progress.keys_now(((c or {}).get("keys") or {}).get(kind), kind, now, tz, member) if c else None
        return c, cur, progress.key_cap(kind, member)

    def change_keys(self, kind: str, delta: int):
        now = now_utc()
        c, cur, cap = self._keys_info(kind, now)
        if not c:
            return
        new = max(0, min(cap, (cur or 0) + delta))
        self.store.set_keys(c["id"], kind, progress.keys_entry(new, now))
        self.update_keys(now)

    def update_keys(self, now: datetime):
        for kind, (row, pips, cnt, minus, plus) in self.key_widgets.items():
            c, cur, cap = self._keys_info(kind, now)
            k = progress.KEYS[kind]
            pips.set_value(cur or 0, cap)
            cnt.setText(f"{'—' if cur is None else cur}/{cap}")
            minus.setEnabled(bool(c) and (cur or 0) > 0)
            plus.setEnabled(bool(c) and (cur or 0) < cap)
            row.note.setText((f"Chaves de {c['name']} · " if c else "Adicione um personagem para contar as chaves · ")
                             + f"+{k['daily']} por dia no reset, até {cap}")
            row.note.show()

    def mark_killed(self, boss):
        now = now_utc()
        self.set_respawn(boss.id, now + timedelta(hours=boss.respawn_h), killed_at=now)

    def set_respawn(self, boss_id: str, due: datetime | None, killed_at: datetime | None = None):
        nick = (self.store.settings.get("nickname") or "").strip() or "alguém"
        self.store.set_respawn(boss_id, due, nick, "app" if self.store.group_on else "local", killed_at is not None)
        if self.store.group_on:
            s = self.store.settings
            job = GroupJob("post", s["group_url"], s["group_key"],
                           {"boss": boss_id, "respawn_at": due.isoformat() if due else None,
                            "killed_at": killed_at.isoformat() if killed_at else None, "by": nick})
            job.signals.done.connect(self.on_group_done)
            self.pool.start(job)
        self.on_tick()

    # ------------------------------------------------------------- group bot
    def group_sync(self):
        if not self.store.group_on or self.group_busy:
            self.update_group_line()
            return
        self.group_busy = True
        s = self.store.settings
        job = GroupJob("get", s["group_url"], s["group_key"])
        job.signals.done.connect(self.on_group_done)
        self.pool.start(job)

    def on_group_done(self, kind: str, result, error: str):
        if kind == "get":
            self.group_busy = False
        if kind == "ping":
            self.group_status.setText("Conectado ao bot do grupo." if not error else error)
            self.group_status.setObjectName("up" if not error else "err")
            restyle(self.group_status)
            if not error:
                self.group_sync()
            return
        if error:
            self.group_error = ("Não consegui enviar a marcação ao bot: " + error) if kind == "post" else error
        else:
            self.group_error = ""
            self.group_last_ok = now_utc()
            if self.store.apply_group(result):
                self.on_tick()
        self.update_group_line()

    def update_group_line(self):
        if not hasattr(self, "group_line"):
            return
        if not self.store.group_on:
            self.group_line.setText("Sem bot do grupo: os horários ficam só neste PC. Configure em Ajustes → Grupo.")
            self.group_line.setObjectName("muted")
        elif self.group_error:
            self.group_line.setText(self.group_error)
            self.group_line.setObjectName("err")
        elif self.group_last_ok:
            self.group_line.setText(f"Sincronizado com o bot do grupo às {self.group_last_ok.astimezone():%H:%M:%S}. "
                                    "Mortes marcadas aqui ou com /gartua no Discord valem para todos.")
            self.group_line.setObjectName("up")
        else:
            self.group_line.setText("Conectando ao bot do grupo…")
            self.group_line.setObjectName("muted")
        restyle(self.group_line)

    def ask_remaining(self, boss):
        dlg = RemainingDialog(boss.name, boss.respawn_h, self)
        if dlg.exec() == QDialog.Accepted:
            left = dlg.remaining()
            if left <= timedelta(0):
                self.set_respawn(boss.id, now_utc())
            else:
                self.set_respawn(boss.id, now_utc() + left)

    # ------------------------------------------------------------- chars tab
    def _build_chars_tab(self) -> QWidget:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(10)
        top = QHBoxLayout()
        self.char_combo = QComboBox()
        self.char_combo.currentIndexChanged.connect(lambda _: (self.render_character(), self._titles_refresh()))
        top.addWidget(self.char_combo, 1)
        add = QPushButton("Adicionar")
        add.setObjectName("primary")
        add.clicked.connect(self.add_character)
        top.addWidget(add)
        self.remove_btn = QPushButton("Remover")
        self.remove_btn.clicked.connect(self.remove_character)
        top.addWidget(self.remove_btn)
        v.addLayout(top)

        self.empty = label("Cole o link do perfil do seu personagem no Shugo.GG ou no AION2 Index em "
                           "“Adicionar”. Exemplos:\nshugo.gg/character/global/la-siel/Nome\n"
                           "aion2index.com/c/la/siel/Nome", "muted", wrap=True)
        v.addWidget(self.empty)

        self.card = QFrame(objectName="card")
        c = QVBoxLayout(self.card)
        c.setContentsMargins(14, 12, 14, 12)
        c.setSpacing(10)
        self.c_name = label("", "name")
        self.c_meta = label("", "muted", wrap=True)
        c.addWidget(self.c_name)
        c.addWidget(self.c_meta)
        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_cp = self._stat("COMBAT POWER")
        self.stat_gear = self._stat("GEAR SCORE")
        stats.addWidget(self.stat_cp[0])
        stats.addWidget(self.stat_gear[0])
        c.addLayout(stats)
        en = QHBoxLayout()
        en.addWidget(label("ENERGIA ODYLE", "section"))
        en.addStretch(1)
        self.e_value = label("—", "countdown")
        en.addWidget(self.e_value)
        set_e = QPushButton("Informar energia…")
        set_e.clicked.connect(self.ask_energy)
        en.addWidget(set_e)
        c.addLayout(en)
        self.e_bar = DottedBar()
        c.addWidget(self.e_bar)
        self.e_note = label("", "muted", wrap=True)
        c.addWidget(self.e_note)
        seg = QHBoxLayout()
        seg.addWidget(label("EVOLUÇÃO", "section"))
        seg.addStretch(1)
        self.seg_cp = QPushButton("CP", objectName="seg", checkable=True, checked=True)
        self.seg_gear = QPushButton("Gear score", objectName="seg", checkable=True)
        self.seg_cp.clicked.connect(lambda: self.set_metric("cp"))
        self.seg_gear.clicked.connect(lambda: self.set_metric("gear"))
        seg.addWidget(self.seg_cp)
        seg.addWidget(self.seg_gear)
        c.addLayout(seg)
        self.chart = GrowthChart()
        c.addWidget(self.chart)
        self.c_status = label("", "muted", wrap=True)
        c.addWidget(self.c_status)
        self.d_gear_h = label("EQUIPAMENTO", "section")
        self.d_gear = label("", wrap=True)
        self.d_gear.setTextFormat(Qt.RichText)
        self.d_skills_h = label("SKILLS", "section")
        self.d_skills = label("", wrap=True)
        self.d_skills.setTextFormat(Qt.RichText)
        self.d_note = label("", "muted", wrap=True)
        for w in (self.d_gear_h, self.d_gear, self.d_skills_h, self.d_skills, self.d_note):
            c.addWidget(w)
        foot = QHBoxLayout()
        self.refresh_btn = QPushButton("Atualizar agora")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        self.open_btn = QPushButton("Abrir perfil")
        self.open_btn.clicked.connect(self.open_profile)
        foot.addWidget(self.refresh_btn)
        foot.addWidget(self.open_btn)
        foot.addStretch(1)
        c.addLayout(foot)
        v.addWidget(self.card)

        self.alts_card = QFrame(objectName="card")
        al = QVBoxLayout(self.alts_card)
        al.setContentsMargins(14, 10, 14, 10)
        al.setSpacing(6)
        al.addWidget(label("TODOS OS PERSONAGENS", "section"))
        self.alts_box = QVBoxLayout()
        self.alts_box.setSpacing(4)
        al.addLayout(self.alts_box)
        al.addWidget(label("Energia Odyle: 5 por hora. Limite 560, ou 840 com Membership "
                           "(marque em Ajustes; vale para a conta toda).", "muted", wrap=True))
        v.addWidget(self.alts_card)
        self.alt_labels: dict[str, tuple] = {}
        v.addStretch(1)
        self.reload_combo()
        return self._scroll(inner)

    def ask_energy(self):
        c = self.current_char()
        if not c:
            return
        now = now_utc()
        member = bool(self.store.settings.get("membership"))
        cap = progress.energy_cap(member)
        cur = progress.energy_now(c.get("energy"), now, member)
        val, ok = QInputDialog.getInt(self, "Energia Odyle", f"Quanto de energia {c['name']} tem agora?",
                                      cur or 0, 0, cap)
        if ok:
            self.store.set_energy(c["id"], progress.energy_entry(val, now))
            self.update_energy(now)

    def update_energy(self, now: datetime):
        c = self.current_char()
        if not c or not hasattr(self, "e_value"):
            return
        member = bool(self.store.settings.get("membership"))
        cap = progress.energy_cap(member)
        cur = progress.energy_now(c.get("energy"), now, member)
        if cur is None:
            self.e_value.setText(f"— / {cap}")
            self.e_bar.set_progress(0)
            self.e_note.setText("Informe quanto tem agora; o app conta 5 por hora a partir daí.")
        else:
            self.e_value.setText(f"{cur} / {cap}")
            self.e_bar.set_progress(cur / cap)
            full = progress.energy_full_at(c.get("energy"), now, member)
            self.e_note.setText(f"Cheia em {fmt_left(full - now)} ({local_when(full)})." if full
                                else "Cheia. A energia que passar do limite se perde.")
        for cid, (en_lbl, full_lbl) in self.alt_labels.items():
            ch = self.store.find(cid)
            if not ch:
                continue
            v = progress.energy_now(ch.get("energy"), now, member)
            en_lbl.setText("—" if v is None else f"{v}/{cap}")
            f = progress.energy_full_at(ch.get("energy"), now, member)
            full_lbl.setText("" if v is None else ("cheia" if f is None else f"cheia em {fmt_left(f - now)}"))

    def rebuild_alts(self):
        while self.alts_box.count():
            item = self.alts_box.takeAt(0)
            lay = item.layout()
            if lay:
                while lay.count():
                    w = lay.takeAt(0).widget()
                    if w:
                        w.deleteLater()
        self.alt_labels = {}
        cur = self.current_id()
        for ch in self.store.characters:
            r = QHBoxLayout()
            r.setSpacing(8)
            name = QPushButton(ch["name"], objectName="seg", checkable=True, checked=ch["id"] == cur)
            name.clicked.connect(lambda _=False, cid=ch["id"]: self.reload_combo(cid) or self.render_character())
            meta = label(" · ".join(x for x in (ch.get("cls") or "", f"Nv {ch['level']}" if ch.get("level") else "") if x),
                         "muted")
            en_lbl = label("—", "countdown")
            full_lbl = label("", "muted")
            r.addWidget(name)
            r.addWidget(meta)
            r.addWidget(Leader(), 1)
            r.addWidget(en_lbl)
            r.addWidget(full_lbl)
            self.alts_box.addLayout(r)
            self.alt_labels[ch["id"]] = (en_lbl, full_lbl)
        self.alts_card.setVisible(bool(self.store.characters))

    def _stat(self, title: str):
        f = QFrame(objectName="stat")
        l = QVBoxLayout(f)
        l.setContentsMargins(12, 9, 12, 9)
        l.setSpacing(2)
        t = label(title, "section")
        val = label("—", "bigval")
        delta = label("", "up")
        l.addWidget(t)
        l.addWidget(val)
        l.addWidget(delta)
        return f, t, val, delta

    def reload_combo(self, select_id: str | None = None):
        cur = select_id or self.current_id()
        self.char_combo.blockSignals(True)
        self.char_combo.clear()
        for c in self.store.characters:
            self.char_combo.addItem(f"{c['name']} · {c['server'].title()}", c["id"])
        if cur:
            i = self.char_combo.findData(cur)
            if i >= 0:
                self.char_combo.setCurrentIndex(i)
        self.char_combo.blockSignals(False)

    def current_id(self) -> str | None:
        return self.char_combo.currentData() if hasattr(self, "char_combo") else None

    def current_char(self) -> dict | None:
        cid = self.current_id()
        return self.store.find(cid) if cid else None

    def _titles_refresh(self):
        if hasattr(self, "titles_tab") and self.titles_tab.isVisible():
            self.titles_tab.refresh()
        self._bis_refresh()

    def _bis_refresh(self):
        if hasattr(self, "bis_tab") and self.bis_tab.isVisible():
            self.bis_tab.refresh()

    def update_header(self):
        c = self.current_char()
        if c:
            bits = [c["name"], c.get("cls") or "", f"Nv {c['level']}" if c.get("level") else "", c.get("server", "").title()]
            self.who_label.setText(" · ".join(b for b in bits if b))
        else:
            self.who_label.setText("Adicione seu personagem na aba Personagens")

    def set_metric(self, m: str):
        self.chart_metric = m
        self.render_character()

    def render_character(self):
        c = self.current_char()
        has = c is not None
        self.empty.setVisible(not has)
        self.card.setVisible(has)
        self.remove_btn.setEnabled(has)
        self.char_combo.setVisible(bool(self.store.characters))
        self.rebuild_alts()
        self.update_header()
        if not has:
            return
        gl = c.get("gear_label") or "Gear score"
        self.c_name.setText(c["name"])
        region = REGIONS.get(c.get("region"), ("", ""))[0]
        bits = [c.get("cls") or "", f"Nível {c['level']}" if c.get("level") else "", c["server"].title(), region]
        self.c_meta.setText(" · ".join(b for b in bits if b))
        self.stat_gear[1].setText(gl.upper())
        self.seg_gear.setText(gl)
        hist = c.get("history") or []
        for (frame, _t, val, delta), key in ((self.stat_cp, "cp"), (self.stat_gear, "gear")):
            val.setText(fmt_int(c.get(key)))
            if len(hist) >= 2 and hist[-1][key] != hist[0][key]:
                d = hist[-1][key] - hist[0][key]
                first = parse_iso(hist[0]["t"]).astimezone()
                delta.setText(f"{'+' if d > 0 else ''}{fmt_int(d)} desde {first:%d/%m}")
                delta.setObjectName("up" if d > 0 else "muted")
                restyle(delta)
            else:
                delta.setText("")
        self.seg_cp.setChecked(self.chart_metric == "cp")
        self.seg_gear.setChecked(self.chart_metric == "gear")
        pts = [(parse_iso(h["t"]), h[self.chart_metric]) for h in hist if parse_iso(h["t"])]
        self.chart.set_series(pts, "CP" if self.chart_metric == "cp" else gl)

        site = "AION2 Index" if c.get("source") == "aion2index" else "Shugo.GG"
        busy = c["id"] in self.fetching
        if busy:
            status = f"Lendo o perfil no {site}…"
        elif c.get("last_error"):
            status = c["last_error"]
        elif c.get("updated"):
            status = f"Atualizado em {parse_iso(c['updated']).astimezone():%d/%m às %H:%M} pelo {site}."
        else:
            status = "Ainda sem leitura."
        self.c_status.setText(status)
        self.c_status.setObjectName("err" if c.get("last_error") and not busy else "muted")
        restyle(self.c_status)
        self.refresh_btn.setEnabled(not busy)
        self.refresh_btn.setText("Atualizando…" if busy else "Atualizar agora")
        self.open_btn.setText(f"Abrir no {site}")
        self.render_details(c)
        now = now_utc()
        self.update_energy(now)
        self.update_keys(now)

    def render_details(self, c: dict):
        d = c.get("details") or {}
        gear, skills = d.get("gear"), d.get("skills")
        esc = lambda t: (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        if gear:
            rows = "".join(
                f"<tr><td style='color:{theme.MUTED};padding:2px 10px 2px 0'>{esc(g['slot'])}</td>"
                f"<td style='padding:2px 10px 2px 0'>{esc(g['item'])}"
                f"{' <b>+' + str(g['enchant']) + '</b>' if g.get('enchant') else ''}</td>"
                f"<td style='color:{theme.MUTED}'>{esc(g['grade'])}</td></tr>" for g in gear)
            self.d_gear.setText(f"<table>{rows}</table>")
        else:
            self.d_gear.setText("<span style='color:%s'>Ainda sem dados de equipamento.</span>" % theme.MUTED)
        if skills and any(skills.values()):
            parts = []
            for key, title in (("active", "Ativas"), ("passive", "Passivas"), ("stigma", "Stigmas")):
                lst = skills.get(key) or []
                if lst:
                    items = ", ".join(f"{esc(n)} <b>{lv}</b>" for n, lv in lst)
                    parts.append(f"<span style='color:{theme.MUTED}'>{title}:</span> {items}")
            self.d_skills.setText("<br>".join(parts))
        else:
            self.d_skills.setText("<span style='color:%s'>Ainda sem dados de skills.</span>" % theme.MUTED)
        notes = []
        if d.get("updated"):
            notes.append(f"Equipamento pelo Shugo.GG e skills pelo AION2 Index, lidos em "
                         f"{parse_iso(d['updated']).astimezone():%d/%m às %H:%M}.")
        miss = {"gear": "equipamento", "skills": "skills", "titles": "títulos"}
        if d.get("errors"):
            notes.append("Não consegui ler agora: " + ", ".join(miss[e] for e in d["errors"] if e in miss) + ".")
        self.d_note.setText(" ".join(notes))

    def add_character(self):
        text, ok = QInputDialog.getText(self, "Adicionar personagem",
                                        "Link do perfil no Shugo.GG ou no AION2 Index:")
        if not ok or not text.strip():
            return
        try:
            link = parse_link(text)
        except ProfileError as e:
            QMessageBox.warning(self, "Link não reconhecido", str(e))
            return
        c = self.store.add_character(link)
        self.reload_combo(c["id"])
        self.render_character()
        self.start_fetch(c)

    def remove_character(self):
        c = self.current_char()
        if not c:
            return
        box = QMessageBox(QMessageBox.Question, "Remover personagem",
                          f"Remover {c['name']} e o histórico de evolução dele?", parent=self)
        yes = box.addButton("Remover", QMessageBox.DestructiveRole)
        box.addButton("Cancelar", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self.store.remove_character(c["id"])
            self.reload_combo()
            self.render_character()

    def open_profile(self):
        c = self.current_char()
        if c:
            QDesktopServices.openUrl(QUrl(c["url"]))

    # ------------------------------------------------------------- fetching
    def start_fetch(self, c: dict):
        if c["id"] in self.fetching:
            return
        self.fetching.add(c["id"])
        job = FetchJob(c["id"], c["url"])
        job.signals.done.connect(self.on_fetched)
        job.signals.details.connect(self.on_details)
        self.pool.start(job)
        self.render_character()

    def on_details(self, char_id: str, details: dict):
        self.store.record_details(char_id, details, now_utc())
        self.render_character()
        self._titles_refresh()

    def on_fetched(self, char_id: str, data, error: str):
        self.fetching.discard(char_id)
        if data is not None:
            self.store.record_profile(char_id, data, now_utc())
        else:
            self.store.record_error(char_id, error)
        c = self.store.find(char_id)
        if c:
            self.reload_combo()
        self.render_character()

    def manual_refresh(self):
        c = self.current_char()
        if not c:
            return
        last = self.last_manual.get(c["id"])
        if last and now_utc() - last < MANUAL_REFRESH_GAP:
            left = MANUAL_REFRESH_GAP - (now_utc() - last)
            self.c_status.setText(f"Atualizado há pouco. Tente de novo em {fmt_left(left)} para não sobrecarregar o site.")
            return
        self.last_manual[c["id"]] = now_utc()
        self.start_fetch(c)

    def auto_refresh(self):
        gap = timedelta(hours=max(1, int(self.store.settings.get("refresh_hours", 6))))
        for c in self.store.characters:
            last = parse_iso(c.get("updated"))
            if last is None or now_utc() - last >= gap:
                self.start_fetch(c)

    # ------------------------------------------------------------- settings tab
    def _build_settings_tab(self) -> QWidget:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(10)
        s = self.store.settings

        v.addWidget(label("APARÊNCIA", "section"))
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        self.cb_theme = QComboBox()
        for tid, t in theme.THEMES.items():
            self.cb_theme.addItem(t["name"], tid)
        self.cb_size = QComboBox()
        for sid, (name, _) in theme.SIZES.items():
            self.cb_size.addItem(name, sid)
        self.cb_accent = QComboBox()
        for aid, (name, *_r) in theme.ACCENTS.items():
            self.cb_accent.addItem(name, aid)
        for row_i, (text, combo, key, default) in enumerate((("Tema", self.cb_theme, "theme", "ely"),
                                                              ("Tamanho do texto", self.cb_size, "text_size", "normal"),
                                                              ("Cor de destaque", self.cb_accent, "accent", "def"))):
            combo.setCurrentIndex(max(0, combo.findData(s.get(key, default))))
            combo.currentIndexChanged.connect(lambda _=0, cb=combo, k=key: self.change_look(k, cb.currentData()))
            g.addWidget(label(text), row_i, 0)
            g.addWidget(combo, row_i, 1)
        g.setColumnStretch(1, 1)
        v.addLayout(g)
        cb_compact = QCheckBox("Modo compacto")
        cb_compact.setChecked(bool(s.get("compact")))
        cb_compact.toggled.connect(lambda on: self.change_look("compact", on))
        v.addWidget(cb_compact)
        v.addWidget(label("Menos espaço entre os blocos e sem o título alvo na Hoje. "
                          "Cabe melhor ao lado do jogo em monitor pequeno.", "muted", wrap=True))

        v.addSpacing(6)
        v.addWidget(label("CONTA", "section"))
        cb_member = self._check("Tenho Membership (vale para a conta toda)", "membership")
        cb_member.toggled.connect(lambda _: self.on_tick())
        v.addWidget(cb_member)
        v.addWidget(label("Com Membership: energia Odyle até 840 em vez de 560 e chaves do Festival Shugo até 21 "
                          "em vez de 12.", "muted", wrap=True))

        v.addSpacing(6)
        v.addWidget(label("ALERTAS", "section"))
        row = QHBoxLayout()
        row.addWidget(label("Bosses e Abismo: avisar"))
        self.lead = QSpinBox(minimum=1, maximum=30, value=int(s.get("alert_minutes", 5)), suffix=" min")
        self.lead.valueChanged.connect(lambda n: self.store.set_setting("alert_minutes", n))
        row.addWidget(self.lead)
        row.addWidget(label("antes"))
        row.addStretch(1)
        v.addLayout(row)
        row_h = QHBoxLayout()
        row_h.addWidget(label("Shugo e Invasão: avisar"))
        lead_h = QSpinBox(minimum=1, maximum=10, value=int(s.get("alert_minutes_hourly", 2)), suffix=" min")
        lead_h.valueChanged.connect(lambda n: self.store.set_setting("alert_minutes_hourly", n))
        row_h.addWidget(lead_h)
        row_h.addWidget(label("antes"))
        row_h.addStretch(1)
        v.addLayout(row_h)
        v.addWidget(self._check("Não perturbe das 00:00 às 08:00", "dnd"))
        v.addWidget(label("Silencia só o Festival Shugo e a Invasão Dimensional; os bosses grandes continuam avisando.",
                          "muted", wrap=True))
        self.cb_sound = self._check("Tocar som", "sound")
        test = QPushButton("Testar alerta")
        test.clicked.connect(lambda: self.fire_alert("Teste de alerta", "É assim que o aviso vai aparecer."))
        r2 = QHBoxLayout()
        r2.addWidget(self.cb_sound)
        r2.addStretch(1)
        r2.addWidget(test)
        v.addLayout(r2)
        v.addWidget(self._check("Mostrar notificação do Windows", "tray_notify"))
        v.addWidget(label("Os alertas ligados ficam na aba Bosses (caixa “Alerta” em cada linha). "
                          "Por padrão: Nahma, Executores, Vigia Kaira, os dois Gartua e o Festival Shugo.",
                          "muted", wrap=True))

        v.addSpacing(6)
        v.addWidget(label("SONS", "section"))
        v.addWidget(label("Escolha um arquivo WAV ou MP3 para cada tipo de aviso. Sem arquivo, toca o som padrão.",
                          "muted", wrap=True))
        self.sound_labels = {}
        for kind, title in SOUND_KINDS.items():
            box = QVBoxLayout()
            box.setSpacing(3)
            box.addWidget(label(title))
            r = QHBoxLayout()
            name = label("", "muted")
            self.sound_labels[kind] = name
            pick = QPushButton("Escolher…")
            pick.clicked.connect(lambda _=False, k=kind: self.pick_sound(k))
            reset = QPushButton("Padrão")
            reset.clicked.connect(lambda _=False, k=kind: self.set_sound(k, ""))
            test_k = QPushButton("Testar")
            test_k.clicked.connect(lambda _=False, k=kind: play_alert(k, self.store.settings))
            r.addWidget(name, 1)
            for w in (pick, reset, test_k):
                r.addWidget(w)
            box.addLayout(r)
            v.addLayout(box)
        rv = QHBoxLayout()
        rv.addWidget(label("Volume"))
        self.vol = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=int(s.get("volume", 80)))
        self.vol_lbl = label(f"{self.vol.value()}%", "muted")
        self.vol.valueChanged.connect(lambda n: (self.vol_lbl.setText(f"{n}%"), self.store.set_setting("volume", n)))
        rv.addWidget(self.vol, 1)
        rv.addWidget(self.vol_lbl)
        v.addLayout(rv)
        self.refresh_sound_labels()

        v.addSpacing(6)
        v.addWidget(label("SERVIDOR", "section"))
        self.region = QComboBox()
        for code, (name, _tz) in REGIONS.items():
            self.region.addItem(name, code)
        self.region.setCurrentIndex(max(0, self.region.findData(s.get("region", "la"))))
        self.region.currentIndexChanged.connect(lambda _: (self.store.set_setting("region", self.region.currentData()),
                                                            self.on_tick()))
        r3 = QHBoxLayout()
        r3.addWidget(label("Relógio dos eventos"))
        r3.addWidget(self.region, 1)
        v.addLayout(r3)
        v.addWidget(label("Na América Latina (Siel e outros) os eventos seguem o horário de Brasília.", "muted", wrap=True))

        v.addSpacing(6)
        v.addWidget(label("JANELA", "section"))
        cb_top = self._check("Sempre no topo", "always_on_top")
        cb_top.toggled.connect(lambda _: self._apply_on_top())
        v.addWidget(cb_top)
        v.addWidget(label("Útil com o jogo em janela sem bordas.", "muted", wrap=True))
        v.addWidget(self._check("Fechar para a bandeja", "close_to_tray"))
        v.addWidget(label("Ao fechar, o app fica perto do relógio e os alertas continuam.", "muted", wrap=True))

        v.addSpacing(6)
        v.addWidget(label("PERSONAGENS", "section"))
        r4 = QHBoxLayout()
        r4.addWidget(label("Atualizar perfis a cada"))
        sp = QSpinBox(minimum=1, maximum=24, value=int(s.get("refresh_hours", 6)), suffix=" h")
        sp.valueChanged.connect(lambda n: self.store.set_setting("refresh_hours", n))
        r4.addWidget(sp)
        r4.addStretch(1)
        v.addLayout(r4)

        v.addSpacing(6)
        v.addWidget(label("GRUPO (BOT DO DISCORD)", "section"))
        v.addWidget(label("Com o bot, a morte do Gartua e dos outros bosses de campo marcada por qualquer amigo "
                          "(aqui ou com /gartua no Discord) aparece para todos. Peça o endereço e a chave a quem "
                          "administra o bot.", "muted", wrap=True))
        self.in_url = QLineEdit(s.get("group_url", ""))
        self.in_url.setPlaceholderText("Endereço do bot, ex.: http://123.45.67.89:8080")
        self.in_key = QLineEdit(s.get("group_key", ""))
        self.in_key.setPlaceholderText("Chave do grupo")
        self.in_key.setEchoMode(QLineEdit.Password)
        self.in_nick = QLineEdit(s.get("nickname", ""))
        self.in_nick.setPlaceholderText("Seu nome no grupo (aparece nas marcações)")
        for w in (self.in_url, self.in_key, self.in_nick):
            v.addWidget(w)
            w.editingFinished.connect(self.save_group_fields)
        r6 = QHBoxLayout()
        test_btn = QPushButton("Testar conexão")
        test_btn.clicked.connect(self.test_group)
        r6.addWidget(test_btn)
        self.group_status = label("", "muted", wrap=True)
        r6.addWidget(self.group_status, 1)
        v.addLayout(r6)

        v.addSpacing(6)
        v.addWidget(label("SOBRE", "section"))
        v.addWidget(label(f"Diário de Daeva {__version__}. Lê só páginas públicas do Shugo.GG e do AION2 Index; "
                          "não acessa o jogo nem a sua conta.", "muted", wrap=True))
        folder = QPushButton("Abrir pasta de dados")
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))))
        r5 = QHBoxLayout()
        r5.addWidget(folder)
        r5.addStretch(1)
        v.addLayout(r5)
        v.addStretch(1)
        return self._scroll(inner)

    def change_look(self, key: str, value):
        self.store.set_setting(key, value)
        theme.apply(QApplication.instance(), self.store.settings)
        for w in self.findChildren(QWidget):
            w.update()
        self.render_character()
        self.on_tick()
        if self.bis_tab.isVisible():
            self.bis_tab.refresh()

    def pick_sound(self, kind: str):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher som", "", "Sons (*.wav *.mp3)")
        if path:
            self.set_sound(kind, path)

    def set_sound(self, kind: str, path: str):
        if path and not path.lower().endswith(SOUND_EXTS):
            QMessageBox.warning(self, "Formato não aceito", "Escolha um arquivo .wav ou .mp3.")
            return
        sounds = dict(self.store.settings.get("sounds") or {})
        sounds[kind] = path
        self.store.set_setting("sounds", sounds)
        self.refresh_sound_labels()

    def refresh_sound_labels(self):
        from pathlib import Path
        for kind, lbl_w in self.sound_labels.items():
            path = (self.store.settings.get("sounds") or {}).get(kind) or ""
            if not path:
                lbl_w.setText("Som padrão")
            elif Path(path).is_file():
                lbl_w.setText(Path(path).name)
            else:
                lbl_w.setText(f"{Path(path).name} (não encontrado; toca o padrão)")

    def _check(self, text: str, key: str) -> QCheckBox:
        cb = QCheckBox(text)
        cb.setChecked(bool(self.store.settings.get(key)))
        cb.toggled.connect(lambda on: self.store.set_setting(key, on))
        return cb

    def save_group_fields(self):
        s = self.store.settings
        new = (normalize_url(self.in_url.text()), self.in_key.text().strip(), self.in_nick.text().strip())
        if new != (s.get("group_url"), s.get("group_key"), s.get("nickname")):
            s["group_url"], s["group_key"], s["nickname"] = new
            self.store.save()
            self.in_url.setText(new[0])
            self.group_error = ""
            self.group_sync()

    def test_group(self):
        self.save_group_fields()
        s = self.store.settings
        self.group_status.setText("Testando…")
        self.group_status.setObjectName("muted")
        restyle(self.group_status)
        job = GroupJob("ping", s.get("group_url", ""), s.get("group_key", ""))
        job.signals.done.connect(self.on_group_done)
        self.pool.start(job)

    def _apply_on_top(self):
        on = bool(self.store.settings.get("always_on_top"))
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        if visible:
            self.show()

    # ------------------------------------------------------------- tick & alerts
    def on_tick(self):
        now = now_utc()
        s = self.store.settings
        tz = REGIONS.get(s.get("region", "la"), REGIONS["la"])[1]
        region_name = REGIONS.get(s.get("region", "la"), REGIONS["la"])[0]
        self.tz_label.setText(f"ABISMO E EVENTOS · SERVIDORES {region_name.upper()}")
        lead = int(s.get("alert_minutes", 5))
        alerts = s["alerts"]
        upcoming: list[tuple[datetime, str]] = []

        lead_h = int(s.get("alert_minutes_hourly", 2))
        local_hour = now.astimezone().hour
        f, t = int(s.get("dnd_from", 0)), int(s.get("dnd_to", 8))
        quiet = bool(s.get("dnd")) and (f <= local_hour < t if f <= t else (local_hour >= f or local_hour < t))
        for ev in EVENTS:
            row = self.event_rows[ev.id]
            occ = next_occurrence(ev, now, tz)
            if occ is None:
                continue
            ev_lead = lead_h if ev.kind == "hourly" else lead
            if occ.live(now):
                row.countdown.setText(f"termina em {fmt_left(occ.end - now)}")
                row.set_state("live")
            else:
                left = occ.start - now
                row.countdown.setText(fmt_left(left))
                row.set_state("soon" if left <= timedelta(minutes=ev_lead) else "")
            row.when.setText(local_when(occ.start))
            if alerts.get(ev.id):
                if not occ.live(now) and ev.kind != "hourly":
                    upcoming.append((occ.start, ev.name))
                if self.tracker.due(f"{ev.id}:{occ.start.isoformat()}", occ.start, now, ev_lead):
                    if not (quiet and ev.kind == "hourly"):
                        self.fire_alert(f"{ev.name} em {ev_lead} min", ev.detail or ev.en, ev.kind)

        for b in FIELD_BOSSES:
            row = self.field_rows[b.id]
            due = self.store.respawn_time(b.id)
            row.clear_btn.setVisible(due is not None)
            meta = self.store.kill_meta(b.id)
            if due is not None and meta.get("by"):
                origem = {"discord": " pelo Discord", "app": " pelo app"}.get(meta.get("via"), "")
                what = "Morte marcada" if meta.get("killed") else "Tempo informado"
                row.note.setText(f"{what} por {meta['by']}{origem}")
                row.note.show()
            else:
                row.note.hide()
            if due is None:
                row.countdown.setText("—")
                row.when.setText("sem registro")
                row.set_state("")
            elif due <= now:
                row.countdown.setText("pode ter nascido")
                row.when.setText(f"desde {due.astimezone():%H:%M}")
                row.set_state("ready")
            else:
                left = due - now
                row.countdown.setText(fmt_left(left))
                row.when.setText(f"às {local_when(due)}")
                row.set_state("soon" if left <= timedelta(minutes=lead) else "")
                if alerts.get(b.id):
                    upcoming.append((due, b.name))
                    if self.tracker.due(f"{b.id}:{due.isoformat()}", due, now, lead):
                        self.fire_alert(f"{b.name} em {lead} min", "Respawn pelo último registro do grupo.", "big")

        if upcoming:
            t_, name = min(upcoming)
            self.next_label.setText(f"Próximo alerta: <b>{name}</b> em {fmt_left(t_ - now)} ({local_when(t_)})")
        else:
            self.next_label.setText("Nenhum alerta de boss ligado. Ligue em “Alerta” nas linhas da aba Bosses.")
        self.group_dot.setText("● GRUPO ATIVO" if self.store.group_on and self.group_last_ok else "")
        self.update_today(now, tz, lead)
        self.update_keys(now)
        if now.second % 20 == 0:
            self.update_energy(now)

    def fire_alert(self, title: str, body: str, kind: str = "big"):
        s = self.store.settings
        if s.get("sound", True):
            play_alert(kind, s)
        if s.get("tray_notify", True) and self.tray.isVisible():
            self.tray.showMessage(title, body, QSystemTrayIcon.Information, 12000)
        QApplication.alert(self, 4000)

    # ------------------------------------------------------------- tray & update
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Diário de Daeva")
        menu = QMenu()
        a_open = QAction("Abrir", self, triggered=self.show_normal)
        a_test = QAction("Testar alerta", self, triggered=lambda: self.fire_alert("Teste de alerta", "Tudo certo."))
        a_quit = QAction("Sair", self, triggered=self.quit_app)
        menu.addAction(a_open)
        menu.addAction(a_test)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_normal() if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._really_quit = True
        self.titles_tab.stop_loading()
        try:
            self.store.save_title_cache()
        except OSError:
            pass
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e):
        if not self._really_quit and self.store.settings.get("close_to_tray") and self.tray.isVisible():
            e.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage("Diário de Daeva continua aberto",
                                      "Os alertas seguem ativos. Para sair, use o ícone na bandeja → Sair.",
                                      QSystemTrayIcon.Information, 6000)
            return
        self.quit_app()
        e.accept()

    def check_update(self):
        job = UpdateCheck()
        job.signals.found.connect(self.on_update_found)
        self.pool.start(job)

    def on_update_found(self, tag: str, url: str):
        self.update_btn.setText(f"Versão {tag} disponível")
        self.update_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        self.update_btn.show()
