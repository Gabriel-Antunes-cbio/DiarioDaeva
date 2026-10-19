"""Agenda de bosses e eventos do AION 2 (servidores Global).

Os horários fixos seguem o relógio do servidor da região. Na América Latina
(Siel e cia.) esse relógio é o horário de Brasília. Bosses de campo não têm
horário fixo: renascem um tempo depois de morrer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

REGIONS = {
    "la": ("América Latina", "America/Sao_Paulo"),
    "nae": ("NA Leste", "America/New_York"),
    "naw": ("NA Oeste", "America/Los_Angeles"),
    "eu": ("Europa", "Europe/Berlin"),
    "as": ("Ásia", "Asia/Tokyo"),
}

# 0 = segunda ... 6 = domingo (padrão do Python)
SEG, TER, QUA, QUI, SEX, SAB, DOM = range(7)


@dataclass(frozen=True)
class Event:
    id: str
    name: str
    en: str
    times: tuple[tuple[int, int], ...]
    days: tuple[int, ...] | None = None  # None = todo dia
    duration_min: int = 30
    unconfirmed: bool = False
    detail: str = ""
    big: bool = False  # boss grande: alerta ligado por padrão


def _hours(hours, minute=0):
    return tuple((h, minute) for h in hours)


EVENTS: tuple[Event, ...] = (
    Event("nahma", "Senhor Guardião Nahma", "Guardian Lord Nahma",
          _hours([21]), (SEX, DOM), 30, unconfirmed=True, big=True,
          detail="Abismo Inferior (Lv 65) e Nahma Enfurecido no Médio (Lv 80)"),
    Event("execs", "Executores do Abismo", "Siege Bosses",
          _hours([21], 30), (SEG, QUI, SAB), 30, big=True,
          detail="Inferior: Tamasa, Argo, Kaira · Médio: Dramos, Ducal, Marakha"),
    Event("kaira", "Vigia Kaira", "Watcher Kaira",
          _hours([1, 4, 7, 10, 13, 16, 19, 22]), None, 30, unconfirmed=True, big=True,
          detail="Ronda o Abismo Inferior; alguns guias indicam início às 02:00"),
    Event("siege", "Cerco de Artefato", "Artifact Siege",
          _hours([21]), (SEG, QUI, SAB), 30),
    Event("rift", "Fenda Espaço-Tempo", "Spacetime Rift",
          _hours([2, 5, 8, 11, 14, 17, 20, 23]), None, 10,
          detail="Portal aberto por 10 minutos"),
)


@dataclass(frozen=True)
class FieldBoss:
    id: str
    name: str
    respawn_h: int
    where: str = ""
    big: bool = False


FIELD_BOSSES: tuple[FieldBoss, ...] = (
    FieldBoss("gartua", "Immortal Gartua", 12, big=True),
    FieldBoss("lagta", "High Commander Lagta", 12,
              "Plantação Drana (Verteron) · Fortaleza Lagta (Altgard)"),
    FieldBoss("dartan", "Silent Dartan", 6,
              "Planalto Sul de Altamia (Verteron) · Ruínas de Basfelt (Altgard)"),
    FieldBoss("kashapa", "Soul Ruler Kashapa", 6, "Verteron · Depósito de Fafnita (Altgard)"),
    FieldBoss("danar", "Melted Danar", 1),
)

EVENT_BY_ID = {e.id: e for e in EVENTS}
FIELD_BY_ID = {b.id: b for b in FIELD_BOSSES}


@dataclass
class Occurrence:
    start: datetime  # sempre com fuso (UTC)
    end: datetime

    def live(self, now: datetime) -> bool:
        return self.start <= now < self.end


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def next_occurrence(ev: Event, now: datetime, tz_name: str) -> Occurrence | None:
    """Ocorrência em andamento ou a próxima, para o relógio de servidor `tz_name`."""
    tz = ZoneInfo(tz_name)
    today = now.astimezone(tz).date()
    best: Occurrence | None = None
    for k in range(-1, 9):
        day: date = today + timedelta(days=k)
        if ev.days is not None and day.weekday() not in ev.days:
            continue
        for h, m in ev.times:
            start = datetime.combine(day, time(h, m), tzinfo=tz).astimezone(timezone.utc)
            end = start + timedelta(minutes=ev.duration_min)
            if end <= now:
                continue
            if best is None or start < best.start:
                best = Occurrence(start, end)
        if best is not None and k >= 1:
            break
    return best


def field_respawn(boss: FieldBoss, killed_at: datetime | None) -> datetime | None:
    if killed_at is None:
        return None
    return killed_at + timedelta(hours=boss.respawn_h)


def fmt_left(delta: timedelta) -> str:
    s = max(0, int(delta.total_seconds()))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


@dataclass
class AlertTracker:
    """Decide quando tocar o alerta: uma vez por ocorrência, `lead` minutos antes."""
    fired: set[str] = field(default_factory=set)

    def due(self, key: str, start: datetime, now: datetime, lead_min: int) -> bool:
        left = (start - now).total_seconds()
        if key in self.fired or left <= 0 or left > lead_min * 60:
            return False
        self.fired.add(key)
        if len(self.fired) > 500:
            self.fired = set(list(self.fired)[-200:])
        return True
