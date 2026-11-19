"""Discord glue: listens for score pastes, reposts them compactly, serves /leaderboard."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

import discord
from discord import app_commands

from dailyslop.boards import SCOPES, build_board
from dailyslop.db import Database
from dailyslop.games import GAMES, Game
from dailyslop.handler import handle_message
from dailyslop.leaderboard import Entry, page_count, quote_annotation, render_page

log = logging.getLogger("dailyslop")

VIEW_TIMEOUT = 600  # seconds before buttons stop working


def board_for(db: Database, guild: discord.Guild, game: Game, scope: str) -> tuple[str, list[Entry]]:
    """Build one server's board, using that server's member list and nicknames."""
    members = guild.members  # needs the Server Members intent
    return build_board(
        db,
        guild.id,
        game,
        scope,
        member_ids={m.id for m in members},
        names={m.id: m.display_name for m in members},
    )


def board_embed(title: str, entries: list[Entry], page: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=render_page(entries, page))
    embed.set_footer(text=f"Page {page + 1}/{page_count(entries)}")
    return embed


SCOPE_LABELS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly", "all-time": "All-time"}


class PeriodButton(discord.ui.Button["LeaderboardView"]):
    def __init__(self, scope: str) -> None:
        super().__init__(label=SCOPE_LABELS[scope], style=discord.ButtonStyle.secondary, row=0)
        self.scope = scope

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.switch(interaction, self.scope)


class LeaderboardView(discord.ui.View):
    """A board with period buttons (daily/weekly/...) on top and page buttons below."""

    def __init__(self, build: Callable[[str], tuple[str, list[Entry]]], scope: str = "daily") -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.build = build  # scope -> (title, entries), rebuilt fresh on every switch
        self.scope = scope
        self.title, self.entries = build(scope)
        self.page = 0
        self.message: discord.Message | None = None
        for s in SCOPES:
            self.add_item(PeriodButton(s))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        last = page_count(self.entries) - 1
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= last
        for child in self.children:
            if isinstance(child, PeriodButton):
                child.style = (
                    discord.ButtonStyle.primary
                    if child.scope == self.scope
                    else discord.ButtonStyle.secondary
                )

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=board_embed(self.title, self.entries, self.page), view=self
        )

    async def switch(self, interaction: discord.Interaction, scope: str) -> None:
        self.scope = scope
        self.title, self.entries = self.build(scope)
        self.page = 0
        await self._show(interaction)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page -= 1
        await self._show(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=1)
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


class SharePromptView(discord.ui.View):
    """One-time question: show this person's scores on their other servers too?"""

    def __init__(self, db: Database, user_id: int) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.db = db
        self.user_id = user_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This question is for someone else.", ephemeral=True
            )
            return False
        return True

    async def _answer(self, interaction: discord.Interaction, share: bool) -> None:
        self.db.set_sharing(self.user_id, share)
        self.stop()
        text = (
            "✅ Your scores will show on the leaderboards of every server you share with this bot."
            if share
            else "👍 Your scores will stay on the server where you post them."
        )
        await interaction.response.edit_message(
            content=f"{text} Change it any time with `/sharing`.", view=None, delete_after=20
        )

    @discord.ui.button(label="Share across servers", style=discord.ButtonStyle.success)
    async def share_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._answer(interaction, True)

    @discord.ui.button(label="Keep separate", style=discord.ButtonStyle.secondary)
    async def private_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._answer(interaction, False)

    async def on_timeout(self) -> None:
        # Unanswered: stay private, tidy up. They can still use /sharing.
        if self.message is not None:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass


