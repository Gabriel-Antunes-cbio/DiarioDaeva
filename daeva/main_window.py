"""Janela principal: abas Bosses, Personagens e Ajustes, alertas e ícone na bandeja."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSystemTrayIcon, QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from . import GITHUB_REPO, __version__
from .chart import GrowthChart, fmt_int
from .group import GroupError, get_kills, normalize_url, ping, post_kill
from .profiles import ProfileError, fetch_profile, parse_link
from .schedule import (
    EVENTS, FIELD_BOSSES, REGIONS, AlertTracker, field_respawn, fmt_left, next_occurrence, now_utc,
)
from .sound import play_alert, resource
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


class FetchJob(QRunnable):
    def __init__(self, char_id: str, url: str):
        super().__init__()
        self.char_id, self.url = char_id, url
        self.signals = _Signals()

    def run(self):
        try:
            data = fetch_profile(parse_link(self.url))
            self.signals.done.emit(self.char_id, data, "")
        except ProfileError as e:
            self.signals.done.emit(self.char_id, None, str(e))
        except Exception as e:  # nunca derrubar o app por causa de um site
            self.signals.done.emit(self.char_id, None, f"Erro inesperado ao ler o perfil: {e}")


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
                res = post_kill(self.url, self.key, p["boss"], p["killed_at"], p["by"])
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


class KillTimeDialog(QDialog):
    def __init__(self, boss_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(boss_name)
        v = QVBoxLayout(self)
        v.addWidget(label(f"Que horas o {boss_name} morreu? (seu horário)", wrap=True))
        self.time = QTimeEdit(QTime.currentTime())
        self.time.setDisplayFormat("HH:mm")
        v.addWidget(self.time)
        v.addWidget(label("Se o horário for depois de agora, conto como ontem.", "muted", wrap=True))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Salvar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def chosen(self) -> datetime:
        now = datetime.now().astimezone()
        t = self.time.time()
        dt = now.replace(hour=t.hour(), minute=t.minute(), second=0, microsecond=0)
        if dt > now:
            dt -= timedelta(days=1)
        return dt


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
        head.addWidget(label("Diário de Daeva", "title"))
        head.addStretch(1)
        self.update_btn = QPushButton("Nova versão disponível")
        self.update_btn.setObjectName("primary")
        self.update_btn.hide()
        head.addWidget(self.update_btn)
        v.addLayout(head)
        self.next_label = label("", "next", wrap=True)
        v.addWidget(self.next_label)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_bosses_tab(), "Bosses")
        self.tabs.addTab(self._build_chars_tab(), "Personagens")
        self.tabs.addTab(self._build_settings_tab(), "Ajustes")
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

    # ------------------------------------------------------------- bosses tab
    def _scroll(self, inner: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
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
            v.addWidget(row)

        v.addSpacing(8)
        v.addWidget(label("BOSSES DE CAMPO · RENASCEM APÓS A MORTE", "section"))
        v.addWidget(label("Marque quando o boss cair. O mapa do jogo (Exploração → Field Boss) mostra o "
                          "estado real do seu canal.", "muted", wrap=True))
        self.group_line = label("", "muted", wrap=True)
        v.addWidget(self.group_line)
        for b in FIELD_BOSSES:
            row = EventRow(b.name, b.where, [(f"respawn {b.respawn_h}h", "tag")],
                           self.store.settings["alerts"].get(b.id, False),
                           lambda on, k=b.id: self.store.set_alert(k, on))
            kill = QPushButton("Morreu agora")
            kill.setObjectName("primary")
            kill.clicked.connect(lambda _=False, k=b.id: self.set_kill(k, now_utc()))
            at = QPushButton("Horário…")
            at.clicked.connect(lambda _=False, bb=b: self.ask_kill_time(bb))
            clear = QPushButton("Limpar")
            clear.clicked.connect(lambda _=False, k=b.id: self.set_kill(k, None))
            for w in (kill, at, clear):
                row.extra.addWidget(w)
            row.extra.addStretch(1)
            row.clear_btn = clear
            self.field_rows[b.id] = row
            v.addWidget(row)
        v.addStretch(1)
        return self._scroll(inner)

    def set_kill(self, boss_id: str, when: datetime | None):
        nick = (self.store.settings.get("nickname") or "").strip() or "alguém"
        self.store.set_kill(boss_id, when, nick, "app" if self.store.group_on else "local")
        if self.store.group_on:
            s = self.store.settings
            job = GroupJob("post", s["group_url"], s["group_key"],
                           {"boss": boss_id, "killed_at": when.isoformat() if when else None, "by": nick})
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

    def ask_kill_time(self, boss):
        dlg = KillTimeDialog(boss.name, self)
        if dlg.exec() == QDialog.Accepted:
            self.set_kill(boss.id, dlg.chosen())

    # ------------------------------------------------------------- chars tab
    def _build_chars_tab(self) -> QWidget:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(10)
        top = QHBoxLayout()
        self.char_combo = QComboBox()
        self.char_combo.currentIndexChanged.connect(lambda _: self.render_character())
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
        v.addStretch(1)
        self.reload_combo()
        return self._scroll(inner)

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
            self.char_combo.addItem(f"{c['name']} · {c['server']}", c["id"])
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
        if not has:
            return
        gl = c.get("gear_label") or "Gear score"
        self.c_name.setText(c["name"])
        region = REGIONS.get(c.get("region"), ("", ""))[0]
        bits = [c.get("cls") or "", f"Nível {c['level']}" if c.get("level") else "", c["server"], region]
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
        self.pool.start(job)
        self.render_character()

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

        v.addWidget(label("ALERTAS", "section"))
        row = QHBoxLayout()
        row.addWidget(label("Avisar"))
        self.lead = QSpinBox(minimum=1, maximum=30, value=int(s.get("alert_minutes", 5)), suffix=" min")
        self.lead.valueChanged.connect(lambda n: self.store.set_setting("alert_minutes", n))
        row.addWidget(self.lead)
        row.addWidget(label("antes do spawn"))
        row.addStretch(1)
        v.addLayout(row)
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
                          "Por padrão: Nahma, Executores, Vigia Kaira e Immortal Gartua.", "muted", wrap=True))

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
        cb_top = self._check("Sempre no topo (útil com o jogo em janela sem bordas)", "always_on_top")
        cb_top.toggled.connect(lambda _: self._apply_on_top())
        v.addWidget(cb_top)
        v.addWidget(self._check("Fechar para a bandeja (os alertas continuam funcionando)", "close_to_tray"))

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

        for ev in EVENTS:
            row = self.event_rows[ev.id]
            occ = next_occurrence(ev, now, tz)
            if occ is None:
                continue
            if occ.live(now):
                row.countdown.setText(f"termina em {fmt_left(occ.end - now)}")
                row.set_state("live")
            else:
                left = occ.start - now
                row.countdown.setText(fmt_left(left))
                row.set_state("soon" if left <= timedelta(minutes=lead) else "")
            row.when.setText(local_when(occ.start))
            if alerts.get(ev.id):
                if not occ.live(now):
                    upcoming.append((occ.start, ev.name))
                if self.tracker.due(f"{ev.id}:{occ.start.isoformat()}", occ.start, now, lead):
                    self.fire_alert(f"{ev.name} em {lead} min", ev.detail or ev.en)

        for b in FIELD_BOSSES:
            row = self.field_rows[b.id]
            kill = self.store.kill_time(b.id)
            due = field_respawn(b, kill)
            row.clear_btn.setVisible(kill is not None)
            meta = self.store.kill_meta(b.id)
            if kill is not None and meta.get("by"):
                origem = {"discord": " pelo Discord", "app": " pelo app"}.get(meta.get("via"), "")
                row.note.setText(f"Morte às {kill.astimezone():%H:%M}, marcada por {meta['by']}{origem}")
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
                    if self.tracker.due(f"{b.id}:{kill.isoformat()}", due, now, lead):
                        self.fire_alert(f"{b.name} em {lead} min", "Respawn calculado pela última morte marcada.")

        if upcoming:
            t, name = min(upcoming)
            self.next_label.setText(f"Próximo alerta: <b>{name}</b> em {fmt_left(t - now)} ({local_when(t)})")
        else:
            self.next_label.setText("Nenhum alerta ligado. Ligue em “Alerta” nas linhas da aba Bosses.")

    def fire_alert(self, title: str, body: str):
        s = self.store.settings
        if s.get("sound", True):
            play_alert()
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
