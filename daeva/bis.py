"""Aba BiS: compara o personagem com a build da classe.

A build (skills, stigmas, arcanas, prioridades) vem do Atreia Lens.
O equipamento de referência são os itens mais usados pelos 360 personagens nível 45 de maior CP
da América Latina, segundo o GameWith. Os dois ficam em daeva/data/bis.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "bis.json"

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

# Slot do Shugo.GG -> slot do GameWith
SLOT_MAP = {
    "main hand": "Main hand", "off-hand": "Off hand", "off hand": "Off hand", "torso": "Chest", "chest": "Chest",
    "legs": "Greaves", "helmet": "Helm", "helm": "Helm", "shoulders": "Pauldrons", "gloves": "Gloves",
    "boots": "Boots", "cape": "Cloak", "cloak": "Cloak", "belt": "Belt", "necklace": "Necklace",
    "earring": "Earrings", "ring": "Rings", "bracelet": "Bracelets", "rune1": "Runes", "rune2": "Runes",
    "rune": "Runes", "amulet": "Amulet",
}
SLOT_PT = {
    "Main hand": "Arma", "Off hand": "Escudo", "Helm": "Elmo", "Pauldrons": "Ombreiras", "Chest": "Peitoral",
    "Gloves": "Luvas", "Greaves": "Perneiras", "Boots": "Botas", "Cloak": "Capa", "Belt": "Cinto",
    "Necklace": "Colar", "Earrings": "Brinco", "Rings": "Anel", "Bracelets": "Bracelete", "Amulet": "Amuleto",
    "Runes": "Runa",
}
GRADE_RANK = {"common": 0, "rare": 1, "epic": 2, "unique": 3, "legendary": 4, "mythic": 5}
END_LEVEL = 45


def load(path: Path = DATA_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(s: str) -> str:
    s = s.lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))
    return re.sub(r"[^a-z0-9]", "", s)


def class_id(cls: str) -> str | None:
    return CLASS_ALIASES.get(_key(cls))


def _enh(v) -> int:
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else 0


def _levels(skills: dict | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for group in ("active", "passive", "stigma"):
        for name, lvl in (skills or {}).get(group, []):
            out[_key(name)] = int(lvl)
    return out


def compare_skills(build: dict, levels: dict[str, int], stats: dict[str, dict]) -> list[dict]:
    rows = []
    for s in build["skills"]:
        have = levels.get(_key(s["name"]))
        st = stats.get(_key(s["name"]), {})
        row = {"name": s["name"], "pt": s["pt"], "have": have, "target": s["level"], "min": s["min"],
               "max": s["max"], "specs": s["specs"], "points": s["points"], "avg": st.get("avg")}
        if s["skip"]:
            row["status"] = "fora" if have else "fora_ok"
            row["gap"] = 0
        elif have is None:
            row["status"], row["gap"] = "sem_dado", 0
        elif have > (s["max"] or s["min"]):
            row["status"], row["gap"] = "acima", 0
        elif have >= (s["max"] or s["min"]):
            row["status"], row["gap"] = "max", 0
        elif have >= s["min"]:
            row["status"], row["gap"] = "ok", 0
        else:
            row["status"], row["gap"] = "falta", s["min"] - have
        rows.append(row)
    return rows


def compare_stigmas(build: dict, levels: dict[str, int], learned: set[str]) -> dict:
    main = []
    for s in build["stigmas"]:
        k = _key(s["name"])
        have = levels.get(k)
        known = k in learned
        if not known:
            status, gap = "nao_aprendido", s["rank"]
        elif have >= s["rank"]:
            status, gap = "ok", 0
        else:
            status, gap = "falta", s["rank"] - have
        main.append({"name": s["name"], "pt": s["pt"], "have": have if known else None, "target": s["rank"],
                     "status": status, "gap": gap})
    alt = [{"name": s["name"], "pt": s["pt"], "have": levels.get(_key(s["name"])) if _key(s["name"]) in learned else None}
           for s in build["stigmas_alt"]]
    return {"main": main, "alt": alt}


def compare_gear(build: dict, gear: list[dict] | None) -> list[dict]:
    ref = {g["slot"]: g for g in build["gear"]}
    rows, seen = [], set()
    for piece in gear or []:
        slot = SLOT_MAP.get(piece["slot"].strip().lower())
        if not slot or slot not in ref:
            continue
        top = ref[slot]
        seen.add(slot)
        mine_g = GRADE_RANK.get(piece.get("grade", "").lower(), -1)
        top_g = GRADE_RANK.get(top["grade"].lower(), -1)
        enh, top_enh = int(piece.get("enchant", 0)), _enh(top["typical_enhance"])
        if _key(piece["item"]) == _key(top["item"]):
            status = "igual" if enh >= top_enh else "refinar"
        elif mine_g > top_g >= 0:
            status = "grau_acima"
        elif 0 <= mine_g < top_g:
            status = "grau_abaixo"
        else:
            status = "outro"
        rows.append({"slot": slot, "slot_pt": SLOT_PT[slot], "item": piece["item"], "enchant": enh,
                     "grade": piece.get("grade", ""), "top_item": top["item"], "top_enchant": top_enh,
                     "top_grade": top["grade"], "share": top["share_pct"], "status": status,
                     "refine_gap": max(0, top_enh - enh) if status in ("igual", "refinar") else 0})
    for slot, top in ref.items():
        if slot not in seen:
            rows.append({"slot": slot, "slot_pt": SLOT_PT[slot], "item": None, "enchant": 0, "grade": "",
                         "top_item": top["item"], "top_enchant": _enh(top["typical_enhance"]),
                         "top_grade": top["grade"], "share": top["share_pct"], "status": "vazio", "refine_gap": 0})
    order = list(SLOT_PT)
    rows.sort(key=lambda r: order.index(r["slot"]))
    return rows


ARCANA_PT = {"chalice": "Cálice", "parchment": "Papiro", "scroll": "Papiro", "compass": "Bússola",
             "bell": "Sino", "mirror": "Espelho"}
ARCANA_KIND_PT = {"vigor": "Vigor", "magic": "Magia"}


def compare_arcana(build: dict, gear: list[dict] | None) -> list[dict]:
    """Arcanas aparecem no Shugo.GG como linhas Arcana1..5 ('Chalice of Vigor +1')."""
    mine = {}
    for piece in gear or []:
        if not piece["slot"].strip().lower().startswith("arcana"):
            continue
        m = re.match(r"(\w+) of (\w+)", piece["item"].strip(), re.I)
        if m:
            pt = ARCANA_PT.get(m.group(1).lower())
            if pt:
                mine[pt] = {"kind": ARCANA_KIND_PT.get(m.group(2).lower(), m.group(2)), "item": piece["item"],
                            "enchant": int(piece.get("enchant", 0)), "grade": piece.get("grade", "")}
    rows = []
    for a in build["arcana"]:
        want = "Magia" if _key(a["type"]) in ("magia", "magica", "magic") else a["type"]
        have = mine.get(a["arcana"])
        status = "sem_dado" if not mine else ("vazio" if not have else ("ok" if have["kind"] == want else "tipo_errado"))
        rows.append({"arcana": a["arcana"], "want": want, "gods": a["gods"], "have": have, "status": status})
    return rows


def priorities(result: dict, limit: int = 3) -> list[dict]:
    """As poucas coisas que mais aproximam o personagem da build, em ordem."""
    cand = []
    for s in result["stigmas"]["main"]:
        if s["status"] == "nao_aprendido":
            cand.append((30, "Aprender o stigma " + s["pt"], f"Faz parte dos 4 principais da build (rank {s['target']})."))
        elif s["status"] == "falta":
            cand.append((s["gap"] * 1.2, f"Subir o stigma {s['pt']} de {s['have']} para {s['target']}",
                         "É um dos 4 stigmas principais da build."))
    for s in result["skills"]:
        if s["status"] == "falta":
            weight = (s["points"] or 6) / 10
            cand.append((s["gap"] * weight, f"Subir {s['pt']} de {s['have']} para {s['target']}",
                         f"Prioridade {s['points'] or '-'} na build."))
    for a in result["arcana"]:
        if a["status"] == "tipo_errado":
            cand.append((7, f"Trocar a arcana {a['arcana']} de {a['have']['kind']} para {a['want']}",
                         f"A build usa {a['arcana']} de {a['want']} ({a['gods']})."))
        elif a["status"] == "vazio":
            cand.append((9, f"Equipar a arcana {a['arcana']} de {a['want']}", f"Deuses da build: {a['gods']}."))
    if result["endgame"]:
        for g in result["gear"]:
            if g["status"] == "grau_abaixo":
                cand.append((8, f"Trocar {g['slot_pt'].lower()}: {g['item']} ({g['grade']})",
                             f"Os top usam {g['top_item']} ({g['top_grade']}), {g['share']}%."))
            elif g["status"] == "vazio":
                cand.append((10, f"Equipar {g['slot_pt'].lower()}", f"Os top usam {g['top_item']}."))
            elif g["refine_gap"]:
                cand.append((g["refine_gap"] * 0.8, f"Refinar {g['item']} de +{g['enchant']} para +{g['top_enchant']}",
                             f"Refino comum entre os top ({g['share']}% usam esse item)."))
    cand.sort(key=lambda c: -c[0])
    return [{"title": t, "why": w} for _, t, w in cand[:limit]]


def compare(cls: str, level: int | None, skills: dict | None, gear: list[dict] | None, data: dict | None = None) -> dict:
    data = data or load()
    cid = class_id(cls)
    if not cid:
        raise ValueError(f"Classe desconhecida: {cls!r}")
    build = data["classes"][cid]
    levels = _levels(skills)
    learned = {_key(n) for n, _ in (skills or {}).get("stigma", [])}
    stats = {_key(s["name"]): s for s in build["skill_stats"]}
    result = {
        "class": cid, "gw_slug": build["gw_slug"], "build": build["build"], "level": level,
        "endgame": (level or 0) >= END_LEVEL,
        "skills": compare_skills(build, levels, stats),
        "passives": [{"name": p["name"], "pt": p["pt"], "have": levels.get(_key(p["name"]))} for p in build["passives"]],
        "stigmas": compare_stigmas(build, levels, learned),
        "gear": compare_gear(build, gear),
        "arcana": compare_arcana(build, gear), "arcana_note": build["arcana_note"],
        "arcana_stats": build["arcana_stats"][:4],
        "enhancing": build["enhancing"], "manastones": build["manastones"],
        "titles": build["titles"], "wings": build["wings"],
    }
    result["todo"] = priorities(result)
    sk = [s for s in result["skills"] if not s["status"].startswith("fora") and s["status"] != "sem_dado"]
    result["summary"] = {
        "skills_ok": sum(s["status"] in ("ok", "max", "acima") for s in sk), "skills_total": len(sk),
        "stigmas_ok": sum(s["status"] == "ok" for s in result["stigmas"]["main"]),
        "stigmas_total": len(result["stigmas"]["main"]),
        "gear_match": sum(g["status"] in ("igual", "refinar") for g in result["gear"]),
        "gear_up": sum(g["status"] == "grau_acima" for g in result["gear"]),
        "gear_total": len(result["gear"]),
        "arcana_ok": sum(a["status"] == "ok" for a in result["arcana"]),
        "arcana_total": len(result["arcana"]),
        "arcana_known": any(a["status"] != "sem_dado" for a in result["arcana"]),
    }
    return result
