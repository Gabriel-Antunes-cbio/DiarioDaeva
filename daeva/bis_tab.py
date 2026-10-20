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
    "refinar": ("refinar +{gap}", theme.WARN), "vazio": ("vazio", theme.WARN),
    "tipo_errado": ("tipo diferente", theme.WARN),
}
SECTIONS = (("skills", "Skills"), ("stigmas", "Stigmas"), ("arcana", "Arcanas"), ("gear", "Equipamento"),
            ("wings", "Asas e títulos"), ("notes", "Notas"))


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
        self.body.setText("")
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
        sub = f"Comparado com a build da classe no Atreia Lens ({r['mode']} · {r['stage']} · {r['weapon']})."
        if not r["endgame"]:
            sub += f" Você está no {lvl}: as metas da build são de nível 45."
        self.sub.setText(sub)
        s = r["summary"]
        vals = [
            (f"{s['skills_ok']} de {s['skills_total']}", "skills da build"),
            (f"{s['stigmas_ok']} de {s['stigmas_total']}", "stigmas principais"),
            (f"{s['arcana_ok']} de {s['arcana_total']}" if s["arcana_known"] else "—",
             "tipo e refino da build" if s["arcana_known"] else "não aparecem no perfil"),
        ]
        for (val, note), (a, b) in zip(self.stat_labels, vals):
            val.setText(a)
            note.setText(b)
        self.note.setText(
            "Os níveis de skill do AION2 Index já somam o bônus do Daevanion. "
            f"Build completa: <a style='color:{theme.LIVE}' href='https://atreialens.hartmannlab.xyz/{r['class']}'>"
            "Atreia Lens (atreialens.hartmannlab.xyz)</a>, feito pela comunidade.")
        self.render_section()

    def render_section(self):
        for k, b in self.seg_btns.items():
            b.setChecked(k == self.section)
        r = self.result
        if not r:
            return
        muted = lambda t: f"<span style='color:{theme.MUTED}'>{t}</span>"
        if self.section == "skills":
            rows = []
            for s in r["skills"]:
                p = s["parts"]
                parts = " + ".join(f"{v} {k}" for k, v in (("base", p["base"]), ("Daevanion", p["daevanion"]),
                                                            ("arcanas", p["arcanas"]), ("joias", p["joias"])) if v)
                rows.append([esc(s["pt"]) + "<br>" + muted(esc(" · ".join(s["effects"]))),
                             f"<b>{'—' if s['have'] is None else s['have']}</b>", str(s["target"]), muted(esc(parts)),
                             tag(s["status"], s["gap"])])
            html = table(["SKILL", "VOCÊ", "META", "COMPOSIÇÃO DA META", ""], rows)
            pas = ", ".join(f"{esc(p['pt'])} <b>{p['have'] if p['have'] is not None else '—'}</b>" for p in r["passives"])
            html += f"<p>{muted('Passivas, em ordem de prioridade:')} {pas}</p>"
        elif self.section == "stigmas":
            rows = [[esc(s["pt"]), f"<b>{'—' if s['have'] is None else s['have']}</b>", str(s["target"]),
                     tag(s["status"], s["gap"])] for s in r["stigmas"]["main"]]
            html = table(["STIGMA", "VOCÊ", "RANK", ""], rows)
            alt = ", ".join(f"{esc(a['pt'])} <b>{'—' if a['have'] is None else a['have']}</b>" for a in r["stigmas"]["alt"])
            if alt:
                html += f"<p>{muted('Também bons:')} {alt}</p>"
            html += f"<p>{muted('O AION2 Index não diz quais stigmas estão equipados, só o nível de cada um.')}</p>"
        elif self.section == "arcana":
            html = ""
            for a in r["arcana"]:
                have = a["have"]
                mine = (f"você: {esc(a['base'])} {'da' if have['kind'] == 'Mana' else 'do'} {esc(have['kind'])} "
                        f"+{have['enchant']}") if have else "você: —"
                lines = ", ".join(f"{esc(x['name'])} {esc(x['value'])}" for x in a["lines"])
                html += (f"<p style='margin-top:10px'><b>{esc(a['name'])}</b> · {esc(a['god'])} "
                         f"{'' if a['status'] == 'sem_dado' else tag(a['status'], a['refine_gap'])}<br>"
                         f"{muted(lines)}<br>{muted(mine)}</p>")
            if not r["summary"]["arcana_known"]:
                html += f"<p>{muted('As arcanas deste personagem não aparecem no perfil público.')}</p>"
        elif self.section == "gear":
            html = f"<p>{muted('Substatus para buscar em cada peça, do mais importante (1) ao menos importante (5). O valor é a referência da build.')}</p>"
            for g in r["gear_slots"]:
                stone = esc(g["stone"] or "")
                if g.get("divine"):
                    stone += f" · Pedra Divina: {esc(g['divine'])}"
                rows = "".join(
                    f"<tr><td style='color:{theme.ACCENT};padding:1px 10px 1px 0'><b>{n}</b></td>"
                    f"<td style='padding:1px 14px 1px 0'>{esc(x['name'])}</td>"
                    f"<td style='color:{theme.MUTED}'>{esc(x['ref'])}</td></tr>"
                    for n, x in enumerate(g["substats"], 1))
                html += f"<p style='margin-top:12px'><b>{esc(g['name'].upper())}</b>{muted(' · ' + stone)}</p><table>{rows}</table>"
                if g["also"]:
                    html += f"<p>{muted('Também servem: ' + esc(', '.join(g['also'])))}</p>"
            if r["gear_notes"]:
                html += "<p style='margin-top:12px'><b>Notas de equipamentos</b></p>" + "".join(
                    f"<p>{muted(esc(n))}</p>" for n in r["gear_notes"])
        elif self.section == "wings":
            wings = ", ".join(esc(w["name"]) + (" <b>(principal)</b>" if w["main"] else "") for w in r["wings"])
            html = f"<p><b>Asas:</b> {wings}</p>"
            for kind in ("Ataque", "Defesa", "Utilidade"):
                ts = [t for t in r["titles"] if t["type"] == kind]
                if ts:
                    html += f"<p style='margin-top:10px'><b>Títulos de {kind.lower()}</b></p>"
                    for t in ts:
                        stats = ", ".join(f"{esc(x['name'])} {esc(x['value'])}" for x in t["stats"])
                        html += (f"<p>{esc(t['name'])}{' <b>(principal)</b>' if t['main'] else ''}"
                                 f"{'<br>' + muted(stats) if stats else ''}</p>")
            html += "".join(f"<p>{muted(esc(n))}</p>" for n in r["wings_notes"])
        else:
            html = f"<p><b>Rotação</b></p><p>{muted(esc(r['rotation']))}</p><p><b>Notas de skills</b></p>"
            html += "".join(f"<p>{muted(esc(n))}</p>" for n in r["skill_notes"])
        self.body.setText(html)
