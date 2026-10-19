"""Dados locais do app: personagens, histórico de CP/GS, mortes de bosses e ajustes.

Tudo fica num JSON em %APPDATA%\\DiarioDeDaeva\\dados.json (Windows). Nada é enviado
para lugar nenhum.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .schedule import EVENTS, FIELD_BOSSES, FIELD_BY_ID

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
        self.data = {"version": 1, "characters": [], "field_due": {}, "settings": default_settings(),
                     "titles": {"owned": {}, "target": {}, "focus": "pve"}}
        self.cache_path = self.path.with_name("titulos_cache.json")
        self.title_cache: dict[str, dict] = {}
        self.load()

    # ------------------------------------------------------------ persistence
    def load(self) -> None:
        try:
            cache = json.loads(self.cache_path.read_text(encoding="utf-8")) if self.cache_path.exists() else {}
            self.title_cache = cache if isinstance(cache, dict) else {}
        except (OSError, ValueError):
            self.title_cache = {}
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
        self.data["field_due"] = {k: v for k, v in (raw.get("field_due") or {}).items() if isinstance(v, str)}
        # versões até 1.2 guardavam a hora da morte: converte para a hora do respawn
        for k, v in (raw.get("field_kills") or {}).items():
            kt = parse_iso(v) if isinstance(v, str) else None
            if kt and k in FIELD_BY_ID and k not in self.data["field_due"]:
                self.data["field_due"][k] = iso(kt + timedelta(hours=FIELD_BY_ID[k].respawn_h))
        self.data["field_meta"] = {k: v for k, v in (raw.get("field_meta") or {}).items() if isinstance(v, dict)}
        t = raw.get("titles") or {}
        self.data["titles"] = {
            "owned": {k: list(v) for k, v in (t.get("owned") or {}).items() if isinstance(v, list)},
            "target": {k: v for k, v in (t.get("target") or {}).items() if isinstance(v, dict)},
            "focus": t.get("focus") if t.get("focus") in ("pve", "pvp", "def", "any") else "pve",
        }
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
        if getattr(prof, "faction", ""):
            c["faction"] = prof.faction
        hist = c.setdefault("history", [])
        changed = not hist or hist[-1]["cp"] != prof.cp or hist[-1]["gear"] != prof.gear
        if changed:
            hist.append({"t": iso(when), "cp": prof.cp, "gear": prof.gear})
            del hist[:-HISTORY_MAX]
        self.save()
        return changed

    def record_details(self, char_id: str, details: dict, when: datetime) -> None:
        c = self.find(char_id)
        if c is None:
            return
        old = c.get("details") or {}
        new = {k: details.get(k) if details.get(k) is not None else old.get(k) for k in ("gear", "skills", "titles")}
        new["updated"] = iso(when)
        new["errors"] = list(details.get("errors") or [])
        c["details"] = new
        self.save()

    def record_error(self, char_id: str, message: str) -> None:
        c = self.find(char_id)
        if c is not None:
            c["last_error"] = message
            self.save()

    # ------------------------------------------------------------ field bosses
    def respawn_time(self, boss_id: str) -> datetime | None:
        return parse_iso(self.data["field_due"].get(boss_id))

    def kill_meta(self, boss_id: str) -> dict:
        return (self.data.get("field_meta") or {}).get(boss_id) or {}

    def set_respawn(self, boss_id: str, due: datetime | None, by: str = "", via: str = "local",
                    killed: bool = False) -> None:
        """Guarda quando o boss nasce. killed=True quando veio de “Morreu agora”."""
        if due is None:
            self.data["field_due"].pop(boss_id, None)
        else:
            self.data["field_due"][boss_id] = iso(due)
        self.data.setdefault("field_meta", {})[boss_id] = {"by": by, "via": via, "killed": killed}
        self.save()

    def apply_group(self, bosses: dict) -> bool:
        """Substitui os horários locais pelos do bot do grupo. Devolve True se algo mudou."""
        dues, meta = {}, {}
        for bid, rec in (bosses or {}).items():
            if not isinstance(rec, dict) or bid not in FIELD_BY_ID:
                continue
            due = parse_iso(rec.get("respawn_at"))
            if due is None and parse_iso(rec.get("killed_at")):
                due = parse_iso(rec["killed_at"]) + timedelta(hours=FIELD_BY_ID[bid].respawn_h)
            if due:
                dues[bid] = iso(due)
            meta[bid] = {"by": str(rec.get("by") or ""), "via": str(rec.get("via") or ""),
                         "killed": bool(rec.get("killed_at"))}
        changed = dues != self.data["field_due"] or meta != self.data.get("field_meta")
        if changed:
            self.data["field_due"] = dues
            self.data["field_meta"] = meta
            self.save()
        return changed

    @property
    def group_on(self) -> bool:
        return bool(self.settings.get("group_url") and self.settings.get("group_key"))

    # ------------------------------------------------------------ títulos
    @property
    def titles(self) -> dict:
        return self.data["titles"]

    def owned(self, char_id: str) -> set[str]:
        return set(self.titles["owned"].get(char_id, []))

    def set_owned(self, char_id: str, slug: str, on: bool) -> None:
        cur = self.owned(char_id)
        (cur.add if on else cur.discard)(slug)
        self.titles["owned"][char_id] = sorted(cur)
        self.save()

    def target(self, char_id: str) -> dict | None:
        return self.titles["target"].get(char_id)

    def set_target(self, char_id: str, ach_id: str | None) -> None:
        if ach_id is None:
            self.titles["target"].pop(char_id, None)
        else:
            self.titles["target"][char_id] = {"id": ach_id, "progress": 0}
        self.save()

    def set_progress(self, char_id: str, n: int) -> None:
        t = self.target(char_id)
        if t is not None:
            t["progress"] = max(0, int(n))
            self.save()

    def set_focus(self, focus: str) -> None:
        self.titles["focus"] = focus
        self.save()

    def cache_title(self, slug: str, info: dict, when: datetime) -> None:
        self.title_cache[slug] = dict(info, t=iso(when))

    def save_title_cache(self) -> None:
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.title_cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.cache_path)
