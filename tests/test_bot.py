import json
import threading
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from bot.state import BoardError, KillBoard, parse_clock, parse_remaining
from daeva.store import Store

UTC = timezone.utc
SP = "America/Sao_Paulo"


def utc(*a):
    return datetime(*a, tzinfo=UTC)


def test_parse_clock_today_and_yesterday():
    now = utc(2026, 10, 19, 20, 0)  # 17:00 em Brasília
    assert parse_clock("14:32", SP, now) == utc(2026, 10, 19, 17, 32)
    assert parse_clock("14h32", SP, now) == utc(2026, 10, 19, 17, 32)
    assert parse_clock("23:10", SP, now) == utc(2026, 10, 19, 2, 10)  # ontem 23:10 BRT
    with pytest.raises(BoardError):
        parse_clock("25:00", SP, now)
    with pytest.raises(BoardError):
        parse_clock("amanhã", SP, now)


def test_board_set_respawn_and_alert_once(tmp_path):
    b = KillBoard(tmp_path / "m.json")
    now = utc(2026, 10, 19, 20, 0)
    b.set("gartua", now, "Kumaglad", "discord", now)
    assert b.respawn_at("gartua") == utc(2026, 10, 20, 8, 0)
    assert b.due_alerts(utc(2026, 10, 20, 7, 54), 5) == []
    assert b.due_alerts(utc(2026, 10, 20, 7, 56), 5) == ["gartua"]
    assert b.due_alerts(utc(2026, 10, 20, 7, 57), 5) == []
    again = KillBoard(tmp_path / "m.json")  # persistiu, inclusive o "já avisado"
    assert again.killed_at("gartua") == now
    assert again.due_alerts(utc(2026, 10, 20, 7, 58), 5) == []


def test_board_rejects_bad_input(tmp_path):
    b = KillBoard(tmp_path / "m.json")
    now = utc(2026, 10, 19, 20, 0)
    with pytest.raises(BoardError):
        b.set("dragao", now, "x", "app", now)
    with pytest.raises(BoardError):
        b.set("gartua", now + timedelta(hours=1), "x", "app", now)
    with pytest.raises(BoardError):
        b.set("gartua", now - timedelta(days=3), "x", "app", now)


def test_app_store_applies_group_state(tmp_path):
    s = Store(tmp_path / "d.json")
    state = {"gartua": {"killed_at": "2026-10-19T20:00:00+00:00", "by": "Ana", "via": "discord"},
             "lagta": {"killed_at": None, "by": "Bia", "via": "app"}}
    assert s.apply_group(state)
    assert s.respawn_time("gartua") == utc(2026, 10, 20, 8, 0)  # morte 20:00 + 12 h
    assert s.respawn_time("lagta") is None
    assert s.kill_meta("gartua")["by"] == "Ana"
    assert not s.apply_group(state)  # nada mudou


