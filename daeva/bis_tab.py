"""Aba BiS: o personagem selecionado comparado com a build da classe dele."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from . import bis, theme

STATUS_TXT = {
    "max": ("na meta", theme.OK), "acima": ("acima da meta", theme.OK), "ok": ("na meta", theme.OK), "falta": ("falta {gap}", theme.WARN),
    "fora": ("fora da build", theme.MUTED), "fora_ok": ("fora da build", theme.MUTED),
    "sem_dado": ("sem dado", theme.MUTED), "nao_aprendido": ("não aprendido", theme.WARN),
    "igual": ("igual aos top", theme.OK), "refinar": ("refinar +{gap}", theme.WARN),
    "grau_acima": ("grau acima", theme.OK), "grau_abaixo": ("grau abaixo", theme.WARN),
    "outro": ("outro item", theme.MUTED), "vazio": ("vazio", theme.WARN),
    "tipo_errado": ("tipo diferente", theme.WARN),
}
SECTIONS = (("skills", "Skills"), ("stigmas", "Stigmas"), ("arcana", "Arcanas"), ("gear", "Equipamento"),
            ("ref", "Referência"))


def esc(t) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tag(status: str, gap: int = 0) -> str:
    text, color = STATUS_TXT.get(status, (status, theme.MUTED))
    return f"<span style='color:{color}'>{esc(text.format(gap=gap))}</span>"


def lbl(text="", name=None, wrap=True) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<td style='color:{theme.MUTED};padding:0 12px 4px 0'>{h}</td>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td style='padding:3px 12px 3px 0'>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{tr}</table>"


class BisTab(QWidget):
    def __init__(self, current_char, parent=None):
        super().__init__(parent)
        self.current_char = current_char
        self.section = "skills"
        self.data = bis.load()
        self.result: dict | None = None

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

        self.header = lbl("", "name")
        self.sub = lbl("", "muted")
        v.addWidget(self.header)
        v.addWidget(self.sub)

        self.stats = QHBoxLayout()
        self.stats.setSpacing(10)
        self.stat_labels = []
        for title in ("SKILLS NA META", "STIGMAS NA META", "ARCANAS CERTAS"):
            f = QFrame(objectName="stat")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(10, 8, 10, 8)
            fl.setSpacing(2)
            t = lbl(title, "section")
            val = lbl("", "bigval")
            note = lbl("", "muted")
            for w in (t, val, note):
                fl.addWidget(w)
            self.stats.addWidget(f)
            self.stat_labels.append((val, note))
        v.addLayout(self.stats)

        v.addWidget(lbl("O QUE FAZER PRIMEIRO", "section"))
        self.todo = lbl("")
        self.todo.setTextFormat(Qt.RichText)
        todo_card = QFrame(objectName="card")
        tl = QVBoxLayout(todo_card)
        tl.setContentsMargins(14, 12, 14, 12)
        tl.addWidget(self.todo)
        v.addWidget(todo_card)

        seg = QHBoxLayout()
        self.seg_btns = {}
        for key, text in SECTIONS:
            b = QPushButton(text, objectName="seg", checkable=True)
            b.clicked.connect(lambda _=False, k=key: self.set_section(k))
            seg.addWidget(b)
            self.seg_btns[key] = b
        seg.addStretch(1)
        v.addLayout(seg)
        card = QFrame(objectName="card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        self.body = lbl("")
        self.body.setTextFormat(Qt.RichText)
        cl.addWidget(self.body)
        v.addWidget(card)

        self.note = lbl("", "muted")
        self.note.setTextFormat(Qt.RichText)
        self.note.setOpenExternalLinks(True)
        v.addWidget(self.note)
        foot = QHBoxLayout()
        self.open_build = QPushButton("Abrir a build no Atreia Lens")
        self.open_build.clicked.connect(self._open_build)
        foot.addWidget(self.open_build)
        foot.addStretch(1)
        v.addLayout(foot)
        v.addStretch(1)
        self.refresh()

    # ------------------------------------------------------------------
    def set_section(self, key: str):
        self.section = key
        self.render_section()

    def _open_build(self):
        if self.result:
            QDesktopServices.openUrl(QUrl(f"https://atreialens.hartmannlab.xyz/{self.result['class']}"))

    def refresh(self):
        c = self.current_char()
        d = (c or {}).get("details") or {}
        self.result = None
        if not c:
            self._empty("Adicione um personagem na aba Personagens para ver a comparação.")
            return
        cid = bis.class_id(c.get("cls") or "")
        if not cid:
            self._empty("Ainda não sei a classe deste personagem. Clique em “Atualizar agora” na aba Personagens.")
            return
        if not d.get("skills") and not d.get("gear"):
            self._empty("Ainda sem skills e equipamento lidos. Clique em “Atualizar agora” na aba Personagens.")
            return
        self.result = bis.compare(c["cls"], c.get("level"), d.get("skills"), d.get("gear"), self.data)
        self.render()

    def _empty(self, msg: str):
        self.header.setText("BiS")
        self.sub.setText(msg)
        for w in (self.todo, self.body):
            w.setText("")
        for val, note in self.stat_labels:
            val.setText("—")
            note.setText("")
        self.open_build.setEnabled(False)
        self.note.setText("")

    def render(self):
        r, c = self.result, self.current_char()
        self.open_build.setEnabled(True)
        self.header.setText(f"{c['name']} · {r['build']}")
        lvl = f"nível {r['level']}" if r.get("level") else ""
        sub = "Comparado com a build da classe no Atreia Lens."
        if not r["endgame"]:
            sub += f" Você está no {lvl}: as metas da build são de nível 45."
        self.sub.setText(sub)
        s = r["summary"]
        vals = [
            (f"{s['skills_ok']} de {s['skills_total']}", "skills da build"),
            (f"{s['stigmas_ok']} de {s['stigmas_total']}", "stigmas principais"),
            (f"{s['arcana_ok']} de {s['arcana_total']}" if s["arcana_known"] else "—",
             "tipo igual ao da build" if s["arcana_known"] else "não aparecem no perfil"),
        ]
        for (val, note), (a, b) in zip(self.stat_labels, vals):
            val.setText(a)
            note.setText(b)
        if r["todo"]:
            self.todo.setText("<br>".join(
                f"<b style='color:{theme.ACCENT}'>{i}</b>&nbsp; <b>{esc(t['title'])}</b><br>"
                f"<span style='color:{theme.MUTED}'>{esc(t['why'])}</span>" for i, t in enumerate(r["todo"], 1)))
        else:
            self.todo.setText("Nada urgente: o personagem já está na meta da build.")
        self.note.setText(
            "Os níveis de skill do AION2 Index já somam o bônus do Daevanion. "
            f"Build: <a style='color:{theme.LIVE}' href='https://atreialens.hartmannlab.xyz/{r['class']}'>Atreia Lens</a> · "
            f"nível médio das skills: <a style='color:{theme.LIVE}' "
            f"href='https://gamewith.ai/aion2/en/build-stats/la/{r['gw_slug']}'>GameWith</a>.")
        self.render_section()

    def render_section(self):
        for k, b in self.seg_btns.items():
            b.setChecked(k == self.section)
        r = self.result
        if not r:
            return
        if self.section == "skills":
            rows = []
            for s in r["skills"]:
                have = "—" if s["have"] is None else str(s["have"])
                meta = s["target"] or "N/A"
                rows.append([esc(s["pt"]), f"<b>{have}</b>", esc(meta), esc(s["specs"] or "—"),
                             f"{s['avg']:.1f}".replace(".", ",") if s.get("avg") is not None else "—",
                             tag(s["status"], s["gap"])])
            html = table(["SKILL", "VOCÊ", "META", "ESPEC.", "MÉDIA TOP", ""], rows)
            pas = ", ".join(f"{esc(p['pt'])} <b>{p['have'] if p['have'] is not None else '—'}</b>" for p in r["passives"])
            html += f"<p><span style='color:{theme.MUTED}'>Passivas, em ordem de prioridade:</span> {pas}</p>"
        elif self.section == "stigmas":
            rows = [[esc(s["pt"]), f"<b>{'—' if s['have'] is None else s['have']}</b>", str(s["target"]),
                     tag(s["status"], s["gap"])] for s in r["stigmas"]["main"]]
            html = table(["STIGMA PRINCIPAL", "VOCÊ", "RANK", ""], rows)
            alt = ", ".join(f"{esc(a['pt'])} <b>{'—' if a['have'] is None else a['have']}</b>" for a in r["stigmas"]["alt"])
            if alt:
                html += f"<p><span style='color:{theme.MUTED}'>Alternativas:</span> {alt}</p>"
            html += (f"<p style='color:{theme.MUTED}'>O AION2 Index não diz quais stigmas estão equipados, "
                     "só o nível de cada um.</p>")
        elif self.section == "arcana":
            if r["arcana"]:
                rows = []
                for a in r["arcana"]:
                    have = a["have"]
                    mine = f"{esc(a['arcana'])} de {esc(have['kind'])} +{have['enchant']}" if have else "—"
                    rows.append([esc(a["arcana"]), f"de {esc(a['want'])}", esc(a["gods"]), mine, tag(a["status"])])
                html = table(["ARCANA", "BUILD", "DEUSES", "VOCÊ", ""], rows)
            else:
                html = ""
            if r["arcana_note"]:
                html += f"<p>{esc(r['arcana_note'])}</p>"
            if not r["summary"]["arcana_known"]:
                html += f"<p style='color:{theme.MUTED}'>As arcanas deste personagem não aparecem no perfil público.</p>"
            top = ", ".join(f"{esc(a['name'])} {a['share_pct']}%" for a in r["arcana_stats"])
            html += f"<p><span style='color:{theme.MUTED}'>Mais usadas pelos top:</span> {top}</p>"
        elif self.section == "gear":
            gs = r["gear_stats"]

            def steps(lst):
                return "".join(f"<tr><td style='color:{theme.ACCENT};padding:2px 10px 2px 0'><b>{i}</b></td>"
                               f"<td>{' ≈ '.join(esc(x) for x in step)}</td></tr>" for i, step in enumerate(lst, 1))
            html = (f"<p><b>Status para buscar nos itens</b> "
                    f"<span style='color:{theme.MUTED}'>(prioridade de aprimoramento da {esc(r['build'])})</span></p>"
                    f"<table>{steps(gs['substats'])}</table>"
                    f"<p><b>Manastones</b></p><table>{steps(gs['manastones'])}</table>")
            if gs["notes"]:
                html += "<p style='color:%s'>%s</p>" % (theme.MUTED, "<br>".join(esc(n) for n in gs["notes"]))
            html += f"<p style='color:{theme.MUTED}'>≈ quer dizer que os dois valem quase o mesmo.</p>"
        else:
            t = r["titles"]
            html = (f"<p><b>Aprimoramento:</b> {esc(' → '.join(r['enhancing']))}</p>"
                    f"<p><b>Manastones:</b> {esc(' → '.join(r['manastones']))}</p>"
                    f"<p><b>Títulos ofensivos:</b> {esc(', '.join(t.get('offensive', [])))}<br>"
                    f"<b>Defensivos:</b> {esc(', '.join(t.get('defensive', [])))}<br>"
                    f"<b>Utilidade:</b> {esc(', '.join(t.get('utility', [])))}</p>"
                    f"<p><b>Asas:</b> {esc(', '.join(r['wings']))}</p>")
        self.body.setText(html)
