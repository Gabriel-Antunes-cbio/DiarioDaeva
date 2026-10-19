"""Cliente da API do bot do grupo (horários dos bosses de campo compartilhados)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from . import __version__


class GroupError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url


def _request(base: str, key: str, path: str, body: dict | None = None, timeout: float = 10) -> dict:
    base = normalize_url(base)
    if not base or not key:
        raise GroupError("Preencha o endereço do bot e a chave do grupo em Ajustes.")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method="POST" if body is not None else "GET", headers={
        "X-Daeva-Key": key.strip(),
        "Content-Type": "application/json",
        "User-Agent": f"DiarioDeDaeva/{__version__}",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read(200_000).decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise GroupError("Chave do grupo incorreta. Confira com quem administra o bot.") from e
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error")
        except Exception:
            msg = None
        raise GroupError(msg or f"O bot respondeu com erro {e.code}.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GroupError("Sem conexão com o bot. Confira o endereço ou se a VM está ligada.") from e
    except ValueError as e:
        raise GroupError("O endereço não parece ser o bot do Diário de Daeva.") from e


def ping(base: str, key: str) -> None:
    if not _request(base, key, "/api/ping").get("ok"):
        raise GroupError("O endereço não parece ser o bot do Diário de Daeva.")


def get_kills(base: str, key: str) -> dict:
    return _request(base, key, "/api/kills").get("bosses") or {}


def post_kill(base: str, key: str, boss: str, respawn_at_iso: str | None, by: str,
              killed_at_iso: str | None = None) -> dict:
    body = {"boss": boss, "respawn_at": respawn_at_iso, "killed_at": killed_at_iso, "by": by}
    return _request(base, key, "/api/kills", body).get("bosses") or {}
