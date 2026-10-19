"""Bot do Discord do Diário de Daeva.

Comandos:
  /gartua [falta]       Eternal Gartua (Elyos): vazio = morreu agora; ou quanto falta para nascer (3h20)
  /morreu boss [falta]  o mesmo para qualquer boss de campo
  /timers               mostra os respawns registrados
  /limpar boss          apaga o registro de um boss
  /velsta               mostra a arte da Velsta

Avisa no canal configurado alguns minutos antes de cada respawn e serve os horários
para o app dos amigos (ver bot/web.py).

Rodar:  python -m bot.daeva_bot   (a partir da raiz do repositório, com o .env preenchido)
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import discord  # noqa: E402
from aiohttp import web  # noqa: E402
from discord import app_commands  # noqa: E402
from discord.ext import tasks  # noqa: E402

from bot.arte import VELSTA  # noqa: E402
from bot.state import BoardError, KillBoard, parse_remaining  # noqa: E402
from bot.web import make_app  # noqa: E402
from daeva.schedule import FIELD_BOSSES, FIELD_BY_ID  # noqa: E402

log = logging.getLogger("daeva-bot")


def load_env(path: Path) -> None:
    """Lê um .env simples (CHAVE=valor) sem dependências extras."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env(Path(__file__).resolve().parent / ".env")

TOKEN = os.environ.get("DISCORD_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0") or 0)
GUILD_ID = int(os.environ.get("GUILD_ID", "0") or 0)
ROLE_ID = int(os.environ.get("ROLE_ID", "0") or 0)
ALERT_MENTION = os.environ.get("ALERT_MENTION", "").strip().lower().lstrip("@")  # "everyone", "here" ou vazio
GROUP_KEY = os.environ.get("GROUP_KEY", "")
PORT = int(os.environ.get("PORT", "8080") or 8080)
TZ_NAME = os.environ.get("TZ_NAME", "America/Sao_Paulo")
ALERT_MINUTES = int(os.environ.get("ALERT_MINUTES", "5") or 5)
DATA_FILE = Path(os.environ.get("DATA_FILE", str(Path(__file__).resolve().parent / "dados" / "mortes.json")))

BOSS_CHOICES = [app_commands.Choice(name=b.name, value=b.id) for b in FIELD_BOSSES]


def alert_mention() -> tuple[str, discord.AllowedMentions]:
    """Quem é marcado nos avisos: @everyone/@here (ALERT_MENTION) ou o cargo (ROLE_ID)."""
    if ALERT_MENTION in ("everyone", "here"):
        return f"@{ALERT_MENTION} ", discord.AllowedMentions(everyone=True, roles=False, users=False)
    if ROLE_ID:
        return f"<@&{ROLE_ID}> ", discord.AllowedMentions(roles=True, everyone=False, users=False)
    return "", discord.AllowedMentions.none()


def ts(dt: datetime, style: str = "t") -> str:
    """Marcação de horário do Discord: cada pessoa vê no próprio fuso."""
    return f"<t:{int(dt.timestamp())}:{style}>"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DaevaBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.board = KillBoard(DATA_FILE)
        self.runner: web.AppRunner | None = None

    async def setup_hook(self):
        register_commands(self)
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        if GROUP_KEY:
            app = make_app(self.board, GROUP_KEY, self.on_app_change)
            self.runner = web.AppRunner(app, access_log=None)
            await self.runner.setup()
            await web.TCPSite(self.runner, "0.0.0.0", PORT).start()
            log.info("API do app ouvindo na porta %s", PORT)
        else:
            log.warning("GROUP_KEY vazio: a API do app ficou desligada.")
        self.alert_loop.start()

    async def on_ready(self):
        log.info("Conectado como %s", self.user)

    async def channel(self) -> discord.abc.Messageable | None:
        if not CHANNEL_ID:
            return None
        ch = self.get_channel(CHANNEL_ID)
        if ch is None:
            try:
                ch = await self.fetch_channel(CHANNEL_ID)
            except discord.DiscordException:
                log.exception("Não consegui abrir o canal %s", CHANNEL_ID)
                return None
        return ch

    def kill_text(self, boss_id: str, rec: dict) -> str:
        b = FIELD_BY_ID[boss_id]
        killed = self.board.killed_at(boss_id)
        due = self.board.respawn_at(boss_id)
        if due is None:
            return f"🧹 Registro do **{b.name}** apagado por {rec['by']}."
        origem = " pelo app" if rec.get("via") == "app" else ""
        if killed is not None:
            head = f"⚔️ **{b.name}** morreu às {ts(killed)} (marcado por {rec['by']}{origem})."
        else:
            head = f"⏳ **{b.name}**: respawn informado por {rec['by']}{origem}."
        return f"{head}\nNasce {ts(due, 'R')}, às {ts(due)}. Aviso {ALERT_MINUTES} min antes."

    async def on_app_change(self, boss_id: str, rec: dict):
        ch = await self.channel()
        if ch:
            await ch.send(self.kill_text(boss_id, rec), allowed_mentions=discord.AllowedMentions.none())

    @tasks.loop(seconds=20)
    async def alert_loop(self):
        due = self.board.due_alerts(now_utc(), ALERT_MINUTES)
        if not due:
            return
        ch = await self.channel()
        if ch is None:
            return
        mention, allowed = alert_mention()
        for bid in due:
            b = FIELD_BY_ID[bid]
            when = self.board.respawn_at(bid)
            await ch.send(f"{mention}🔔 **{b.name}** nasce {ts(when, 'R')} ({ts(when)}).",
                          allowed_mentions=allowed)

    @alert_loop.before_loop
    async def _wait_ready(self):
        await self.wait_until_ready()

    async def close(self):
        if self.runner:
            await self.runner.cleanup()
        await super().close()


