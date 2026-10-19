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
    cls, level = _class_level((_meta(page, "og:title") + " " + desc + " " + text[:4000]))
    return ProfileData(_int(m_cp.group(1)), gs, cls, level)


def parse_aion2index(page: str) -> ProfileData:
    text = _visible_text(page)
    m_cp = re.search(r"Combat power\s*:?\s*" + _NUM, text, re.I)
    m_il = re.search(r"Item level\s*:?\s*" + _NUM, text, re.I)
    if not m_cp or not m_il:
        raise ProfileError("A página do AION2 Index não trouxe Combat power e Item level. "
                           "O personagem pode não existir ou o site mudou de formato.")
    cls, level = _class_level(text[:6000])
    if not cls:
        m = re.search(r"class_icon_([a-z]+)\.", page)
        if m and m.group(1) in CLASSES_PT:
            cls = CLASSES_PT[m.group(1)]
    return ProfileData(_int(m_cp.group(1)), _int(m_il.group(1)), cls, level)


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
