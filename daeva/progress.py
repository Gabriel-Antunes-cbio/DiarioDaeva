"""Contadores que andam sozinhos: energia Odyle e chaves do Festival Shugo e da Invasão Dimensional.

O app não lê o jogo: a pessoa informa o valor uma vez e o app calcula o resto a partir da hora em que
o valor foi informado.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Energia Odyle: 5 por hora (15 a cada 3 h). Limite 560, ou 840 com Membership (vale para a conta toda).
ENERGY_RATE = 5
ENERGY_CAP = 560
ENERGY_CAP_MEMBER = 840
ENERGY_COST = 40  # cada recompensa

# Chaves: (quantas entram por dia, limite sem Membership, limite com Membership)
KEYS = {
    "shugo": {"name": "Festival Shugo", "daily": 3, "cap": 12, "cap_member": 21},
    "invasion": {"name": "Invasão Dimensional", "daily": 1, "cap": 7, "cap_member": 7},
}
RESET_HOUR = 4  # reset diário: 04:00 no relógio do servidor (Brasília na América Latina)


def _parse(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------- energia
def energy_cap(member: bool) -> int:
    return ENERGY_CAP_MEMBER if member else ENERGY_CAP


def energy_now(entry: dict | None, now: datetime, member: bool) -> int | None:
    """Energia agora, a partir do último valor informado {'v': 320, 't': iso}."""
    if not entry or _parse(entry.get("t")) is None:
        return None
    cap = energy_cap(member)
    v = int(entry.get("v", 0))
    if v >= cap:
        return v  # já estava no limite (ou acima, se a Membership acabou): não sobe mais
    hours = max(0.0, (now - _parse(entry["t"])).total_seconds() / 3600)
    return min(cap, v + int(hours) * ENERGY_RATE)


def energy_full_at(entry: dict | None, now: datetime, member: bool) -> datetime | None:
    """Quando a energia chega no limite (None se já está cheia ou sem dado)."""
    cur = energy_now(entry, now, member)
    if cur is None or cur >= energy_cap(member):
        return None
    start = _parse(entry["t"])
    base = int(entry.get("v", 0))
    hours_needed = -(-(energy_cap(member) - base) // ENERGY_RATE)  # arredonda para cima
    return start + timedelta(hours=hours_needed)


def energy_entry(value: int, now: datetime) -> dict:
    return {"v": max(0, int(value)), "t": _iso(now)}


# ----------------------------------------------------------------- chaves
def resets_between(a: datetime, b: datetime, tz_name: str, hour: int = RESET_HOUR) -> int:
    """Quantos resets diários (hour:00 no relógio do servidor) aconteceram em (a, b]."""
    if b <= a:
        return 0
    tz = ZoneInfo(tz_name)
    la, lb = a.astimezone(tz), b.astimezone(tz)
    first = datetime.combine(la.date(), time(hour), tzinfo=tz)
    if first <= la:
        first += timedelta(days=1)
    if first > lb:
        return 0
    n, d = 0, first
    while d <= lb and n < 400:
        n += 1
        d = datetime.combine((d + timedelta(days=1)).date(), time(hour), tzinfo=tz)
    return n


def key_cap(kind: str, member: bool) -> int:
    k = KEYS[kind]
    return k["cap_member"] if member else k["cap"]


def keys_now(entry: dict | None, kind: str, now: datetime, tz_name: str, member: bool) -> int | None:
    """Chaves agora, somando as que entraram nos resets desde o último valor informado."""
    if not entry or _parse(entry.get("t")) is None:
        return None
    cap = key_cap(kind, member)
    v = int(entry.get("v", 0))
    if v >= cap:
        return v
    return min(cap, v + resets_between(_parse(entry["t"]), now, tz_name) * KEYS[kind]["daily"])


def keys_entry(value: int, now: datetime) -> dict:
    return {"v": max(0, int(value)), "t": _iso(now)}
