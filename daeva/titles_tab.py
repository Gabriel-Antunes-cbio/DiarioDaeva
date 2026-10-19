"""Aba Títulos: conquistas que dão título, sugestão de alvo e acompanhamento do progresso."""
from __future__ import annotations

import time
from datetime import timedelta

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .schedule import now_utc
from .store import Store, parse_iso
from .titles import (
    CREDIT, FOCUS, Achievement, TitleInfo, fetch_title, fmt_stats, load_achievements, score,
)

CACHE_DAYS = 14
GRADE_ORDER = {"Mythic": 6, "Legendary": 5, "Legend": 5, "Unique": 4, "Epic": 3, "Rare": 2, "Common": 1}
GRADE_PT = {"Legendary": "Lendário", "Legend": "Lendário", "Unique": "Único", "Epic": "Épico", "Rare": "Raro",
            "Common": "Comum", "Special": "Especial", "Mythic": "Mítico"}
FACTION_PT = {"Elyos": "Elyos", "Asmodian": "Asmodiano", "Both factions": "Ambas"}


def lbl(text="", name=None, wrap=True) -> QLabel:
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


class _LoadSignals(QObject):
    item = Signal(str, object)       # slug, dict | None
    finished = Signal(int, int)      # ok, falhas


class TitleLoader(QRunnable):
    """Lê a página de cada título na MetaBot.GG, devagar (1 por segundo), respeitando o limite deles."""

    def __init__(self, slugs: list[str]):
        super().__init__()
        self.slugs = slugs
        self.stop = False
        self.signals = _LoadSignals()

    def run(self):
        ok = fail = 0
        for slug in self.slugs:
            if self.stop:
                break
            try:
                info = fetch_title(slug)
                self.signals.item.emit(slug, info.to_dict())
                ok += 1
            except Exception:
                self.signals.item.emit(slug, None)
                fail += 1
            time.sleep(1.1)
        self.signals.finished.emit(ok, fail)


