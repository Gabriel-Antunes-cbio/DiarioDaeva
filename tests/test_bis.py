import json
import sys
from pathlib import Path

import pytest

from daeva import bis

ROOT = Path(__file__).resolve().parent.parent
DATA = bis.load()
PROFILES = json.loads((Path(__file__).parent / "data" / "perfis_bis.json").read_text(encoding="utf-8"))["profiles"]


def run(name):
    p = PROFILES[name]
    return bis.compare(p["cls"], p["level"], p["skills"], p["gear"], DATA)


def test_dados_vem_so_do_atreia_lens():
    assert DATA["source"]["name"] == "Atreia Lens"
    assert "gamewith" not in json.dumps(DATA, ensure_ascii=False).lower()


def test_todas_as_classes_completas():
    assert set(DATA["classes"]) == {"gladiator", "templar", "assassin", "ranger", "sorcerer",
                                    "spirit-master", "cleric", "chanter"}
    for cid, c in DATA["classes"].items():
        assert len(c["stigmas"]) == 4, cid
        assert len(c["skills"]) >= 9, cid
        assert all(s["en"] for s in c["skills"] + c["stigmas"]), cid
        assert all(s["final"] == s["base"] + s["daevanion"] + s["arcanas"] + s["joias"] for s in c["skills"]), cid
        assert len(c["gear"]) == (14 if cid == "assassin" else 16), cid
        assert all(len(s["substats"]) == 5 for s in c["gear"]), cid
        assert len(c["arcanas"]) == (3 if cid == "assassin" else 5), cid
        assert c["wings"] and c["titles"], cid


def test_leitor_da_pagina_do_clerigo():
    sys.path.insert(0, str(ROOT / "tools"))
    from ler_atreia import parse
    b = parse((ROOT / "tools/bis_fontes/paginas/cleric.txt").read_text(encoding="utf-8"))
    assert b["build"] == "Build de Cleric" and b["weapon"] == "Maça"
    rel = next(s for s in b["skills"] if s["pt"] == "Relâmpago do Julgamento")
    assert (rel["final"], rel["base"], rel["daevanion"], rel["arcanas"], rel["joias"]) == (17, 10, 4, 3, 0)
    peito = next(s for s in b["gear"] if s["slot"] == "Peitoral")
    assert [x["name"] for x in peito["substats"]] == ["Amplificação de Dano", "Mercê do Empíreo", "Mercê da Terra",
                                                       "Acerto Crítico", "Precisão"]
    assert peito["substats"][0]["ref"] == "+6,58%"
    assert b["arcanas"][0]["name"] == "Cálice do Vigor +5" and b["arcanas"][0]["god"] == "Tempo [Siel] +25"


@pytest.mark.parametrize("raw,cid", [("Gladiator", "gladiator"), ("Spiritmaster", "spirit-master"),
                                     ("Spirit Master", "spirit-master"), ("Clérigo", "cleric"), ("Caçador", "ranger")])
def test_classe_reconhecida(raw, cid):
    assert bis.class_id(raw) == cid


def test_kumaglad():
    r = run("Kumaglad")
    st = {s["pt"]: s for s in r["stigmas"]["main"]}
    assert st["Postura de Assalto"]["status"] == "ok"
    assert st["Explosão de Ira"]["gap"] == 12
    sk = {s["pt"]: s for s in r["skills"]}
    assert sk["Esmagada Descendente"]["status"] == "falta" and sk["Esmagada Descendente"]["gap"] == 2
    assert sk["Golpe Afiado"]["status"] == "acima"
    arc = {a["base"]: a["status"] for a in r["arcana"]}
    assert arc == {"Cálice": "refinar", "Manuscrito": "refinar", "Bússola": "refinar",
                   "Sino": "tipo_errado", "Espelho": "tipo_errado"}
    nomes = [s["name"] for s in r["gear_slots"]]
    assert "Brincos" in nomes and "Anéis" in nomes and len(nomes) == 13


def test_mori_abaixo_do_45():
    r = run("Mori")
    assert not r["endgame"]
    assert {s["status"] for s in r["stigmas"]["main"]} == {"nao_aprendido", "falta"}


def test_sem_arcana_no_perfil():
    assert not run("Fuwawa")["summary"]["arcana_known"]
