import json
from pathlib import Path

import pytest

from daeva import bis

DATA = bis.load()
PROFILES = json.loads((Path(__file__).parent / "data" / "perfis_bis.json").read_text(encoding="utf-8"))["profiles"]


def run(name):
    p = PROFILES[name]
    return bis.compare(p["cls"], p["level"], p["skills"], p["gear"], DATA)


def test_todas_as_classes_tem_build_completa():
    assert set(DATA["classes"]) == {"gladiator", "templar", "assassin", "ranger", "sorcerer",
                                    "spirit-master", "cleric", "chanter"}
    for cid, c in DATA["classes"].items():
        assert len(c["stigmas"]) == 4, cid
        assert c["gear_stats"]["substats"] and c["gear_stats"]["manastones"], cid
        assert all(s["pt"] for s in c["skills"]), cid
        for s in c["skills"]:
            assert s["skip"] or s["min"] is not None, (cid, s["name"])


@pytest.mark.parametrize("raw,cid", [("Gladiator", "gladiator"), ("Spiritmaster", "spirit-master"),
                                     ("Spirit Master", "spirit-master"), ("Clérigo", "cleric"), ("Caçador", "ranger")])
def test_classe_reconhecida(raw, cid):
    assert bis.class_id(raw) == cid


def test_faixas_de_nivel():
    sm = {s["name"]: s for s in DATA["classes"]["spirit-master"]["skills"]}
    assert (sm["Summon: Fire Spirit"]["min"], sm["Summon: Fire Spirit"]["max"]) == (16, 20)
    assert (sm["Cold Shock"]["min"], sm["Cold Shock"]["max"]) == (16, None)


def test_kumaglad():
    r = run("Kumaglad")
    st = {s["name"]: s for s in r["stigmas"]["main"]}
    assert st["Lunge Stance"]["status"] == "ok"
    assert st["Rage Burst"]["gap"] == 12
    sk = {s["name"]: s for s in r["skills"]}
    assert sk["Overhead Slam"]["status"] == "falta" and sk["Overhead Slam"]["gap"] == 2
    assert sk["Keen Strike"]["status"] == "acima"
    assert sk["Sword Aura Rampage"]["status"] == "fora"
    arc = {a["arcana"]: a["status"] for a in r["arcana"]}
    assert arc == {"Cálice": "ok", "Papiro": "ok", "Bússola": "ok", "Sino": "tipo_errado", "Espelho": "tipo_errado"}
    assert r["gear_stats"]["substats"][0] == ["Bônus de Golpe Potente"]
    assert r["gear_stats"]["substats"][-1] == ["Precisão Adicional", "Acerto Crítico"]
    assert "todo" not in r


def test_prioridade_de_status_por_classe():
    assert run("Fuwawa")["gear_stats"]["manastones"][0] == ["Amplificação de Dano de Ataque Frontal"]
    assert run("Mori")["gear_stats"]["manastones"][0] == ["Amplificação de Dano de Arma", "Amplificação de Dano Crítico"]
    assert DATA["classes"]["assassin"]["gear_stats"]["substats"][0] == ["Precisão"]


def test_stigmas_do_mori():
    r = run("Mori")
    assert not r["endgame"]
    assert {s["status"] for s in r["stigmas"]["main"]} == {"nao_aprendido", "falta"}


def test_sem_arcana_no_perfil():
    r = run("Fuwawa")
    assert not r["summary"]["arcana_known"]


def test_substatus_por_peca_do_clerigo():
    r = run("Mori")
    nomes = [s["name"] for s in r["gear_slots"]]
    assert nomes[:3] == ["Arma", "Guarda", "Elmo"]
    assert "Brincos" in nomes and "Anéis" in nomes and "Braceletes" in nomes and len(nomes) == 13
    peito = next(s for s in r["gear_slots"] if s["name"] == "Peitoral")
    assert [x["name"] for x in peito["substats"]] == ["Amplificação de Dano", "Mercê do Empíreo", "Mercê da Terra",
                                                       "Acerto Crítico", "Precisão"]
    assert peito["substats"][0]["ref"] == "+6,58%"
    assert next(s for s in r["gear_slots"] if s["name"] == "Arma")["divine"] == "Soberba de Zikel"


def test_classe_sem_lista_por_peca_ainda():
    assert run("Kumaglad")["gear_slots"] == []
