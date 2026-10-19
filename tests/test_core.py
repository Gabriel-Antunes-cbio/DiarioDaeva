from datetime import datetime, timedelta, timezone

import pytest

from daeva.profiles import ProfileError, parse_aion2index, parse_link, parse_shugo
from daeva.schedule import EVENT_BY_ID, FIELD_BY_ID, AlertTracker, field_respawn, next_occurrence
from daeva.store import Store

UTC = timezone.utc
SP = "America/Sao_Paulo"


def utc(*a):
    return datetime(*a, tzinfo=UTC)


# ------------------------------------------------------------------ agenda
def test_siege_monday_night_brasilia():
    now = utc(2026, 10, 19, 18, 24)  # seg 15:24 em Brasília
    occ = next_occurrence(EVENT_BY_ID["execs"], now, SP)
    assert occ.start == utc(2026, 10, 20, 0, 30)  # seg 21:30 BRT


def test_nahma_next_friday():
    occ = next_occurrence(EVENT_BY_ID["nahma"], utc(2026, 10, 19, 18, 24), SP)
    assert occ.start == utc(2026, 10, 24, 0, 0)  # sex 21:00 BRT


def test_kaira_every_three_hours():
    occ = next_occurrence(EVENT_BY_ID["kaira"], utc(2026, 10, 19, 18, 24), SP)
    assert occ.start == utc(2026, 10, 19, 19, 0)  # 16:00 BRT


def test_event_live_window():
    occ = next_occurrence(EVENT_BY_ID["nahma"], utc(2026, 10, 24, 0, 10), SP)
    assert occ.live(utc(2026, 10, 24, 0, 10))


def test_other_region_dst():
    occ = next_occurrence(EVENT_BY_ID["execs"], utc(2026, 10, 19, 12, 0), "Europe/Berlin")
    assert occ.start == utc(2026, 10, 19, 19, 30)  # 21:30 CEST


def test_gartua_respawn_and_alert_once():
    kill = utc(2026, 10, 19, 10, 0)
    due = field_respawn(FIELD_BY_ID["gartua"], kill)
    assert due == utc(2026, 10, 19, 22, 0)
    tr = AlertTracker()
    assert not tr.due("g", due, due - timedelta(minutes=6), 5)
    assert tr.due("g", due, due - timedelta(minutes=5), 5)
    assert not tr.due("g", due, due - timedelta(minutes=4), 5)


# ------------------------------------------------------------------ links
def test_parse_links():
    a = parse_link("https://shugo.gg/character/global/la-siel/Kumaglad")
    assert (a.source, a.region, a.server, a.name) == ("shugo", "la", "Siel", "Kumaglad")
    b = parse_link("aion2index.com/c/la/siel/Kumaglad")
    assert (b.source, b.region, b.server, b.gear_label) == ("aion2index", "la", "Siel", "Item level")
    with pytest.raises(ProfileError):
        parse_link("https://shugo.gg/character/kr/quai/x")
    with pytest.raises(ProfileError):
        parse_link("https://google.com")


# ------------------------------------------------------------------ páginas
SHUGO = """<html><head>
<meta property="og:title" content="Kumaglad - AION 2 Gladiator Lv 45, Siel | Shugo.GG">
<meta name="description" content="Kumaglad: AION 2 Level 45 Elyos Gladiator (1,723 GS) of the legion bibas on Siel (Global).">
</head><body><h1>Kumaglad</h1>
<p><span>Level 45</span> · <span>Gladiator</span> · <span>Elyos</span> · Legion: bibas ·
<span>Gear score</span> <b>1,723</b> · Title: Failed Entrepreneur · <span>Combat power</span> <b>106,302</b></p>
<ul><li>Level 45 · Templar · 130,317 Combat Power</li></ul></body></html>"""

A2I = """<html><body><img src="/img/class_icon_gladiator.png"><b>Gladiator</b>Level <b>45</b>
<div>Combat power<span>106,302</span><small>#110 Gladiator · #790 on Siel</small></div>
<div>Item level<span>2,237</span><small>#3,644 in Latin America</small></div></body></html>"""


def test_parse_shugo_page():
    p = parse_shugo(SHUGO)
    assert (p.cp, p.gear, p.cls, p.level) == (106302, 1723, "Gladiador", 45)


def test_parse_aion2index_page():
    p = parse_aion2index(A2I)
    assert (p.cp, p.gear, p.cls, p.level) == (106302, 2237, "Gladiador", 45)


def test_parse_missing_values():
    with pytest.raises(ProfileError):
        parse_shugo("<html><body>Not found</body></html>")


# ------------------------------------------------------------------ dados
def test_store_history(tmp_path):
    s = Store(tmp_path / "d.json")
    c = s.add_character(parse_link("https://shugo.gg/character/global/la-siel/Kumaglad"))
    t = utc(2026, 10, 19, 19)
    assert s.record_profile(c["id"], parse_shugo(SHUGO), t)
    assert not s.record_profile(c["id"], parse_shugo(SHUGO), t + timedelta(hours=6))
    s2 = Store(tmp_path / "d.json")
    assert len(s2.characters[0]["history"]) == 1
    assert s2.settings["alerts"]["gartua"] is True
    assert s2.settings["alerts"]["rift"] is False
