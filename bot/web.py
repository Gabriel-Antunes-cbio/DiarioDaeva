"""API HTTP pequena para o app dos amigos ler e marcar mortes de bosses.

GET  /api/ping   -> {"ok": true}
GET  /api/kills  -> {"bosses": {...}}
POST /api/kills  {"boss": "gartua", "respawn_at": "<ISO>" | null, "killed_at": "<ISO>" | null, "by": "Kumaglad"}
                 (respawn_at = quando nasce; killed_at = quando morreu; os dois null = limpar)

Todas as rotas exigem o cabeçalho X-Daeva-Key com a chave do grupo.
"""
from __future__ import annotations

import hmac
from datetime import datetime, timezone
from typing import Awaitable, Callable

from aiohttp import web

from .state import BoardError, KillBoard, parse_iso

OnChange = Callable[[str, dict], Awaitable[None]]


def make_app(board: KillBoard, group_key: str, on_change: OnChange | None = None) -> web.Application:
    @web.middleware
    async def auth(request: web.Request, handler):
        given = request.headers.get("X-Daeva-Key", "")
        if not group_key or not hmac.compare_digest(given, group_key):
            return web.json_response({"error": "Chave do grupo incorreta."}, status=401)
        return await handler(request)

    async def ping(_):
        return web.json_response({"ok": True})

    async def get_kills(_):
        return web.json_response(board.snapshot())

    async def post_kill(request: web.Request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Corpo inválido."}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Corpo inválido."}, status=400)
        boss = str(body.get("boss", ""))
        raw_k, raw_r = body.get("killed_at"), body.get("respawn_at")
        killed = parse_iso(raw_k) if raw_k else None
        respawn = parse_iso(raw_r) if raw_r else None
        if (raw_k and killed is None) or (raw_r and respawn is None):
            return web.json_response({"error": "Horário inválido."}, status=400)
        try:
            rec = board.set(boss, killed, str(body.get("by") or ""), "app", datetime.now(timezone.utc), respawn)
        except BoardError as e:
            return web.json_response({"error": str(e)}, status=400)
        if on_change:
            await on_change(boss, rec)
        return web.json_response(board.snapshot())

    app = web.Application(middlewares=[auth], client_max_size=16 * 1024)
    app.router.add_get("/api/ping", ping)
    app.router.add_get("/api/kills", get_kills)
    app.router.add_post("/api/kills", post_kill)
    return app
