"""Leaderboard text rendering and paging. No Discord code here."""

from __future__ import annotations

from dataclasses import dataclass

PAGE_SIZE = 10
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


@dataclass(frozen=True)
class Entry:
    """One leaderboard line."""

    name: str
    value: str  # already formatted for display, e.g. "365" or "412.5 avg · 8 plays"


def page_count(entries: list[Entry], page_size: int = PAGE_SIZE) -> int:
    return max(1, -(-len(entries) // page_size))


def render_page(entries: list[Entry], page: int, page_size: int = PAGE_SIZE) -> str:
    """Render one page (0-indexed; out-of-range pages are clamped)."""
    if not entries:
        return "_No scores yet._"
    page = min(max(page, 0), page_count(entries, page_size) - 1)
    start = page * page_size
    lines = []
    for rank, entry in enumerate(entries[start : start + page_size], start=start + 1):
        marker = MEDALS.get(rank, f"`{rank}.`")
        lines.append(f"{marker} **{entry.name}** · {entry.value}")
    return "\n".join(lines)
