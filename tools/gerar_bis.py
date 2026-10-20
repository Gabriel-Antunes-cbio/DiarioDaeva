"""Gera daeva/data/bis.json a partir das páginas de classe do Atreia Lens copiadas em tools/bis_fontes/paginas/.

Tudo da build vem dessas páginas. Os arquivos <classe>.en.json/.pt.json (também do Atreia Lens, versão em
inglês e em português) servem só de dicionário: o AION2 Index mostra as skills do personagem em inglês.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "bis_fontes"
OUT = ROOT / "daeva" / "data" / "bis.json"
sys.path.insert(0, str(ROOT / "tools"))
from ler_atreia import parse  # noqa: E402

CLASSES = ["gladiator", "templar", "assassin", "ranger", "sorcerer", "spirit-master", "cleric", "chanter"]
# A página do Assassino escreve a ordem das passivas em texto corrido (S / A / B), sem a linha "Prioridade de passivas".
ASSASSIN_PASSIVES = ["Golpe Potente pela Retaguarda", "Postura de Ataque Súbito", "Exploração de Fraqueza",
                     "Acerto de Impacto", "Sexto Sentido Aguçado"]


def dictionary(c: str) -> dict:
    """PT -> EN, pareando as listas da versão em inglês e em português da mesma página."""
    en = json.loads((SRC / f"{c}.en.json").read_text(encoding="utf-8"))
    pt = json.loads((SRC / f"{c}.pt.json").read_text(encoding="utf-8"))
    out = {}
    for key, field in (("skill_final", "name"), ("skill_priority", "name"), ("stigmas_main", "name"),
                       ("stigmas_alt", None), ("passive_priority", None)):
        for a, b in zip(en.get(key) or [], pt.get(key) or []):
            out[b if field is None else b[field]] = a if field is None else a[field]
    return out


def passives(build: dict, c: str) -> list[str]:
    if c == "assassin":
        return ASSASSIN_PASSIVES
    for line in build["skill_notes"]:
        if line.startswith("Prioridade de passivas:"):
            return [re.sub(r"^\d+\s+", "", x.strip()) for x in line.split(":", 1)[1].split("·")]
    return []


def stigma_alts(build: dict) -> list[str]:
    for line in build["skill_notes"]:
        m = re.search(r"Também bom: (.+?)\.?$", line)
        if m:
            return [x.strip() for x in m.group(1).split(",")]
    return []


out = {"source": {"name": "Atreia Lens", "url": "https://atreialens.hartmannlab.xyz/{slug}",
                  "note": "Builds da comunidade. Página de cada classe copiada em 20/10/2026."},
       "collected": "2026-10-20", "classes": {}}
missing = []
for c in CLASSES:
    b = parse((SRC / "paginas" / f"{c}.txt").read_text(encoding="utf-8"))
    tr = dictionary(c)

    def en(name, kind):
        if name not in tr:
            missing.append((c, kind, name))
        return tr.get(name)

    for s in b["skills"]:
        s["en"] = en(s["pt"], "skill")
    for s in b["stigmas"]:
        s["en"] = en(s["pt"], "stigma")
    b["stigmas_alt"] = [{"pt": x, "en": tr.get(x)} for x in stigma_alts(b)]
    b["passives"] = [{"pt": x, "en": en(x, "passiva")} for x in passives(b, c)]
    b["slug"] = c
    out["classes"][c] = b

if missing:
    print("Sem tradução para o inglês:", missing)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", {c: (len(v["skills"]), len(v["stigmas"]), len(v["arcanas"]), len(v["gear"])) for c, v in out["classes"].items()})
