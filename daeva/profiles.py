"""Leitura de perfis públicos de personagem no Shugo.GG e no AION2 Index.

O app só lê a página pública do personagem, do mesmo jeito que um navegador.
Nada aqui toca no cliente do jogo ou na conta NC.
"""
from __future__ import annotations

import html as htmllib
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlparse

from . import __version__

REGION_CODES = ("la", "eu", "nae", "naw", "as")
USER_AGENT = f"DiarioDeDaeva/{__version__} (app pessoal; leitura de perfil publico)"

CLASSES_PT = {
    "gladiator": "Gladiador", "templar": "Templário", "assassin": "Assassino",
    "ranger": "Caçador", "sorcerer": "Feiticeiro", "spiritmaster": "Espiritualista",
    "cleric": "Clérigo", "chanter": "Cantor",
}


class ProfileError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


@dataclass
class ProfileLink:
    source: str  # "shugo" | "aion2index"
    region: str
    server: str
    name: str
    url: str

    @property
    def gear_label(self) -> str:
        return "Item level" if self.source == "aion2index" else "Gear score"

    @property
    def site_name(self) -> str:
        return "AION2 Index" if self.source == "aion2index" else "Shugo.GG"


@dataclass
class ProfileData:
    cp: int
    gear: int
    cls: str = ""
    level: int | None = None
    faction: str = ""


def _cap(s: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in s.replace("-", " ").split())


def parse_link(raw: str) -> ProfileLink:
    """Reconhece um link de perfil. Levanta ProfileError com o motivo se não reconhecer."""
    raw = (raw or "").strip()
    if not raw:
        raise ProfileError("Cole o link da página do personagem.")
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    u = urlparse(raw)
    host = (u.hostname or "").lower().removeprefix("www.")
    seg = [unquote(p) for p in u.path.split("/") if p]

    if host == "shugo.gg" and len(seg) >= 4 and seg[0] == "character":
        if seg[1].lower() != "global":
            raise ProfileError("Esse link é de um servidor coreano ou taiwanês. Use um personagem dos servidores Global.")
        m = re.fullmatch(r"(la|eu|nae|naw|as)-(.+)", seg[2].lower())
        if not m:
            raise ProfileError("Não reconheci a região e o servidor nesse link do Shugo.GG.")
        region, server = m.group(1), m.group(2)
        name = seg[3]
        url = f"https://shugo.gg/character/global/{region}-{quote(server)}/{quote(name)}"
        return ProfileLink("shugo", region, _cap(server), name, url)

    if host == "aion2index.com" and len(seg) >= 4 and seg[0] == "c":
        region = seg[1].lower()
        if region not in REGION_CODES:
            raise ProfileError("Não reconheci a região nesse link do AION2 Index.")
        server, name = seg[2].lower(), seg[3]
        url = f"https://aion2index.com/c/{region}/{quote(server)}/{quote(name)}"
        return ProfileLink("aion2index", region, _cap(server), name, url)

    raise ProfileError("Use o endereço da página do personagem no Shugo.GG "
                       "(shugo.gg/character/global/la-siel/Nome) ou no AION2 Index "
                       "(aion2index.com/c/la/siel/Nome).")


# ---------------------------------------------------------------- HTML -> texto

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.S | re.I)
_NUM = r"(\d{1,3}(?:[.,\s]\d{3})+|\d+)"


def _visible_text(page: str) -> str:
    t = _SCRIPT.sub(" ", page)
    t = _TAG.sub(" ", t)
    t = htmllib.unescape(t)
    return re.sub(r"\s+", " ", t)


def _meta(page: str, key: str) -> str:
    for pat in (rf'<meta[^>]+(?:name|property)="{re.escape(key)}"[^>]+content="([^"]*)"',
                rf'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="{re.escape(key)}"'):
        m = re.search(pat, page, re.I)
        if m:
            return htmllib.unescape(m.group(1))
    return ""


def _int(s: str) -> int:
    return int(re.sub(r"\D", "", s))


def _class_level(text: str) -> tuple[str, int | None]:
    cls, level = "", None
    m = re.search(r"\b(" + "|".join(CLASSES_PT) + r")\b", text, re.I)
    if m:
        cls = CLASSES_PT[m.group(1).lower()]
    m = re.search(r"\b(?:Level|Lv\.?)\s*(\d{1,2})\b", text, re.I)
    if m:
        level = int(m.group(1))
    return cls, level


def _faction(text: str) -> str:
    m = re.search(r"\b(Elyos|Asmodian)s?\b", text)
    return m.group(1) if m else ""


def parse_shugo(page: str) -> ProfileData:
    text = _visible_text(page)
    # Resumo do perfil: "... Gear score 1,723 · ... · Combat power 106,302"
    # (listas de outros personagens usam "130,317 Combat Power", número antes do rótulo)
    m_cp = re.search(r"Combat power\s*:?\s*" + _NUM, text) or \
        re.search(r"Combat Power\s*:?\s*" + _NUM, text)
    gs = None
    desc = _meta(page, "description") or _meta(page, "og:description")
    m = re.search(_NUM + r"\s*GS\b", desc)
    if m:
        gs = _int(m.group(1))
    if gs is None:
        m = re.search(r"Gear score\s*:?\s*" + _NUM, text, re.I)
        if m:
            gs = _int(m.group(1))
    if not m_cp or gs is None:
        raise ProfileError("A página do Shugo.GG não trouxe Combat Power e Gear score. "
                           "O personagem pode não existir ou o site mudou de formato.")
    head = _meta(page, "og:title") + " " + desc + " " + text[:4000]
    cls, level = _class_level(head)
    return ProfileData(_int(m_cp.group(1)), gs, cls, level, _faction(head))


