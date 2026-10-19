"""Conquistas que dão título, bônus de cada título e sugestão do melhor alvo.

A lista de conquistas vem embutida (daeva/data/conquistas_titulos.json). Os bônus de cada título
(grau, facção, bônus equipado e bônus de coleção) são lidos da página pública do título na
MetaBot.GG e guardados em cache local. A MetaBot permite reaproveitar os dados com um link de
crédito para a página de origem (metabot.gg/en/ai); o app mostra esse link em cada título.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import __version__
from .profiles import _visible_text
from .sound import resource

TITLE_URL = "https://metabot.gg/en/aion-2/titles/{slug}"
CREDIT = "Dados de conquistas e títulos: MetaBot.GG"


@dataclass
class Achievement:
    id: str
    group: str
    achievement: str
    goal: str
    title: str
    slug: str
    tiers: bool

    @property
    def url(self) -> str:
        return TITLE_URL.format(slug=self.slug)

    @property
    def target_count(self) -> int | None:
        """Número da meta, quando ela é contável ('Defeat 100 monsters' -> 100)."""
        m = re.search(r"(?<![+\d,])\b(\d[\d,]*)\s+(?!or\b)[A-Za-z]", self.goal)
        if not m:
            m = re.search(r"Level (\d+)", self.goal)
        if not m:
            return None
        n = int(m.group(1).replace(",", ""))
        return n if n > 1 else None


@dataclass
class TitleInfo:
    grade: str = ""
    faction: str = ""  # "Elyos" | "Asmodian" | "Both factions"
    role: str = ""
    equip: list[tuple[str, str]] = field(default_factory=list)
    collection: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"grade": self.grade, "faction": self.faction, "role": self.role,
                "equip": [list(x) for x in self.equip], "collection": [list(x) for x in self.collection]}

    @classmethod
    def from_dict(cls, d: dict) -> "TitleInfo":
        return cls(d.get("grade", ""), d.get("faction", ""), d.get("role", ""),
                   [tuple(x) for x in d.get("equip", [])], [tuple(x) for x in d.get("collection", [])])

    def fits(self, faction: str) -> bool:
        return not faction or not self.faction or self.faction.startswith("Both") or self.faction == faction


def load_achievements() -> tuple[list[Achievement], dict[str, str]]:
    path = resource("daeva/data/conquistas_titulos.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = {g["id"]: g["name"] for g in data["groups"]}
    return [Achievement(**i) for i in data["items"]], groups


# ------------------------------------------------------------------ página do título
_STAT = re.compile(r"([A-Za-z][A-Za-z'()\-]*(?:\s+[A-Za-z'()\-]+){0,5}?)\s*\+\s*(\d[\d.,]*%?)")
_END = r"(?=How to get|You earn it|Where to get|Source|Related|Achievement|Similar|$)"


def _stats(chunk: str) -> list[tuple[str, str]]:
    out = []
    for name, val in _STAT.findall(chunk):
        name = re.sub(r"^(?:When equipped|Collection bonus(?: \(owned\))?|Equip(?:ped)?|bonus)\s*", "", name.strip(), flags=re.I)
        if name and len(name) <= 40:
            out.append((name, "+" + val))
    return out


def parse_title_page(page: str) -> TitleInfo:
    text = _visible_text(page)
    info = TitleInfo()
    m = re.search(r"\bGrade\s+(Common|Rare|Legendary|Legend|Epic|Unique|Special|Mythic|Heroic|Eternal)\b", text)
    if m:
        info.grade = m.group(1)
    m = re.search(r"\bFaction\s+(Elyos|Asmodian|Both factions)\b", text)
    if m:
        info.faction = m.group(1)
    m = re.search(r"\bRole\s+(Offensive|Defensive|Utility)\b", text)
    if m:
        info.role = m.group(1)
    m = re.search(r"When equipped(.*?)(?=Collection bonus|$)", text, re.S)
    if m:
        info.equip = _stats(m.group(1)[:400])
    m = re.search(r"Collection bonus(?: \(owned\))?(.*?)" + _END, text, re.S)
    if m:
        info.collection = _stats(m.group(1)[:300])
    if not (info.grade or info.equip or info.collection):
        raise ValueError("Página de título sem os dados esperados.")
    return info


def fetch_title(slug: str, timeout: float = 20) -> TitleInfo:
    req = urllib.request.Request(TITLE_URL.format(slug=slug), headers={
        "User-Agent": f"DiarioDeDaeva/{__version__} (app de fã; credita MetaBot.GG)",
        "Accept": "text/html", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        page = r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    return parse_title_page(page)


# ------------------------------------------------------------------ sugestões
FOCUS = {
    "pve": ("Ataque (PvE)", ("PvE Attack", "PvE Damage", "Attack Bonus", "Penetration", "Critical", "Accuracy",
                             "Damage Boost", "Additional Damage")),
    "pvp": ("Ataque (PvP)", ("PvP Attack", "PvP Damage", "PvP Accuracy", "PvP Penetration", "Endurance Penetration",
                             "Attack Bonus", "Critical")),
    "def": ("Defesa", ("Defense", "Damage Tolerance", "Block", "HP", "Evasion", "Endurance", "Resist")),
    "any": ("Qualquer bônus", ()),
}


def _matches(stat: str, keys: tuple[str, ...], focus: str) -> bool:
    if not keys:
        return True
    if focus == "pve" and stat.startswith("PvP"):
        return False
    if focus == "def" and "Penetration" in stat:
        return False
    return any(k.lower() in stat.lower() for k in keys)


def score(info: TitleInfo | None, focus: str) -> tuple[int, int]:
    """(stats de coleção que servem ao foco, stats equipados que servem ao foco). Maior é melhor.
    O bônus de coleção pesa mais porque vale para sempre, mesmo sem equipar."""
    if info is None:
        return (0, 0)
    keys = FOCUS.get(focus, FOCUS["any"])[1]
    c = sum(1 for s, _ in info.collection if _matches(s, keys, focus))
    e = sum(1 for s, _ in info.equip if _matches(s, keys, focus))
    return (c, e)


def fmt_stats(stats: list[tuple[str, str]]) -> str:
    return ", ".join(f"{s} {v}" for s, v in stats) if stats else "—"
