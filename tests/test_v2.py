"""Partes novas da 2.0: energia, chaves, temas, sons e eventos de toda hora."""
from datetime import datetime, timedelta, timezone

import pytest

from daeva import progress, sound, theme
from daeva.schedule import EVENT_BY_ID, next_occurrence
from daeva.store import Store

UTC = timezone.utc
TZ = "America/Sao_Paulo"


def t(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def test_energia_sobe_5_por_hora_ate_o_limite():
    e = progress.energy_entry(320, t("2026-10-20T12:00:00"))
    assert progress.energy_now(e, t("2026-10-20T14:30:00"), False) == 330
    assert progress.energy_now(e, t("2026-10-25T00:00:00"), False) == 560
    assert progress.energy_now(e, t("2026-10-25T00:00:00"), True) == 840
    full = progress.energy_full_at(e, t("2026-10-20T12:00:00"), False)
    assert full == t("2026-10-20T12:00:00") + timedelta(hours=48)


def test_energia_cheia_nao_tem_previsao():
    e = progress.energy_entry(560, t("2026-10-20T12:00:00"))
    assert progress.energy_full_at(e, t("2026-10-20T13:00:00"), False) is None


def test_resets_diarios_as_4h_de_brasilia():
    # 04:00 em Brasília = 07:00 UTC
    assert progress.resets_between(t("2026-10-20T06:59:00"), t("2026-10-20T07:00:00"), TZ) == 1
    assert progress.resets_between(t("2026-10-20T07:00:00"), t("2026-10-20T20:00:00"), TZ) == 0
    assert progress.resets_between(t("2026-10-20T08:00:00"), t("2026-10-23T08:00:00"), TZ) == 3


def test_chaves_entram_no_reset_e_respeitam_o_limite():
    inv = progress.keys_entry(5, t("2026-10-20T08:00:00"))
    assert progress.keys_now(inv, "invasion", t("2026-10-21T08:00:00"), TZ, False) == 6
    assert progress.keys_now(inv, "invasion", t("2026-10-30T08:00:00"), TZ, False) == 7
    shugo = progress.keys_entry(10, t("2026-10-20T08:00:00"))
    assert progress.keys_now(shugo, "shugo", t("2026-10-21T08:00:00"), TZ, False) == 12
    assert progress.keys_now(shugo, "shugo", t("2026-10-22T08:00:00"), TZ, True) == 16


def test_shugo_toda_hora_e_invasao_na_meia_hora():
    now = t("2026-10-20T20:10:00")
    assert next_occurrence(EVENT_BY_ID["shugo"], now, TZ).start == t("2026-10-20T21:00:00")
    assert next_occurrence(EVENT_BY_ID["invasion"], now, TZ).start == t("2026-10-20T20:30:00")
    weekly = next_occurrence(EVENT_BY_ID["reset_weekly"], now, TZ).start
    assert weekly == t("2026-10-21T07:00:00")  # quarta 04:00 em Brasília


@pytest.mark.parametrize("tid", list(theme.THEMES))
def test_todos_os_temas_geram_estilo(tid):
    for size in theme.SIZES:
        for accent in theme.ACCENTS:
            qss = theme.build_qss(tid, size, compact=True, accent=accent)
            assert "QLabel#bigcount" in qss and "{" in qss
    theme.build_qss(tid)
    assert theme.FG == theme.THEMES[tid]["c"]["ink"]


def test_fontes_embutidas_existem():
    names = {f.name for f in theme.font_files()}
    assert {"Oxanium-Bold.ttf", "Barlow-Regular.ttf", "IMFeENrm28P.ttf", "VT323-Regular.ttf"} <= names


def test_som_personalizado_cai_no_padrao_se_sumir(tmp_path):
    mp3 = tmp_path / "gartua.mp3"
    mp3.write_bytes(b"ID3")
    s = {"sounds": {"big": str(mp3), "hourly": str(tmp_path / "sumiu.mp3"), "reset": str(tmp_path / "x.ogg")}}
    assert sound.sound_path("big", s) == mp3
    assert sound.sound_path("hourly", s).name == "alerta.wav"
    assert sound.sound_path("reset", s).name == "alerta.wav"


def test_ajustes_novos_tem_padrao(tmp_path):
    st = Store(tmp_path / "dados.json")
    s = st.settings
    assert s["theme"] == "ely" and s["dnd"] is True and s["alert_minutes_hourly"] == 2
    assert s["alerts"]["shugo"] is True and s["alerts"]["invasion"] is False
    assert set(s["sounds"]) == {"big", "hourly", "reset"}
