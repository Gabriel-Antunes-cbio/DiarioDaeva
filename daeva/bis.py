"""Aba BiS: compara o personagem com a build da classe.

A build (skills, stigmas, arcanas e a prioridade de status dos itens) vem do Atreia Lens, por classe.
O nível médio das skills entre os top da América Latina vem do GameWith. Tudo fica em daeva/data/bis.json.
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

END_LEVEL = 45


def load(path: Path = DATA_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(s: str) -> str:
    s = s.lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))
    return re.sub(r"[^a-z0-9]", "", s)


def class_id(cls: str) -> str | None:
    return CLASS_ALIASES.get(_key(cls))


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


def group_slots(slots: list[dict] | None) -> list[dict]:
    """Junta as peças de esquerda e direita quando a recomendação é a mesma ("Brinco (esq.)" + "(dir.)" -> "Brincos")."""
    if not slots:
        return []
    plural = {"Brinco": "Brincos", "Anel": "Anéis", "Bracelete": "Braceletes"}
    out = []
    for s in slots:
        base = s["slot"].split(" (")[0]
        same = {k: s[k] for k in ("substats", "also", "stone", "divine")}
        prev = out[-1] if out else None
        if prev and prev["base"] == base and prev["same"] == same and base in plural:
            prev["name"] = plural[base]
            continue
        out.append({"base": base, "name": s["slot"], "same": same, **same})
    for o in out:
        del o["base"], o["same"]
    return out


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
        "gear_stats": build["gear_stats"],
        "gear_slots": group_slots(build.get("gear_slots", {}) and build["gear_slots"]["slots"]),
        "gear_notes": (build.get("gear_slots") or {}).get("notes", []),
        "arcana": compare_arcana(build, gear), "arcana_note": build["arcana_note"],
        "arcana_stats": build["arcana_stats"][:4],
        "enhancing": build["enhancing"], "manastones": build["manastones"],
        "titles": build["titles"], "wings": build["wings"],
    }
    sk = [s for s in result["skills"] if not s["status"].startswith("fora") and s["status"] != "sem_dado"]
    result["summary"] = {
        "skills_ok": sum(s["status"] in ("ok", "max", "acima") for s in sk), "skills_total": len(sk),
        "stigmas_ok": sum(s["status"] == "ok" for s in result["stigmas"]["main"]),
        "stigmas_total": len(result["stigmas"]["main"]),
        "arcana_ok": sum(a["status"] == "ok" for a in result["arcana"]),
        "arcana_total": len(result["arcana"]),
        "arcana_known": any(a["status"] != "sem_dado" for a in result["arcana"]),
    }
    return result
