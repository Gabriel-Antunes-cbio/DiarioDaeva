"""Junta as builds do Atreia Lens (EN + PT) e as estatísticas do GameWith num só arquivo."""
import json, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "tools" / "bis_fontes"; OUT = ROOT / "daeva" / "data" / "bis.json"
CLASSES = ["gladiator", "templar", "assassin", "ranger", "sorcerer", "spirit-master", "cleric", "chanter"]

# Níveis com faixa conferidos numa segunda leitura focada da página (a primeira leitura achatava "16-20" e "16+").
LEVEL_TEXT = {
    "ranger": {"Burst Arrow": "16+"},
    "chanter": {"Recuperation": "16-20"},
    "spirit-master": {"Cold Shock": "16+", "Summon: Fire Spirit": "16-20", "Summon: Water Spirit": "16-20",
                      "Jointstrike: Curse": "16-20", "Summon: Earth Spirit": "12-16"},
    "assassin": {"Insignia Explosion": "20 ou 16", "Savage Roar": "20 ou 12", "Shadow Fall": "12+",
                 "Whirlwind Slice": "12 ou 16", "Flash Slice": "8+", "Infiltrate": "8+", "Defiance": "12 ou 16"},
}
ARCANA_NOTE = {
    "assassin": "Ordem: Papiro → Bússola → Cálice. Papiro: Corte Rápido, Estocada no Coração, Explosão de Insígnia. "
                "Bússola: Rugido da Besta, Desenfreio da Tempestade, Remoção de Impacto. "
                "Cálice: passivas Golpe Potente pela Retaguarda, Postura de Ataque Súbito, Exploração de Fraqueza.",
}

# Prioridade de status dos itens (aprimoramento + manastones), conferida linha a linha na página de cada classe.
# Cada passo é uma lista: dois itens no mesmo passo valem quase o mesmo (≈ no site).
ENH = [["Bônus de Golpe Potente"], ["Amplificação de Dano de Arma"], ["Amplificação de Dano"], ["Ataque"],
       ["Precisão Adicional", "Acerto Crítico"]]
MANA_FRONT = [["Amplificação de Dano de Ataque Frontal"], ["Amplificação de Dano de Arma", "Amplificação de Dano Crítico"],
              ["Amplificação de Dano"], ["Ataque"]]
MANA = [["Amplificação de Dano de Arma", "Amplificação de Dano Crítico"], ["Amplificação de Dano"], ["Ataque"]]
FRONT_IF = "Ataque Frontal só se a sua build for frontal."
GEAR_STATS = {
    "gladiator": {"substats": ENH, "manastones": MANA_FRONT, "notes": [FRONT_IF]},
    "ranger": {"substats": ENH, "manastones": MANA_FRONT, "notes": [FRONT_IF]},
    "chanter": {"substats": ENH, "manastones": MANA_FRONT, "notes": [FRONT_IF]},
    "templar": {"substats": ENH, "manastones": MANA_FRONT, "notes": []},
    "cleric": {"substats": ENH, "manastones": MANA, "notes": []},
    "spirit-master": {"substats": ENH, "manastones": MANA, "notes": []},
    "sorcerer": {"substats": ENH, "manastones": MANA, "notes": []},
    "assassin": {
        "substats": [["Precisão"], ["Amplificação de Dano da Retaguarda"],
                     ["Ataque", "Amplificação de Dano de Arma", "Golpe Potente", "Acerto Crítico", "Ataque contra Chefe/PvE"]],
        "manastones": [["Amplificação de Dano da Retaguarda"], ["Amplificação de Dano de Arma"], ["Amplificação de Dano Crítico"],
                       ["Ataque 30+"], ["Amplificação de Dano"]],
        "notes": ["Ponto de partida: Acerto Crítico até cerca de 2.200, depois Precisão.",
                  "Precisão primeiro só se o chefe ainda mostra erros ou aparos.",
                  "Retaguarda só vale se você consegue ficar nas costas do chefe com consistência.",
                  "Slots de Acerto Crítico: Acerto Crítico até a meta, depois Precisão; reserva Ataque contra Chefe 18+.",
                  "Slots de Golpe Potente: Golpe Potente 2%+, depois Retaguarda 2,8%+.",
                  "Mais Golpe Potente: comece pela Vinculação da Alma do elmo e da capa."]},
}


def span(text):
    """'20' -> (20,20) · '16+' -> (16,None) · '16-20' -> (16,20) · '20 ou 16' -> (16,20)"""
    if text is None:
        return None, None
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if "+" in text:
        return nums[0], None
    return min(nums), max(nums)

def specs(v):
    if v is None: return None
    if isinstance(v, list): return "/".join(map(str, v)) or None
    return v

out = {"sources": {
          "build": {"name": "Atreia Lens", "url": "https://atreialens.hartmannlab.xyz/{slug}",
                    "note": "Builds da comunidade, PvE. Nível final das skills e stigmas recomendados."},
          "stats": {"name": "GameWith Build Stats", "url": "https://gamewith.ai/aion2/en/build-stats/la/{gw_slug}",
                    "note": "Nível médio das skills entre os 360 personagens nível 45 de maior CP da América Latina."}},
       "collected": {"build": "2026-10-20", "stats": "2026-10-07"},
       "classes": {}}
gw = json.load(open(RAW / "gamewith.json"))
for c in CLASSES:
    en = json.load(open(RAW / f"{c}.en.json")); pt = json.load(open(RAW / f"{c}.pt.json"))
    def pair(key, field="name"):
        a, b = en[key], pt[key]
        assert len(a) == len(b), (c, key, len(a), len(b))
        return [(x if isinstance(x, str) else x[field], y if isinstance(y, str) else y[field], x) for x, y in zip(a, b)]
    pts = {x["name"]: x["points"] for x in en["skill_priority"]}
    skills = []
    for name, name_pt, row in pair("skill_final"):
        txt = LEVEL_TEXT.get(c, {}).get(name)
        if txt is None and row["level"] is not None:
            txt = str(row["level"])
        lo, hi = span(txt)
        skills.append({"name": name, "pt": name_pt, "level": txt, "min": lo, "max": hi,
                       "specs": specs(row.get("specs")), "points": pts.get(name), "skip": txt is None})
    stig = [{"name": n, "pt": p, "rank": r["rank"]} for n, p, r in pair("stigmas_main")]
    alt = [{"name": n, "pt": p} for n, p, _ in pair("stigmas_alt")]
    arc = [{"arcana": p, "type": r_pt["type"], "gods": r_pt["gods"] if isinstance(r_pt["gods"], str) else " / ".join(r_pt["gods"])}
           for p, r_pt in zip([x["arcana"] for x in pt["arcana"]], pt["arcana"])]
    g = gw["classes"][c]
    out["classes"][c] = {
        "build": pt["build"], "slug": c, "gw_slug": gw["slugs"].get(c, c),
        "skills": skills,
        "passives": [{"name": n, "pt": p} for n, p, _ in pair("passive_priority")],
        "stigmas": stig, "stigmas_alt": alt,
        "arcana": arc, "arcana_note": ARCANA_NOTE.get(c),
        "enhancing": pt["enhancing_priority"], "manastones": pt["manastone_priority"],
        "titles": pt["titles"], "wings": pt["wings"],
        "gear_stats": GEAR_STATS[c], "skill_stats": g["skills"], "arcana_stats": g["arcana"],
    }
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", {c: (len(v["skills"]), len(v["stigmas"]), len(v["gear_stats"]["substats"])) for c, v in out["classes"].items()})
