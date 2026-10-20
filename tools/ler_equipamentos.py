"""Lê a parte "Equipamentos" de uma página de classe do Atreia Lens copiada (Ctrl+A, Ctrl+C) para texto.

Uso: python tools/ler_equipamentos.py tools/bis_fontes/paginas/cleric.txt cleric
Grava tools/bis_fontes/<classe>.gear.json com os substatus de cada peça, em ordem.
"""
import json
import re
import sys
from pathlib import Path

SLOTS = ["Arma", "Guarda", "Elmo", "Ombreiras", "Peitoral", "Calças", "Luvas", "Botas", "Capa", "Colar",
         "Brinco (esq.)", "Brinco (dir.)", "Anel (esq.)", "Anel (dir.)", "Bracelete (esq.)", "Bracelete (dir.)"]
VALUE = re.compile(r"^[+-]?\d[\d.,]*%?$")


def parse(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    start = lines.index("Prioridade dos substats")
    end = lines.index("Total do equipamento", start)
    body = lines[start:end]
    notes = []
    if "Notas de equipamentos" in lines:
        i = lines.index("Notas de equipamentos") + 1
        while i < len(lines) and lines[i] not in ("Asas & Títulos",):
            notes.append(lines[i])
            i += 1
    slots, i = [], 0
    while i < len(body):
        if body[i] not in SLOTS:
            i += 1
            continue
        slot = {"slot": body[i], "substats": [], "also": [], "stone": None, "stone_lines": [], "divine": None}
        i += 1
        while i < len(body) and body[i] != "Substats":
            i += 1
        i += 1
        while i + 2 < len(body) and body[i].isdigit() and not VALUE.match(body[i + 1]) and VALUE.match(body[i + 2]):
            slot["substats"].append({"name": body[i + 1], "ref": body[i + 2]})
            i += 3
        if i < len(body) and body[i] == "Também servem":
            i += 1
            while i < len(body) and body[i] != "Pedra de Mana":
                slot["also"].append(body[i])
                i += 1
        if i < len(body) and body[i] == "Pedra de Mana":
            slot["stone"] = body[i + 1]
            i += 2
            while i + 1 < len(body) and body[i] not in SLOTS and body[i] != "Pedras Divinas" and VALUE.match(body[i + 1]):
                slot["stone_lines"].append({"name": body[i], "ref": body[i + 1]})
                i += 2
        if i < len(body) and body[i] == "Pedras Divinas":
            slot["divine"] = body[i + 1]
            i += 2
        slots.append(slot)
    missing = [s for s in SLOTS if s not in {x["slot"] for x in slots}]
    if len(slots) < 10:
        raise SystemExit(f"Achei só {len(slots)} peças; a parte Equipamentos foi copiada inteira?")
    if missing:
        print("Aviso: a página não traz", ", ".join(missing))
    for s in slots:
        if len(s["substats"]) != 5:
            raise SystemExit(f"{s['slot']}: achei {len(s['substats'])} substatus em vez de 5")
    return {"slots": slots, "notes": notes}


if __name__ == "__main__":
    src, cid = Path(sys.argv[1]), sys.argv[2]
    out = Path(__file__).parent / "bis_fontes" / f"{cid}.gear.json"
    data = parse(src.read_text(encoding="utf-8"))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(data["slots"]), "peças")
