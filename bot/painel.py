"""Texto do /timers: Gartua, Festival Shugo e os outros bosses de campo com registro.

Fica separado do bot para poder ser testado sem o discord.py.
"""
from __future__ import annotations

from datetime import datetime

from daeva.schedule import EVENT_BY_ID, FIELD_BOSSES, next_occurrence

GARTUA = (("gartua", "Elyos"), ("gartua_imortal", "Asmodiano"))


def ts(dt: datetime, style: str = "t") -> str:
    """Marcação de horário do Discord: cada pessoa vê no próprio fuso."""
    return f"<t:{int(dt.timestamp())}:{style}>"


def boss_line(board, boss, now: datetime, label: str | None = None) -> str:
    name = f"**{boss.name}**" + (f" ({label})" if label else "")
    due = board.respawn_at(boss.id)
    if due is None:
        return f"{name}: sem registro · use `/gartua` ou `/morreu`"
    if due <= now:
        return f"{name}: pode ter nascido (desde {ts(due)})"
    by = (board.bosses.get(boss.id) or {}).get("by", "?")
    return f"{name}: nasce {ts(due, 'R')} às {ts(due)} · por {by}"


def shugo_line(now: datetime, tz_name: str) -> str:
    occ = next_occurrence(EVENT_BY_ID["shugo"], now, tz_name)
    if occ is None:
        return "**Festival Shugo**: sem horário"
    if occ.live(now):
        return f"**Festival Shugo**: 🟢 entrada aberta agora · fecha {ts(occ.end, 'R')}"
    return f"**Festival Shugo**: começa {ts(occ.start, 'R')} às {ts(occ.start)} · toda hora cheia"


def timers_text(board, now: datetime, tz_name: str) -> str:
    by_id = {b.id: b for b in FIELD_BOSSES}
    lines = ["⚔️ **Gartua**"]
    for bid, side in GARTUA:
        lines.append(boss_line(board, by_id[bid], now, side))
    lines += ["", "🎪 **Festival Shugo**", shugo_line(now, tz_name)]
    others = [b for b in FIELD_BOSSES if b.id not in dict(GARTUA) and board.respawn_at(b.id) is not None]
    if others:
        lines += ["", "🗺️ **Outros bosses de campo**"]
        lines += [boss_line(board, b, now) for b in others]
    return "\n".join(lines)
