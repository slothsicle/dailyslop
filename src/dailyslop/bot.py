"""Discord glue: listens for score pastes, reposts them compactly, serves /leaderboard."""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands

from dailyslop.db import Database, Entry
from dailyslop.games import GAMES, Game
from dailyslop.handler import handle_message
from dailyslop.leaderboard import page_count, render_page

log = logging.getLogger("dailyslop")

VIEW_TIMEOUT = 600  # seconds before the page buttons stop working


def build_board(db: Database, guild_id: int, game: Game, scope: str) -> tuple[str, list[Entry]]:
    """Return (title, entries) for a game's board. scope is 'today' or 'all-time'."""
    if scope == "all-time":
        entries = db.all_time_board(guild_id, game.key, higher_is_better=game.higher_is_better)
        return f"{game.title} · all-time", entries
    puzzle = db.latest_puzzle(guild_id, game.key)
    if puzzle is None:
        return f"{game.title} · today", []
    entries = db.puzzle_board(
        guild_id, game.key, puzzle, higher_is_better=game.higher_is_better
    )
    return f"{game.title} #{puzzle}", entries


def board_embed(title: str, entries: list[Entry], page: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=render_page(entries, page))
    embed.set_footer(text=f"Page {page + 1}/{page_count(entries)}")
    return embed


class LeaderboardView(discord.ui.View):
    def __init__(self, title: str, entries: list[Entry]) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.title = title
        self.entries = entries
        self.page = 0
        self.message: discord.Message | None = None
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        last = page_count(self.entries) - 1
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= last

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=board_embed(self.title, self.entries, self.page), view=self
        )

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page -= 1
        await self._show(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page += 1
        await self._show(interaction)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class DailySlopBot(discord.Client):
    def __init__(self, db: Database) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # privileged: enable it in the Developer Portal
        super().__init__(intents=intents)
        self.db = db
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self) -> None:
        game_choices = [app_commands.Choice(name=g.title, value=g.key) for g in GAMES.values()]
        scope_choices = [
            app_commands.Choice(name="Latest puzzle", value="today"),
            app_commands.Choice(name="All-time", value="all-time"),
        ]

        @self.tree.command(name="leaderboard", description="Show a game's leaderboard")
        @app_commands.guild_only()
        @app_commands.choices(game=game_choices, scope=scope_choices)
        async def leaderboard(
            interaction: discord.Interaction,
            game: app_commands.Choice[str],
            scope: app_commands.Choice[str] | None = None,
        ) -> None:
            title, entries = build_board(
                self.db, interaction.guild_id, GAMES[game.value], scope.value if scope else "today"
            )
            if not entries:
                await interaction.response.send_message(
                    f"No {GAMES[game.value].title} scores yet.", ephemeral=True
                )
                return
            view = LeaderboardView(title, entries)
            await interaction.response.send_message(
                embed=board_embed(title, entries, 0), view=view
            )
            view.message = await interaction.original_response()

    async def setup_hook(self) -> None:
        dev_guild = os.environ.get("DEV_GUILD_ID")
        if dev_guild:  # instant command sync for a test server
            guild = discord.Object(id=int(dev_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        result = handle_message(
            self.db,
            guild_id=message.guild.id,
            user_id=message.author.id,
            user_name=message.author.display_name,
            text=message.content,
        )
        if result is None:
            return  # not a score we fully understand: leave the message alone

        if result.is_new:
            title, entries = build_board(
                self.db, message.guild.id, result.game, "today"
            )
            view = LeaderboardView(title, entries)
            # Post first, delete second: if posting fails the original is still there.
            view.message = await message.channel.send(
                f"**{message.author.display_name}** · {result.score.display()}",
                embed=board_embed(title, entries, 0),
                view=view,
            )
        else:
            await message.channel.send(
                f"{message.author.mention}, you already posted "
                f"{result.game.title} #{result.score.puzzle}.",
                delete_after=10,
            )

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning("Missing Manage Messages in #%s; could not delete score", message.channel)
        except discord.NotFound:
            pass