def test_api_roundtrip(tmp_path):
    """Sobe a API de verdade numa porta local e conversa com ela pelo cliente do app."""
    aiohttp = pytest.importorskip("aiohttp")
    import asyncio
    from aiohttp import web

    from bot.web import make_app
    from daeva import group

    board = KillBoard(tmp_path / "m.json")
    changes = []

    async def on_change(boss, rec):
        changes.append((boss, rec["by"]))

    loop = asyncio.new_event_loop()
    ready = threading.Event()
    holder = {}

    async def start():
        runner = web.AppRunner(make_app(board, "segredo", on_change))
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        holder["port"] = site._server.sockets[0].getsockname()[1]
        holder["runner"] = runner
        ready.set()

    t = threading.Thread(target=lambda: (loop.run_until_complete(start()), loop.run_forever()), daemon=True)
    t.start()
    assert ready.wait(5)
    base = f"http://127.0.0.1:{holder['port']}"
    try:
        group.ping(base, "segredo")
        with pytest.raises(group.GroupError, match="Chave"):
            group.ping(base, "errada")
        killed = datetime.now(UTC) - timedelta(minutes=3)
        state = group.post_kill(base, "segredo", "gartua", None, "Kumaglad", killed_at_iso=killed.isoformat())
        assert state["gartua"]["by"] == "Kumaglad" and state["gartua"]["via"] == "app"
        assert group.get_kills(base, "segredo")["gartua"]["killed_at"]
        due = datetime.now(UTC) + timedelta(hours=3, minutes=20)
        state = group.post_kill(base, "segredo", "lagta", due.isoformat(), "Ana")
        assert state["lagta"]["killed_at"] is None and state["lagta"]["respawn_at"]
        with pytest.raises(group.GroupError, match="futuro"):
            group.post_kill(base, "segredo", "gartua", None, "x",
                            killed_at_iso=(datetime.now(UTC) + timedelta(hours=2)).isoformat())
        assert changes == [("gartua", "Kumaglad"), ("lagta", "Ana")]
    finally:
        asyncio.run_coroutine_threadsafe(holder["runner"].cleanup(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)


def test_parse_remaining():
    assert parse_remaining("3h20") == timedelta(hours=3, minutes=20)
    assert parse_remaining("3h 20m") == timedelta(hours=3, minutes=20)
    assert parse_remaining("3:05") == timedelta(hours=3, minutes=5)
    assert parse_remaining("2h") == timedelta(hours=2)
    assert parse_remaining("45m") == timedelta(minutes=45)
    assert parse_remaining("90") == timedelta(minutes=90)
    for bad in ("amanhã", "3h75", "60h"):
        with pytest.raises(BoardError):
            parse_remaining(bad)


def test_board_remaining_time(tmp_path):
    b = KillBoard(tmp_path / "m.json")
    now = utc(2026, 10, 19, 20, 0)
    b.set("gartua", None, "Ana", "discord", now, respawn_at=now + timedelta(hours=3, minutes=20))
    assert b.respawn_at("gartua") == utc(2026, 10, 19, 23, 20)
    assert b.killed_at("gartua") is None
    assert b.snapshot()["bosses"]["gartua"]["respawn_at"] == "2026-10-19T23:20:00+00:00"
    assert b.due_alerts(utc(2026, 10, 19, 23, 16), 5) == ["gartua"]
    with pytest.raises(BoardError):
        b.set("gartua", None, "x", "app", now, respawn_at=now - timedelta(hours=1))


def test_app_store_migrates_old_kill_times(tmp_path):
    import json
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"characters": [], "field_kills": {"gartua": "2026-10-19T20:00:00+00:00"}}))
    assert Store(path).respawn_time("gartua") == utc(2026, 10, 20, 8, 0)


def test_timers_mostra_gartua_e_shugo(tmp_path):
    from bot.painel import timers_text
    board = KillBoard(tmp_path / "mortes.json")
    now = utc(2026, 10, 23, 21, 40)  # 18:40 em Brasília
    board.set("gartua", now - timedelta(hours=2), "Kumaglad", "discord", now)
    board.set("lagta", now - timedelta(hours=1), "Fuwawa", "discord", now)
    txt = timers_text(board, now, SP)
    assert "**Eternal Gartua** (Elyos): nasce <t:" in txt and "por Kumaglad" in txt
    assert "**Immortal Gartua** (Asmodiano): sem registro" in txt
    shugo = utc(2026, 10, 23, 22, 0)
    assert f"<t:{int(shugo.timestamp())}:R>" in txt
    assert "High Commander Lagta" in txt and "Silent Dartan" not in txt
    aberto = timers_text(board, utc(2026, 10, 23, 22, 1), SP)
    assert "entrada aberta agora" in aberto


def test_artes_cabem_numa_mensagem():
    from bot.arte import RUGE, VELSTA
    for art in (RUGE, VELSTA):
        assert len(f"```\n{art}\n```") <= 2000
    assert len(RUGE.splitlines()) == 22 and len({len(l) for l in RUGE.splitlines()}) == 1