def parse_aion2index(page: str) -> ProfileData:
    text = _visible_text(page)
    m_cp = re.search(r"Combat power\s*:?\s*" + _NUM, text, re.I)
    m_il = re.search(r"Item level\s*:?\s*" + _NUM, text, re.I)
    if not m_cp or not m_il:
        raise ProfileError("A página do AION2 Index não trouxe Combat power e Item level. "
                           "O personagem pode não existir ou o site mudou de formato.")
    cls, level = _class_level(text[:6000])
    faction = _faction(text[:6000])
    if not cls:
        m = re.search(r"class_icon_([a-z]+)\.", page)
        if m and m.group(1) in CLASSES_PT:
            cls = CLASSES_PT[m.group(1)]
    return ProfileData(_int(m_cp.group(1)), _int(m_il.group(1)), cls, level, faction)


def fetch_profile(link: ProfileLink, timeout: float = 20) -> ProfileData:
    req = urllib.request.Request(link.url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            page = resp.read(3_000_000).decode(charset, "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ProfileError(f"{link.site_name} não encontrou {link.name} em {link.server}.") from e
        raise ProfileError(f"{link.site_name} respondeu com erro {e.code}. Tente mais tarde.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProfileError(f"Sem conexão com {link.site_name}. Confira a internet e tente de novo.") from e
    parser = parse_aion2index if link.source == "aion2index" else parse_shugo
    return parser(page)


# ================================================================ detalhes do personagem
# Equipamento: tabela "Equipment" do Shugo.GG (Slot | Item +N | Grau).
# Skills e contagem de títulos: páginas /skills e /titles do AION2 Index.
# As duas URLs saem da mesma região/servidor/nome, seja qual for o link que a pessoa colou.

def detail_urls(link: ProfileLink) -> dict[str, str]:
    srv, name = quote(link.server.lower().replace(" ", "-")), quote(link.name)
    a2i = f"https://aion2index.com/c/{link.region}/{srv}/{name}"
    return {"gear": f"https://shugo.gg/character/global/{link.region}-{srv}/{name}",
            "skills": a2i + "/skills", "titles": a2i + "/titles"}


_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<t([dh])\b[^>]*>(.*?)</t[dh]>", re.S | re.I)


def _cell_text(html_: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(_TAG.sub(" ", html_))).strip()


def parse_shugo_gear(page: str) -> list[dict]:
    """Linhas da tabela de equipamento: {slot, item, enchant, grade}."""
    gear = []
    for row in _ROW.findall(page):
        cells = _CELL.findall(row)
        if len(cells) < 3 or any(kind.lower() == "h" for kind, _ in cells):
            continue
        slot, item, grade = (_cell_text(c) for _, c in cells[:3])
        m = re.fullmatch(r"(.*?)\s*\+(\d{1,2})\s*(◆*\d*)", item)
        name, enchant = (m.group(1), int(m.group(2))) if m else (item, 0)
        if slot and name and len(slot) <= 20 and grade and len(grade) <= 15:
            gear.append({"slot": slot, "item": name.strip(), "enchant": enchant, "grade": grade})
    return gear


_SKILL = re.compile(r"(?<![\w+])(\d{1,2})\s+([A-Z][A-Za-z'’:,\- ]{1,40}?)\s+Learned at Lv\.?\s*\d+")


def parse_a2i_skills(page: str) -> dict[str, list[list]]:
    """{'active': [[nome, nível]], 'passive': [...], 'stigma': [...]} a partir do texto da página /skills."""
    text = _visible_text(page)
    marks = [(m.start(), key) for key, pat in (("active", r"Active skills"), ("passive", r"Passive skills"),
                                                ("stigma", r"Stigma skills"))
             for m in [re.search(pat, text, re.I)] if m]
    marks.sort()
    out: dict[str, list[list]] = {"active": [], "passive": [], "stigma": []}
    for i, (start, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        for lvl, name in _SKILL.findall(text[start:end]):
            out[key].append([name.strip(), int(lvl)])
    return out


def parse_a2i_title_counts(page: str) -> dict[str, list[int]]:
    """{'Utility': [66, 99], 'Attack': [68, 103], 'Defense': [66, 95], 'total': [200, 297]}"""
    text = _visible_text(page)
    out = {}
    for cat in ("Utility", "Attack", "Defense"):
        m = re.search(cat + r"\D{0,30}?(\d{1,4})\s*/\s*(\d{1,4})", text)
        if m:
            out[cat] = [int(m.group(1)), int(m.group(2))]
    if out:
        out["total"] = [sum(v[0] for v in out.values()), sum(v[1] for v in out.values())]
    else:
        m = re.search(r"(\d{1,4})\s*/\s*(\d{2,4})", text)
        if m:
            out["total"] = [int(m.group(1)), int(m.group(2))]
    return out


def _get(url: str, timeout: float = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(3_000_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")


def fetch_details(link: ProfileLink) -> dict:
    """Busca equipamento, skills e títulos. Cada parte falha sozinha, sem derrubar as outras."""
    urls = detail_urls(link)
    out: dict = {"gear": None, "skills": None, "titles": None, "errors": [], "sources": urls}
    for key, parser in (("gear", parse_shugo_gear), ("skills", parse_a2i_skills), ("titles", parse_a2i_title_counts)):
        try:
            data = parser(_get(urls[key]))
            empty = not data or (key == "skills" and not any(data.values()))
            if empty:
                raise ValueError("vazio")
            out[key] = data
        except Exception:
            out["errors"].append(key)
    return out
