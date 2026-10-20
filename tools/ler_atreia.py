"""Lê uma página de classe do Atreia Lens copiada inteira (Ctrl+A, Ctrl+C) para texto.

Uso: python tools/ler_atreia.py tools/bis_fontes/paginas/cleric.txt
Devolve um dicionário com a build: skills, stigmas, arcanas, equipamentos, asas, títulos e notas.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SLOTS = ["Arma", "Guarda", "Elmo", "Ombreiras", "Peitoral", "Calças", "Luvas", "Botas", "Capa", "Colar",
         "Brinco (esq.)", "Brinco (dir.)", "Anel (esq.)", "Anel (dir.)", "Bracelete (esq.)", "Bracelete (dir.)"]
VALUE = re.compile(r"^[+-]?\d[\d.,]*%?$")
ARCANA_TITLE = re.compile(r"^(Cálice|Manuscrito|Bússola|Sino|Espelho) d[aoe] (\w+) \+(\d+)$")
BONUS = ("Base", "Daevanion", "Arcanas", "Jóias")


def _idx(lines, value, start=0, pred=None):
    for i in range(start, len(lines)):
        if lines[i] == value and (pred is None or pred(i)):
            return i
    raise ValueError(f"não achei '{value}' depois da linha {start}")


def _paragraphs(lines, start, stop_values):
    out = []
    for line in lines[start:]:
        if line in stop_values:
            break
        out.append(line)
    return out


def _num(v: str) -> int:
    return int(v.replace("+", ""))


def parse(text: str) -> dict:
    L = [l.strip() for l in text.splitlines() if l.strip()]
    b = {}
    i = _idx(L, "Build da comunidade")
    b["build"] = L[i + 1]
    j = _idx(L, "partes preenchidas", i)
    b["mode"], b["stage"], b["faction"], b["weapon"] = L[j - 5], L[j - 4], L[j - 3], L[j - 2]

    # ---- skills ativas (painel): nome, "Nível final N", Base/Daevanion/Arcanas/Jóias, efeitos das especializações
    s0 = _idx(L, "Skills ativas")
    st0 = _idx(L, "Stigmas", s0)
    skills, k = [], s0 + 1
    while k < st0:
        if k + 1 < st0 and L[k + 1].startswith("Nível final"):
            sk = {"pt": L[k], "final": int(L[k + 1].split()[-1]), "base": 0, "daevanion": 0, "arcanas": 0,
                  "joias": 0, "effects": []}
            k += 2
            while k < st0 and not (k + 1 < st0 and L[k + 1].startswith("Nível final")):
                if L[k] in BONUS and k + 1 < st0 and VALUE.match(L[k + 1]):
                    key = {"Base": "base", "Daevanion": "daevanion", "Arcanas": "arcanas", "Jóias": "joias"}[L[k]]
                    sk[key] = _num(L[k + 1])
                    k += 2
                else:
                    sk["effects"].append(L[k])
                    k += 1
            skills.append(sk)
        else:
            k += 1
    b["skills"] = skills

    # ---- stigmas
    n0 = _idx(L, "Notas de skills", st0)
    b["stigmas"] = [{"pt": L[k], "rank": int(L[k + 1].split()[-1])}
                    for k in range(st0 + 1, n0 - 1) if L[k + 1].startswith("Rank")]

    # ---- notas de skills (até o título da seção Arcanas)
    a0 = _idx(L, "Arcanas", n0, pred=lambda x: x + 1 < len(L) and ARCANA_TITLE.match(L[x + 1]))
    b["skill_notes"] = L[n0 + 1:a0]

    # ---- arcanas
    d0 = _idx(L, "Daevanion", a0, pred=lambda x: x + 1 < len(L) and "pontos usados" in L[x + 1])
    arcanas, k = [], a0 + 1
    while k < d0:
        m = ARCANA_TITLE.match(L[k])
        if not m:
            k += 1
            continue
        arc = {"name": L[k], "base": m.group(1), "kind": m.group(2), "refine": int(m.group(3)),
               "god": f"{L[k + 2]} {L[k + 3]}", "lines": []}
        k += 4
        while k + 1 < d0 and not ARCANA_TITLE.match(L[k]) and VALUE.match(L[k + 1]):
            arc["lines"].append({"name": L[k], "value": L[k + 1]})
            k += 2
        arcanas.append(arc)
    b["arcanas"] = arcanas

    # ---- rotação (primeiro parágrafo)
    try:
        r0 = _idx(L, "Rotação · macro + setup", d0)
        b["rotation"] = L[r0 + 1]
    except ValueError:
        b["rotation"] = ""

    # ---- equipamentos
    e0 = _idx(L, "Prioridade dos substats", d0)
    e1 = _idx(L, "Total do equipamento", e0)
    body = L[e0:e1]
    slots, k = [], 0
    while k < len(body):
        if body[k] not in SLOTS:
            k += 1
            continue
        slot = {"slot": body[k], "substats": [], "also": [], "stone": None, "stone_lines": [], "divine": None}
        k = body.index("Substats", k) + 1
        while k + 2 < len(body) and body[k].isdigit() and not VALUE.match(body[k + 1]) and VALUE.match(body[k + 2]):
            slot["substats"].append({"name": body[k + 1], "ref": body[k + 2]})
            k += 3
        if k < len(body) and body[k] == "Também servem":
            k += 1
            while k < len(body) and body[k] != "Pedra de Mana":
                slot["also"].append(body[k])
                k += 1
        if k < len(body) and body[k] == "Pedra de Mana":
            slot["stone"] = body[k + 1]
            k += 2
            while k + 1 < len(body) and body[k] not in SLOTS and body[k] != "Pedras Divinas" and VALUE.match(body[k + 1]):
                slot["stone_lines"].append({"name": body[k], "ref": body[k + 1]})
                k += 2
        if k < len(body) and body[k] == "Pedras Divinas":
            slot["divine"] = body[k + 1]
            k += 2
        slots.append(slot)
    if len(slots) < 10 or any(len(s["substats"]) != 5 for s in slots):
        raise SystemExit("A parte Equipamentos veio incompleta.")
    b["gear"] = slots
    g0 = _idx(L, "Notas de equipamentos", e1)
    w0 = _idx(L, "Asas & Títulos", g0)
    b["gear_notes"] = L[g0 + 1:w0]

    # ---- asas e títulos
    wa = _idx(L, "Asa equipada", w0)
    ti = _idx(L, "Títulos equipados", wa)
    wn = _idx(L, "Notas de asas e títulos", ti)
    wings = []
    for k in range(wa + 1, ti):
        if L[k] in ("Único", "Lendário", "Heroico", "Épico"):
            continue
        main = L[k].endswith("Principal")
        wings.append({"name": L[k][:-9] if main else L[k], "main": main})
    b["wings"] = wings
    titles, k = [], ti + 1
    while k < wn:
        if k + 1 < wn and L[k + 1] in ("Ataque", "Defesa", "Utilidade") and not VALUE.match(L[k]):
            main = L[k].endswith("Principal")
            t = {"name": L[k][:-9] if main else L[k], "main": main, "type": L[k + 1], "stats": []}
            k += 2
            while k + 1 < wn and VALUE.match(L[k + 1]) and not (k + 2 < wn and L[k + 2] in ("Ataque", "Defesa", "Utilidade") and False):
                t["stats"].append({"name": L[k], "value": L[k + 1]})
                k += 2
            titles.append(t)
        else:
            k += 1
    b["titles"] = titles
    p0 = _idx(L, "Panteão", wn)
    b["wings_notes"] = L[wn + 1:p0]
    return b


if __name__ == "__main__":
    print(json.dumps(parse(Path(sys.argv[1]).read_text(encoding="utf-8")), ensure_ascii=False, indent=1))
