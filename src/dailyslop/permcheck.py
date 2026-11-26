"""`/checkperms`: work out what the bot can and can't do in a channel, and why.

Discord-free apart from `discord.Permissions` (a plain bit set): bot.py computes the
permissions and passes them in, so this is testable without a server."""

from dataclasses import dataclass

import discord

# (Permissions attribute, name shown in Discord, what breaks without it)
NEEDED = (
    ("view_channel", "View Channel", "it can't see pastes here"),
    ("send_messages", "Send Messages", "it can't post the compact score"),
    ("embed_links", "Embed Links", "the leaderboard under each score won't show"),
    ("read_message_history", "Read Message History", "it can't find its old posts to tidy up"),
    ("manage_messages", "Manage Messages", "it can't delete the original paste"),
)
THREAD_SEND = ("send_messages_in_threads", "Send Messages in Threads")

# Above this share of members missing from the cache, the Server Members intent isn't working.
MEMBER_CACHE_MIN = 0.9


@dataclass(frozen=True)
class Finding:
    ok: bool
    label: str
    problem: str = ""  # what's wrong, when not ok
    fix: str = ""  # what to change, when not ok


def check_permissions(
    channel: discord.Permissions,
    server: discord.Permissions,
    *,
    thread: bool = False,
    timed_out: bool = False,
) -> list[Finding]:
    """One finding per needed permission.

    `channel` is what the bot actually has in this channel (roles and overrides applied);
    `server` is what its roles grant server-wide. Having it server-wide but not here means a
    channel or category override is taking it away."""
    findings: list[Finding] = []
    if timed_out:
        findings.append(
            Finding(
                False,
                "Timeout",
                "the bot is timed out, which removes almost all of its permissions",
                "remove the timeout from the bot (right-click it in the member list)",
            )
        )
    for attr, name, consequence in NEEDED:
        if thread and attr == "send_messages":
            attr, name = THREAD_SEND
            consequence = "it can't post the compact score"
        if getattr(channel, attr):
            findings.append(Finding(True, name))
        elif getattr(server, attr):
            findings.append(
                Finding(
                    False,
                    name,
                    f"denied here by a channel or category override, so {consequence}",
                    "in Channel Settings → Permissions (and the category's), make sure neither the "
                    f"bot nor its role is set to ✗ for {name}, and that @everyone isn't set to ✗ "
                    "unless the bot's own role is set to ✓",
                )
            )
        else:
            findings.append(
                Finding(
                    False,
                    name,
                    f"the bot's role doesn't have it, so {consequence}",
                    f"in Server Settings → Roles, give the bot's role {name} "
                    "(or re-invite the bot with the install link)",
                )
            )
    return findings


def check_members(cached: int, total: int) -> Finding:
    """The bot must know who is in the server to decide who appears on the board."""
    label = "Server Members"
    if total and cached < total * MEMBER_CACHE_MIN:
        return Finding(
            False,
            label,
            f"the bot only knows {cached} of {total} members, so some players may be left "
            "off the boards",
            "whoever runs the bot needs to turn on **Server Members Intent** in the Developer "
            "Portal (Bot tab) and restart it",
        )
    return Finding(True, label)


def render(where: str, findings: list[Finding]) -> str:
    bad = [f for f in findings if not f.ok]
    if not bad:
        return f"✅ Everything looks right in {where}. I can read, post, tidy up and delete pastes here."
    lines = [f"❌ {len(bad)} problem{'s' if len(bad) != 1 else ''} in {where}:", ""]
    for f in bad:
        lines.append(f"**{f.label}:** {f.problem}.")
        lines.append(f"↳ Fix: {f.fix}.")
    passed = [f.label for f in findings if f.ok]
    if passed:
        lines += ["", "✅ Fine: " + ", ".join(passed)]
    return "\n".join(lines)