class TitlesTab(QWidget):
    def __init__(self, store: Store, current_char, parent=None):
        super().__init__(parent)
        self.store = store
        self.current_char = current_char  # função que devolve o personagem selecionado (dict) ou None
        self.items, self.groups = load_achievements()
        self.by_id = {a.id: a for a in self.items}
        self.loader: TitleLoader | None = None
        self.loaded_once = False
        self.fail_count = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        outer.addWidget(sa)
        inner = QWidget()
        sa.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 10, 4, 10)
        v.setSpacing(10)

        self.header = lbl("", "muted")
        v.addWidget(self.header)

        # --- alvo atual
        v.addWidget(lbl("SEU ALVO", "section"))
        self.target_card = QFrame(objectName="card")
        self.tc = QVBoxLayout(self.target_card)
        self.tc.setContentsMargins(14, 12, 14, 12)
        self.tc.setSpacing(6)
        v.addWidget(self.target_card)

        # --- sugestões
        row = QHBoxLayout()
        row.addWidget(lbl("SUGESTÕES PARA VOCÊ", "section", wrap=False))
        row.addStretch(1)
        row.addWidget(lbl("Prioridade", "muted", wrap=False))
        self.focus = QComboBox()
        for k, (name, _) in FOCUS.items():
            self.focus.addItem(name, k)
        self.focus.setCurrentIndex(max(0, self.focus.findData(self.store.titles.get("focus", "pve"))))
        self.focus.currentIndexChanged.connect(lambda _: (self.store.set_focus(self.focus.currentData()), self.refresh()))
        row.addWidget(self.focus)
        v.addLayout(row)
        v.addWidget(lbl("Títulos que faltam, da sua facção, ordenados pelos bônus que servem à prioridade escolhida. "
                        "O bônus de coleção pesa mais porque vale para sempre, mesmo sem equipar o título.", "muted"))
        self.sugg_box = QVBoxLayout()
        self.sugg_box.setSpacing(6)
        v.addLayout(self.sugg_box)

        # --- lista completa
        v.addSpacing(6)
        v.addWidget(lbl("TODAS AS CONQUISTAS COM TÍTULO", "section"))
        f = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar título ou conquista")
        self.search.textChanged.connect(lambda _: self.refresh_list())
        f.addWidget(self.search, 1)
        self.group = QComboBox()
        self.group.addItem("Todos os grupos", "")
        for gid, name in self.groups.items():
            self.group.addItem(name, gid)
        self.group.currentIndexChanged.connect(lambda _: self.refresh_list())
        f.addWidget(self.group)
        self.show_mode = QComboBox()
        for text, key in (("Faltando", "missing"), ("Todas", "all"), ("Que eu tenho", "owned")):
            self.show_mode.addItem(text, key)
        self.show_mode.currentIndexChanged.connect(lambda _: self.refresh_list())
        f.addWidget(self.show_mode)
        v.addLayout(f)
        self.count_label = lbl("", "muted")
        v.addWidget(self.count_label)
        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(5)
        v.addLayout(self.list_box)

        # --- rodapé: carregamento e crédito
        v.addSpacing(6)
        foot = QHBoxLayout()
        self.load_label = lbl("", "muted")
        foot.addWidget(self.load_label, 1)
        self.reload_btn = QPushButton("Atualizar bônus")
        self.reload_btn.clicked.connect(lambda: self.start_loading(force=True))
        foot.addWidget(self.reload_btn)
        v.addLayout(foot)
        credit = QPushButton(CREDIT + " ↗")
        credit.setFlat(True)
        credit.setStyleSheet("text-align:left; border:none; background:transparent; color:#e4ad55; padding:0")
        credit.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://metabot.gg/en/aion-2/achievements")))
        v.addWidget(credit)
        v.addStretch(1)

    # ------------------------------------------------------------- dados
    def char(self) -> dict | None:
        return self.current_char()

    def char_key(self) -> str:
        c = self.char()
        return c["id"] if c else "_geral"

    def faction(self) -> str:
        c = self.char()
        return (c or {}).get("faction", "")

    def info(self, slug: str) -> TitleInfo | None:
        d = self.store.title_cache.get(slug)
        return TitleInfo.from_dict(d) if d else None

    def visible_items(self) -> list[Achievement]:
        fac = self.faction()
        seen, out = set(), []
        for a in self.items:
            inf = self.info(a.slug)
            if inf and not inf.fits(fac):
                continue
            key = (a.slug, a.achievement)
            if key in seen:
                continue
            seen.add(key)
            out.append(a)
        return out

    # ------------------------------------------------------------- carregamento dos bônus
    def showEvent(self, e):
        super().showEvent(e)
        if not self.loaded_once:
            self.loaded_once = True
            self.start_loading()
        self.refresh()

    def start_loading(self, force: bool = False):
        if self.loader is not None:
            return
        limit = now_utc() - timedelta(days=CACHE_DAYS)
        slugs = []
        for slug in dict.fromkeys(a.slug for a in self.items):
            t = parse_iso((self.store.title_cache.get(slug) or {}).get("t"))
            if force or t is None or t < limit:
                slugs.append(slug)
        if not slugs:
            self.update_load_label()
            return
        self.fail_count = 0
        self.loader = TitleLoader(slugs)
        self.loader.signals.item.connect(self.on_title)
        self.loader.signals.finished.connect(self.on_load_done)
        self.pending = len(slugs)
        QThreadPool.globalInstance().start(self.loader)
        self.update_load_label()

    def on_title(self, slug: str, info):
        self.pending -= 1
        if info is None:
            self.fail_count += 1
        else:
            self.store.cache_title(slug, info, now_utc())
            if self.pending % 10 == 0:
                self.store.save_title_cache()
        self.update_load_label()
        if self.pending % 15 == 0:
            self.refresh()

    def on_load_done(self, ok: int, fail: int):
        self.loader = None
        self.store.save_title_cache()
        self.update_load_label()
        self.refresh()

    def stop_loading(self):
        if self.loader:
            self.loader.stop = True

    def update_load_label(self):
        total = len({a.slug for a in self.items})
        have = sum(1 for s in {a.slug for a in self.items} if s in self.store.title_cache)
        if self.loader is not None:
            self.load_label.setText(f"Lendo os bônus dos títulos na MetaBot.GG: {have} de {total}. "
                                    "Leva uns 4 minutos só na primeira vez.")
            self.reload_btn.setEnabled(False)
        else:
            msg = f"Bônus carregados: {have} de {total} títulos."
            if self.fail_count:
                msg += f" {self.fail_count} não puderam ser lidos agora; tente “Atualizar bônus” mais tarde."
            self.load_label.setText(msg)
            self.reload_btn.setEnabled(True)

    # ------------------------------------------------------------- render
    def refresh(self):
        c = self.char()
        owned = self.store.owned(self.char_key())
        vis = self.visible_items()
        vis_slugs = {a.slug for a in vis}
        fac = FACTION_PT.get(self.faction(), "")
        parts = []
        if c:
            parts.append(f"Personagem: <b>{c['name']}</b>" + (f" · {fac}" if fac else ""))
        parts.append(f"Marcados como seus: <b>{len(owned & vis_slugs)}</b> de {len(vis_slugs)} títulos de conquista")
        idx = ((c or {}).get("details") or {}).get("titles") or {}
        if idx.get("total"):
            parts.append(f"AION2 Index: {idx['total'][0]} de {idx['total'][1]} títulos de todos os tipos")
        if not fac and c:
            parts.append("Facção ainda desconhecida: mostrando as duas. Atualize o personagem na aba Personagens.")
        self.header.setText("<br>".join(parts))
        self.render_target()
        self.render_suggestions(vis, owned)
        self.refresh_list()

    def clear(self, layout):
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()

    def bonus_lines(self, slug: str) -> str:
        inf = self.info(slug)
        if inf is None:
            return "Bônus ainda não carregados."
        grade = GRADE_PT.get(inf.grade, inf.grade)
        return (f"{grade}{' · ' + FACTION_PT.get(inf.faction, inf.faction) if inf.faction else ''}<br>"
                f"Coleção (permanente): <b>{fmt_stats(inf.collection)}</b><br>"
                f"Equipado: {fmt_stats(inf.equip)}")

    def render_target(self):
        self.clear(self.tc)
        t = self.store.target(self.char_key())
        a = self.by_id.get(t["id"]) if t else None
        if a is None:
            self.tc.addWidget(lbl("Nenhum alvo escolhido. Use “Definir alvo” numa sugestão ou na lista abaixo.", "muted"))
            return
        self.tc.addWidget(lbl(a.title, "name"))
        self.tc.addWidget(lbl(f"Conquista: <b>{a.achievement}</b> ({self.groups.get(a.group, a.group)})<br>"
                              f"Meta: {a.goal}" + (" · conquista com vários níveis" if a.tiers else ""), "muted"))
        self.tc.addWidget(lbl(self.bonus_lines(a.slug)))
        n = a.target_count
        if n:
            row = QHBoxLayout()
            row.addWidget(lbl("Progresso", wrap=False))
            spin = QSpinBox(minimum=0, maximum=n, value=min(int(t.get("progress", 0)), n))
            spin.valueChanged.connect(lambda val: (self.store.set_progress(self.char_key(), val), bar_text.setText(f"{val} de {n} ({val * 100 // n}%)")))
            row.addWidget(spin)
            for step in (1, 10):
                if n >= step * 2:
                    b = QPushButton(f"+{step}")
                    b.clicked.connect(lambda _=False, s=step: spin.setValue(min(n, spin.value() + s)))
                    row.addWidget(b)
            bar_text = lbl(f"{spin.value()} de {n} ({spin.value() * 100 // n}%)", "up", wrap=False)
            row.addWidget(bar_text)
            row.addStretch(1)
            self.tc.addLayout(row)
            self.tc.addWidget(lbl("O jogo não informa o progresso para apps de fora: atualize olhando o diário de "
                                  "conquistas (ele mostra a contagem atual).", "muted"))
        btns = QHBoxLayout()
        done = QPushButton("Conquistei!")
        done.setObjectName("primary")
        done.clicked.connect(lambda: self.complete_target(a))
        drop = QPushButton("Remover alvo")
        drop.clicked.connect(lambda: (self.store.set_target(self.char_key(), None), self.refresh()))
        open_ = QPushButton("Ver na MetaBot.GG")
        open_.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(a.url)))
        for b in (done, drop, open_):
            btns.addWidget(b)
        btns.addStretch(1)
        self.tc.addLayout(btns)

    def complete_target(self, a: Achievement):
        self.store.set_owned(self.char_key(), a.slug, True)
        self.store.set_target(self.char_key(), None)
        self.refresh()

    def set_target(self, a: Achievement):
        self.store.set_target(self.char_key(), a.id)
        self.refresh()

    def render_suggestions(self, vis: list[Achievement], owned: set[str]):
        self.clear(self.sugg_box)
        focus = self.store.titles.get("focus", "pve")
        tgt = self.store.target(self.char_key())
        tgt_slug = self.by_id[tgt["id"]].slug if tgt and tgt["id"] in self.by_id else None
        cands = []
        for a in vis:
            if a.slug in owned or a.slug == tgt_slug:
                continue
            inf = self.info(a.slug)
            sc = score(inf, focus)
            if inf is None or (focus != "any" and sc == (0, 0)):
                continue
            cands.append((sc, GRADE_ORDER.get(inf.grade, 0), a))
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if not cands:
            msg = ("Carregando os bônus dos títulos…" if self.loader is not None
                   else "Nenhuma sugestão com essa prioridade. Experimente “Qualquer bônus”.")
            self.sugg_box.addWidget(lbl(msg, "muted"))
            return
        for _, _, a in cands[:5]:
            self.sugg_box.addWidget(self.title_row(a, owned, compact=False))

    def title_row(self, a: Achievement, owned: set[str], compact: bool) -> QFrame:
        fr = QFrame(objectName="row")
        g = QGridLayout(fr)
        g.setContentsMargins(12, 8, 12, 8)
        g.setHorizontalSpacing(10)
        has = a.slug in owned
        cb = QCheckBox()
        cb.setChecked(has)
        cb.setToolTip("Marque se você já tem este título")
        cb.toggled.connect(lambda on, s=a.slug: (self.store.set_owned(self.char_key(), s, on), self.refresh()))
        g.addWidget(cb, 0, 0, Qt.AlignTop)
        title = lbl(f"<b>{a.title}</b>")
        g.addWidget(title, 0, 1)
        sub = f"{a.achievement} · {a.goal}"
        g.addWidget(lbl(sub, "muted"), 1, 1)
        if compact:
            inf = self.info(a.slug)
            if inf is not None:
                g.addWidget(lbl(f"Coleção: {fmt_stats(inf.collection)} · Equipado: {fmt_stats(inf.equip)}", "muted"), 2, 1)
        else:
            g.addWidget(lbl(self.bonus_lines(a.slug)), 2, 1)
        btn = QPushButton("Definir alvo")
        btn.clicked.connect(lambda _=False, x=a: self.set_target(x))
        btn.setEnabled(not has)
        g.addWidget(btn, 0, 2, Qt.AlignTop)
        g.setColumnStretch(1, 1)
        return fr

    def refresh_list(self):
        self.clear(self.list_box)
        owned = self.store.owned(self.char_key())
        q = self.search.text().strip().lower()
        gid = self.group.currentData()
        mode = self.show_mode.currentData()
        rows = []
        for a in self.visible_items():
            if gid and a.group != gid:
                continue
            if mode == "missing" and a.slug in owned or mode == "owned" and a.slug not in owned:
                continue
            if q and q not in a.title.lower() and q not in a.achievement.lower() and q not in a.goal.lower():
                continue
            rows.append(a)
        self.count_label.setText(f"{len(rows)} conquistas")
        for a in rows:
            self.list_box.addWidget(self.title_row(a, owned, compact=True))
