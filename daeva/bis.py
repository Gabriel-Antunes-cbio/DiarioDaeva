"""Aba BiS: compara o personagem com a build da classe dele no Atreia Lens.

Tudo da build (skills, stigmas, arcanas, substatus de cada peça, asas, títulos e notas) vem das páginas de
classe do Atreia Lens, guardadas em daeva/data/bis.json (gerado por tools/gerar_bis.py).
Do personagem vêm só os dados dele: skills (AION2 Index) e arcanas (Shugo.GG).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "bis.json"
END_LEVEL = 45

CLASS_ALIASES = {
    "gladiator": "gladiator", "gladiador": "gladiator",
    "templar": "templar", "templario": "templar",
    "assassin": "assassin", "assassino": "assassin",
    "ranger": "ranger", "cacador": "ranger",
    "sorcerer": "sorcerer", "feiticeiro": "sorcerer",
    "spiritmaster": "spirit-master", "elementalist": "spirit-master", "espiritualista": "spirit-master",
    "cleric": "cleric", "clerigo": "cleric",
    "chanter": "chanter", "cantor": "chanter",
}
# Arcanas no Shugo.GG ("Chalice of Vigor +1") -> nomes do Atreia Lens ("Cálice do Vigor")
ARCANA_BASE = {"chalice": "Cálice", "parchment": "Manuscrito", "scroll": "Manuscrito", "manuscript": "Manuscrito",
               "compass": "Bússola", "bell": "Sino", "mirror": "Espelho"}
ARCANA_KIND = {"vigor": "Vigor", "magic": "Mana", "mana": "Mana"}


def load(path: Path = DATA_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(s: str | None) -> str:
    s = (s or "").lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))
    return re.sub(r"[^a-z0-9]", "", s)


def class_id(cls: str) -> str | None:
    return CLASS_ALIASES.get(_key(cls))


def _levels(skills: dict | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for group in ("active", "passive", "stigma"):
        for name, lvl in (skills or {}).get(group, []):
            out[_key(name)] = int(lvl)
    return out


def compare_skills(build: dict, levels: dict[str, int]) -> list[dict]:
    rows = []
    for s in build["skills"]:
        have = levels.get(_key(s["en"]))
        row = {"pt": s["pt"], "en": s["en"], "have": have, "target": s["final"],
               "parts": {k: s[k] for k in ("base", "daevanion", "arcanas", "joias")}, "effects": s["effects"]}
        if have is None:
            row["status"], row["gap"] = "sem_dado", 0
        elif have > s["final"]:
            row["status"], row["gap"] = "acima", 0
        elif have == s["final"]:
            row["status"], row["gap"] = "max", 0
        else:
            row["status"], row["gap"] = "falta", s["final"] - have
        rows.append(row)
    return rows


def compare_stigmas(build: dict, levels: dict[str, int], learned: set[str]) -> dict:
    main = []
    for s in build["stigmas"]:
        k = _key(s["en"])
        known = k in learned
        have = levels.get(k) if known else None
        if not known:
            status, gap = "nao_aprendido", s["rank"]
        elif have >= s["rank"]:
            status, gap = "ok", 0
        else:
            status, gap = "falta", s["rank"] - have
        main.append({"pt": s["pt"], "en": s["en"], "have": have, "target": s["rank"], "status": status, "gap": gap})
    alt = [{"pt": a["pt"], "have": levels.get(_key(a["en"])) if a["en"] and _key(a["en"]) in learned else None}
           for a in build["stigmas_alt"]]
    return {"main": main, "alt": alt}


def compare_arcana(build: dict, gear: list[dict] | None) -> list[dict]:
    """O Shugo.GG lista as arcanas como linhas Arcana1..5 ('Chalice of Vigor +1')."""
    mine = {}
    for piece in gear or []:
        if not piece["slot"].strip().lower().startswith("arcana"):
            continue
        m = re.match(r"(\w+) of (\w+)", piece["item"].strip(), re.I)
        if m and m.group(1).lower() in ARCANA_BASE:
            mine[ARCANA_BASE[m.group(1).lower()]] = {
                "kind": ARCANA_KIND.get(m.group(2).lower(), m.group(2)),
                "enchant": int(piece.get("enchant", 0)), "grade": piece.get("grade", "")}
    rows = []
    for a in build["arcanas"]:
        have = mine.get(a["base"])
        if not mine:
            status = "sem_dado"
        elif not have:
            status = "vazio"
        elif have["kind"] != a["kind"]:
            status = "tipo_errado"
        elif have["enchant"] < a["refine"]:
            status = "refinar"
        else:
            status = "ok"
        rows.append({**a, "have": have, "status": status,
                     "refine_gap": max(0, a["refine"] - have["enchant"]) if have and status == "refinar" else 0})
    return rows


def group_slots(slots: list[dict] | None) -> list[dict]:
    """Junta esquerda e direita quando a recomendação é igual ("Brinco (esq.)" + "(dir.)" -> "Brincos")."""
    plural = {"Brinco": "Brincos", "Anel": "Anéis", "Bracelete": "Braceletes"}
    out = []
    for s in slots or []:
        base = s["slot"].split(" (")[0]
        same = {k: s[k] for k in ("substats", "also", "stone", "stone_lines", "divine")}
        prev = out[-1] if out else None
        if prev and prev["_base"] == base and prev["_same"] == same and base in plural:
            prev["name"] = plural[base]
            continue
        out.append({"_base": base, "_same": same, "name": s["slot"], **same})
    for o in out:
        del o["_base"], o["_same"]
    return out


def compare(cls: str, level: int | None, skills: dict | None, gear: list[dict] | None, data: dict | None = None) -> dict:
    data = data or load()
    cid = class_id(cls)
    if not cid:
        raise ValueError(f"Classe desconhecida: {cls!r}")
    b = data["classes"][cid]
    levels = _levels(skills)
    learned = {_key(n) for n, _ in (skills or {}).get("stigma", [])}
    r = {
        "class": cid, "build": b["build"], "weapon": b["weapon"], "mode": b["mode"], "stage": b["stage"],
        "level": level, "endgame": (level or 0) >= END_LEVEL,
        "skills": compare_skills(b, levels),
        "passives": [{"pt": p["pt"], "have": levels.get(_key(p["en"]))} for p in b["passives"]],
        "stigmas": compare_stigmas(b, levels, learned),
        "arcana": compare_arcana(b, gear),
        "gear_slots": group_slots(b["gear"]), "gear_notes": b["gear_notes"],
        "wings": b["wings"], "titles": b["titles"], "wings_notes": b["wings_notes"],
        "rotation": b["rotation"], "skill_notes": b["skill_notes"],
    }
    sk = [s for s in r["skills"] if s["status"] != "sem_dado"]
    r["summary"] = {
        "skills_ok": sum(s["status"] in ("max", "acima") for s in sk), "skills_total": len(r["skills"]),
        "stigmas_ok": sum(s["status"] == "ok" for s in r["stigmas"]["main"]),
        "stigmas_total": len(r["stigmas"]["main"]),
        "arcana_ok": sum(a["status"] == "ok" for a in r["arcana"]),
        "arcana_total": len(r["arcana"]),
        "arcana_known": any(a["status"] != "sem_dado" for a in r["arcana"]),
    }
    return r