class DailySlopBot(discord.Client):
    def __init__(self, db: Database) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # privileged: enable it in the Developer Portal
        intents.members = True  # privileged: needed to know who is in each server
        super().__init__(intents=intents)
        self.db = db
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def mutual_server_count(self, user_id: int) -> int:
        """How many servers running this bot the user is a member of."""
        return sum(1 for g in self.guilds if g.get_member(user_id) is not None)

    def _register_commands(self) -> None:
        game_choices = [app_commands.Choice(name=g.title, value=g.key) for g in GAMES.values()]

        @self.tree.command(
            name="leaderboard", description="Show a game's leaderboard (switch period with the buttons)"
        )
        @app_commands.guild_only()
        @app_commands.choices(game=game_choices)
        async def leaderboard(
            interaction: discord.Interaction, game: app_commands.Choice[str]
        ) -> None:
            guild, chosen = interaction.guild, GAMES[game.value]
            assert guild is not None  # guild_only
            view = LeaderboardView(lambda scope: board_for(self.db, guild, chosen, scope))
            if not view.entries:
                await interaction.response.send_message(
                    f"No {chosen.title} scores yet.", ephemeral=True
                )
                return
            await interaction.response.send_message(
                embed=board_embed(view.title, view.entries, 0), view=view
            )
            view.message = await interaction.original_response()

        @self.tree.command(
            name="sharing", description="Choose whether your scores show on your other servers"
        )
        @app_commands.choices(
            setting=[
                app_commands.Choice(name="Share across servers", value="share"),
                app_commands.Choice(name="Keep separate", value="private"),
            ]
        )
        async def sharing(
            interaction: discord.Interaction, setting: app_commands.Choice[str] | None = None
        ) -> None:
            if setting is None:
                current = self.db.get_sharing(interaction.user.id)
                state = {True: "shared across servers", False: "kept separate", None: "kept separate (not set)"}[current]
                await interaction.response.send_message(
                    f"Your scores are currently **{state}**.", ephemeral=True
                )
                return
            self.db.set_sharing(interaction.user.id, setting.value == "share")
            await interaction.response.send_message(
                "✅ Your scores will show on every server you share with this bot."
                if setting.value == "share"
                else "👍 Your scores will show only on the server where you post them.",
                ephemeral=True,
            )

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

        name = message.author.display_name
        quote = quote_annotation(result.annotation)
        no_pings = discord.AllowedMentions.none()  # a comment must never ping anyone
        posted_any = False
        repeats: list[str] = []

        # Post first, delete second: if posting fails the original is still there.
        for share in result.shares:
            if not share.is_new:
                repeats.append(f"{share.game.title} {share.game.puzzle_label(share.score.puzzle)}")
                continue
            guild, game = message.guild, share.game
            view = LeaderboardView(lambda scope, g=guild, gm=game: board_for(self.db, g, gm, scope))
            title, entries = view.title, view.entries
            content = f"**{name}** · {share.score.display()}"
            if quote and not posted_any:  # their comment travels with the first new score
                content += f"\n{quote}"
            view.message = await message.channel.send(
                content,
                embed=board_embed(title, entries, 0),
                view=view,
                allowed_mentions=no_pings,
            )
            posted_any = True

        if quote and not posted_any:  # every score was a repeat: still keep what they wrote
            await message.channel.send(
                f"**{name}**\n{quote}", allowed_mentions=no_pings
            )
        if repeats:
            await message.channel.send(
                f"{message.author.mention}, you already posted {', '.join(repeats)}.",
                delete_after=10,
            )

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning("Missing Manage Messages in #%s; could not delete score", message.channel)
        except discord.NotFound:
            pass

        await self._maybe_ask_to_share(message)

    async def _maybe_ask_to_share(self, message: discord.Message) -> None:
        """Ask once, the first time someone who is in 2+ of our servers posts a score."""
        user_id = message.author.id
        if not self.db.needs_share_prompt(user_id) or self.mutual_server_count(user_id) < 2:
            return
        self.db.mark_prompted(user_id)  # ask only once, even if they ignore it
        view = SharePromptView(self.db, user_id)
        view.message = await message.channel.send(
            f"{message.author.mention}, you're in more than one server that uses this bot. "
            "Want your scores to show on the leaderboards of those other servers too? "
            "Only you can answer. Otherwise they stay on the server where you post them. "
            "You can change this any time with `/sharing`.",
            view=view,
        )
