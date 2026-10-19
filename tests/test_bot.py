import json
import threading
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from bot.state import BoardError, KillBoard, parse_clock
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
    assert s.kill_time("gartua") == utc(2026, 10, 19, 20, 0)
    assert s.kill_time("lagta") is None
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
        state = group.post_kill(base, "segredo", "gartua", killed.isoformat(), "Kumaglad")
        assert state["gartua"]["by"] == "Kumaglad" and state["gartua"]["via"] == "app"
        assert group.get_kills(base, "segredo")["gartua"]["killed_at"]
        with pytest.raises(group.GroupError, match="futuro"):
            group.post_kill(base, "segredo", "gartua", (datetime.now(UTC) + timedelta(hours=2)).isoformat(), "x")
        assert changes == [("gartua", "Kumaglad")]
    finally:
        asyncio.run_coroutine_threadsafe(holder["runner"].cleanup(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)
