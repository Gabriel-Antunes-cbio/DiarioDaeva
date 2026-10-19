"""Dados locais do app: personagens, histórico de CP/GS, mortes de bosses e ajustes.

Tudo fica num JSON em %APPDATA%\\DiarioDeDaeva\\dados.json (Windows). Nada é enviado
para lugar nenhum.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .schedule import EVENTS, FIELD_BOSSES

HISTORY_MAX = 365


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        d = base / "DiarioDeDaeva"
    else:
        d = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "diario-de-daeva"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_settings() -> dict:
    alerts = {e.id: e.big for e in EVENTS}
    alerts.update({b.id: b.big for b in FIELD_BOSSES})
    return {
        "region": "la",
        "alert_minutes": 5,
        "alerts": alerts,
        "sound": True,
        "tray_notify": True,
        "always_on_top": False,
        "close_to_tray": True,
        "refresh_hours": 6,
        "group_url": "",
        "group_key": "",
        "nickname": "",
    }


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds") if dt else None


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or data_dir() / "dados.json"
        self.data = {"version": 1, "characters": [], "field_kills": {}, "settings": default_settings()}
        self.load()

    # ------------------------------------------------------------ persistence
    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # arquivo corrompido: guarda uma cópia e recomeça
            try:
                self.path.replace(self.path.with_suffix(".corrompido.json"))
            except OSError:
                pass
            return
        if not isinstance(raw, dict):
            return
        self.data["characters"] = [c for c in raw.get("characters", []) if isinstance(c, dict) and c.get("url")]
        self.data["field_kills"] = {k: v for k, v in (raw.get("field_kills") or {}).items() if isinstance(v, str)}
        self.data["field_meta"] = {k: v for k, v in (raw.get("field_meta") or {}).items() if isinstance(v, dict)}
        s = default_settings()
        saved = raw.get("settings") or {}
        alerts = dict(s["alerts"])
        alerts.update({k: bool(v) for k, v in (saved.get("alerts") or {}).items() if k in alerts})
        s.update({k: v for k, v in saved.items() if k in s and k != "alerts"})
        s["alerts"] = alerts
        self.data["settings"] = s

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # ------------------------------------------------------------ settings
    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def set_setting(self, key: str, value) -> None:
        self.settings[key] = value
        self.save()

    def set_alert(self, key: str, on: bool) -> None:
        self.settings["alerts"][key] = bool(on)
        self.save()

    # ------------------------------------------------------------ characters
    @property
    def characters(self) -> list[dict]:
        return self.data["characters"]

    def find(self, char_id: str) -> dict | None:
        return next((c for c in self.characters if c["id"] == char_id), None)

    def add_character(self, link) -> dict:
        for c in self.characters:
            if c["url"] == link.url:
                return c
        c = {
            "id": uuid.uuid4().hex[:10], "url": link.url, "source": link.source,
            "region": link.region, "server": link.server, "name": link.name,
            "gear_label": link.gear_label, "cls": "", "level": None,
            "cp": None, "gear": None, "updated": None, "history": [], "last_error": None,
        }
        self.characters.append(c)
        self.save()
        return c

    def remove_character(self, char_id: str) -> None:
        self.data["characters"] = [c for c in self.characters if c["id"] != char_id]
        self.save()

    def record_profile(self, char_id: str, prof, when: datetime) -> bool:
        """Grava uma leitura. Devolve True se CP ou GS mudou (novo ponto no gráfico)."""
        c = self.find(char_id)
        if c is None:
            return False
        c.update(cp=prof.cp, gear=prof.gear, updated=iso(when), last_error=None)
        if prof.cls:
            c["cls"] = prof.cls
        if prof.level:
            c["level"] = prof.level
        hist = c.setdefault("history", [])
        changed = not hist or hist[-1]["cp"] != prof.cp or hist[-1]["gear"] != prof.gear
        if changed:
            hist.append({"t": iso(when), "cp": prof.cp, "gear": prof.gear})
            del hist[:-HISTORY_MAX]
        self.save()
        return changed

    def record_error(self, char_id: str, message: str) -> None:
        c = self.find(char_id)
        if c is not None:
            c["last_error"] = message
            self.save()

    # ------------------------------------------------------------ field bosses
    def kill_time(self, boss_id: str) -> datetime | None:
        return parse_iso(self.data["field_kills"].get(boss_id))

    def kill_meta(self, boss_id: str) -> dict:
        return (self.data.get("field_meta") or {}).get(boss_id) or {}

    def set_kill(self, boss_id: str, when: datetime | None, by: str = "", via: str = "local") -> None:
        if when is None:
            self.data["field_kills"].pop(boss_id, None)
        else:
            self.data["field_kills"][boss_id] = iso(when)
        self.data.setdefault("field_meta", {})[boss_id] = {"by": by, "via": via}
        self.save()

    def apply_group(self, bosses: dict) -> bool:
        """Substitui os horários locais pelos do bot do grupo. Devolve True se algo mudou."""
        kills, meta = {}, {}
        for bid, rec in (bosses or {}).items():
            if not isinstance(rec, dict):
                continue
            if rec.get("killed_at"):
                kills[bid] = rec["killed_at"]
            meta[bid] = {"by": str(rec.get("by") or ""), "via": str(rec.get("via") or "")}
        changed = kills != self.data["field_kills"] or meta != self.data.get("field_meta")
        if changed:
            self.data["field_kills"] = kills
            self.data["field_meta"] = meta
            self.save()
        return changed

    @property
    def group_on(self) -> bool:
        return bool(self.settings.get("group_url") and self.settings.get("group_key"))
