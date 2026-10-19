"""Quadro de mortes dos bosses de campo, compartilhado pelo grupo.

Guarda, para cada boss, quando ele morreu, quem marcou e por onde (Discord ou app).
É a fonte da verdade: o bot e o app de cada amigo leem daqui.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from daeva.schedule import FIELD_BY_ID, FIELD_BOSSES

MAX_PAST = timedelta(hours=48)
MAX_FUTURE = timedelta(minutes=5)


class BoardError(ValueError):
    """Erro com mensagem pronta para mostrar a quem marcou."""


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds") if dt else None


def parse_iso(s) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_clock(text: str, tz_name: str, now: datetime) -> datetime:
    """'14:32', '14h32', '1432' ou '9:05' no fuso do servidor. Se ficar no futuro, conta como ontem."""
    t = (text or "").strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})[:h]?(\d{2})", t)
    if not m:
        raise BoardError("Não entendi o horário. Use o formato 14:32.")
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        raise BoardError("Horário inválido. Use o formato 14:32.")
    tz = ZoneInfo(tz_name)
    local_now = now.astimezone(tz)
    dt = local_now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if dt > local_now + timedelta(minutes=1):
        dt -= timedelta(days=1)
    return dt.astimezone(timezone.utc)


class KillBoard:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.bosses: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for bid, rec in (raw.get("bosses") or {}).items():
            if bid in FIELD_BY_ID and isinstance(rec, dict):
                self.bosses[bid] = rec

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"bosses": self.bosses}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def snapshot(self) -> dict:
        return {"bosses": {bid: dict(rec) for bid, rec in self.bosses.items()}}

    def killed_at(self, boss_id: str) -> datetime | None:
        return parse_iso((self.bosses.get(boss_id) or {}).get("killed_at"))

    def respawn_at(self, boss_id: str) -> datetime | None:
        k = self.killed_at(boss_id)
        return k + timedelta(hours=FIELD_BY_ID[boss_id].respawn_h) if k else None

    def set(self, boss_id: str, killed_at: datetime | None, by: str, via: str, now: datetime) -> dict:
        if boss_id not in FIELD_BY_ID:
            raise BoardError("Boss desconhecido.")
        if killed_at is not None:
            if killed_at > now + MAX_FUTURE:
                raise BoardError("Esse horário está no futuro.")
            if killed_at < now - MAX_PAST:
                raise BoardError("Esse horário tem mais de 48 horas.")
        rec = {
            "killed_at": iso(killed_at),
            "by": (by or "alguém").strip()[:40] or "alguém",
            "via": via if via in ("discord", "app") else "app",
            "updated_at": iso(now),
            "alerted": False,
        }
        self.bosses[boss_id] = rec
        self.save()
        return rec

    def due_alerts(self, now: datetime, lead_min: int) -> list[str]:
        """Bosses que nascem nos próximos `lead_min` minutos e ainda não foram avisados."""
        out = []
        for b in FIELD_BOSSES:
            rec = self.bosses.get(b.id)
            due = self.respawn_at(b.id)
            if not rec or due is None or rec.get("alerted"):
                continue
            left = (due - now).total_seconds()
            if 0 < left <= lead_min * 60:
                rec["alerted"] = True
                out.append(b.id)
            elif left <= 0:
                rec["alerted"] = True  # já passou (ex.: bot estava desligado): não avisa atrasado
        if out:
            self.save()
        return out