def register_commands(bot: DaevaBot) -> None:
    tree = bot.tree

    async def record(inter: discord.Interaction, boss_id: str, falta: str | None):
        now = now_utc()
        try:
            if falta:
                rec = bot.board.set(boss_id, None, inter.user.display_name, "discord", now,
                                    respawn_at=now + parse_remaining(falta))
            else:
                rec = bot.board.set(boss_id, now, inter.user.display_name, "discord", now)
        except BoardError as e:
            await inter.response.send_message(f"❌ {e}", ephemeral=True)
            return
        await inter.response.send_message(bot.kill_text(boss_id, rec),
                                          allowed_mentions=discord.AllowedMentions.none())

    @tree.command(name="gartua", description="Registra a morte do Eternal Gartua (Elyos)")
    @app_commands.describe(falta="Quanto falta para nascer, como no mapa do jogo (ex.: 3h20). Vazio = morreu agora")
    async def gartua(inter: discord.Interaction, falta: str | None = None):
        await record(inter, "gartua", falta)

    @tree.command(name="morreu", description="Registra a morte de um boss de campo")
    @app_commands.describe(boss="Qual boss", falta="Quanto falta para nascer, como no mapa do jogo (ex.: 3h20). Vazio = morreu agora")
    @app_commands.choices(boss=BOSS_CHOICES)
    async def morreu(inter: discord.Interaction, boss: app_commands.Choice[str], falta: str | None = None):
        await record(inter, boss.value, falta)

    @tree.command(name="timers", description="Mostra os respawns registrados dos bosses de campo")
    async def timers(inter: discord.Interaction):
        now = now_utc()
        lines = []
        for b in FIELD_BOSSES:
            rec = bot.board.bosses.get(b.id) or {}
            due = bot.board.respawn_at(b.id)
            if due is None:
                lines.append(f"**{b.name}**: sem registro")
            elif due <= now:
                lines.append(f"**{b.name}**: pode ter nascido (desde {ts(due)})")
            else:
                lines.append(f"**{b.name}**: nasce {ts(due, 'R')} às {ts(due)} · por {rec.get('by', '?')}")
        await inter.response.send_message("\n".join(lines), allowed_mentions=discord.AllowedMentions.none())

    @tree.command(name="velsta", description="Invoca a Velsta")
    async def velsta(inter: discord.Interaction):
        await inter.response.send_message(f"```\n{VELSTA}\n```")

    @tree.command(name="limpar", description="Apaga o registro de morte de um boss de campo")
    @app_commands.choices(boss=BOSS_CHOICES)
    async def limpar(inter: discord.Interaction, boss: app_commands.Choice[str]):
        rec = bot.board.set(boss.value, None, inter.user.display_name, "discord", now_utc())
        await inter.response.send_message(bot.kill_text(boss.value, rec),
                                          allowed_mentions=discord.AllowedMentions.none())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not TOKEN:
        sys.exit("Falta DISCORD_TOKEN no bot/.env. Veja docs/BOT.md.")
    if not CHANNEL_ID:
        log.warning("CHANNEL_ID vazio: os avisos no canal ficam desligados.")
    if not ALERT_MENTION and not ROLE_ID:
        log.warning("Nem ALERT_MENTION nem ROLE_ID preenchidos: os avisos saem no canal sem marcar ninguém.")
    DaevaBot().run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
