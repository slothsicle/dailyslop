"""Leaderboard text rendering and paging. No Discord code here."""

from __future__ import annotations

from dataclasses import dataclass

PAGE_SIZE = 5
EXTRA_INDENT = "\u2003\u2003"  # two em spaces: lines the extra up under the name
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


@dataclass(frozen=True)
class Entry:
    """One leaderboard line."""

    name: str
    value: str  # already formatted for display, e.g. "365" or "412.5 avg · 8 plays"
    extra: str = ""  # shown last, only on single-day boards (Krillion's emoji row)


def page_count(entries: list[Entry], page_size: int = PAGE_SIZE) -> int:
    return max(1, -(-len(entries) // page_size))


def render_page(entries: list[Entry], page: int, page_size: int = PAGE_SIZE) -> str:
    """Render one page (0-indexed; out-of-range pages are clamped).

    Each player is one line (rank, name, value); if they have an extra (emoji, round scores)
    it goes on a second line underneath so it can't wrap awkwardly on a narrow screen.
    """
    if not entries:
        return "_No scores yet._"
    page = min(max(page, 0), page_count(entries, page_size) - 1)
    start = page * page_size
    lines = []
    for rank, entry in enumerate(entries[start : start + page_size], start=start + 1):
        marker = MEDALS.get(rank, f"`{rank}.`")
        lines.append(f"{marker} **{entry.name}** · {entry.value}")
        if entry.extra:
            lines.append(EXTRA_INDENT + entry.extra)
    return "\n".join(lines)


def quote_annotation(text: str, limit: int = 400) -> str:
    """Format a person's comment as a Discord quote, shortened if it's long."""
    text = text.strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return "\n".join(f"> {line}" for line in text.splitlines())
