"""Leaderboard text rendering and paging. No Discord code here."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

PAGE_SIZE = 5
# Column budget for a board's first line (rank + name + total), so it fits on a phone without
# wrapping. The name gets whatever the total column leaves, within these limits.
LINE_BUDGET = 34
NAME_MIN = 8
NAME_MAX = 20
RANK_COLUMNS = 4  # " 1. "
GAP_COLUMNS = 2
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


@dataclass(frozen=True)
class Entry:
    """One leaderboard line."""

    name: str
    value: str  # already formatted for display, e.g. "365" or "412.5 avg · 8 plays"
    extra: str = ""  # shown last, only on single-day boards (Krillion's emoji row)


def page_count(entries: list[Entry], page_size: int = PAGE_SIZE) -> int:
    return max(1, -(-len(entries) // page_size))


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0  # accents, variation selectors, joiners take no room of their own
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def text_width(text: str) -> int:
    """Columns the text takes up in a monospace font (CJK and emoji count as 2)."""
    return sum(_char_width(ch) for ch in text)


def fit_name(name: str, width: int = NAME_MAX) -> str:
    """Shorten a display name to at most `width` columns, ending in … if it was cut."""
    name = name.replace("`", "'").replace("\n", " ").strip()
    if text_width(name) <= width:
        return name
    out, used = "", 0
    for ch in name:
        w = _char_width(ch)
        if used + w > width - 1:
            break
        out, used = out + ch, used + w
    return out + "…"


def _pad(text: str, width: int, *, right: bool = False) -> str:
    gap = " " * max(0, width - text_width(text))
    return gap + text if right else text + gap


def _render_table(entries: list[Entry], start: int) -> str:
    """Monospace table: rank, name and total lined up on one line, with the extra (emoji,
    round scores...) on a second line underneath. Keeping them apart means a long row of
    emoji can't wrap awkwardly on a narrow screen."""
    value_w = max(text_width(e.value) for e in entries)
    room = LINE_BUDGET - RANK_COLUMNS - GAP_COLUMNS - value_w
    names = [fit_name(e.name, max(NAME_MIN, min(NAME_MAX, room))) for e in entries]
    name_w = max(text_width(n) for n in names)
    indent = " " * 4  # lines the extra up under the name
    lines = []
    for rank, (entry, name) in enumerate(zip(entries, names, strict=True), start=start + 1):
        lines.append(
            f"{rank:>2}. {_pad(name, name_w)}  {_pad(entry.value, value_w, right=True)}".rstrip()
        )
        if entry.extra:
            lines.append(indent + entry.extra)
    return "```\n" + "\n".join(lines) + "\n```"


def render_page(entries: list[Entry], page: int, page_size: int = PAGE_SIZE) -> str:
    """Render one page (0-indexed; out-of-range pages are clamped)."""
    if not entries:
        return "_No scores yet._"
    page = min(max(page, 0), page_count(entries, page_size) - 1)
    start = page * page_size
    shown = entries[start : start + page_size]
    if any(e.extra for e in shown):
        return _render_table(shown, start)
    lines = []
    for rank, entry in enumerate(shown, start=start + 1):
        marker = MEDALS.get(rank, f"`{rank}.`")
        lines.append(f"{marker} **{entry.name}** · {entry.value}")
    return "\n".join(lines)


def quote_annotation(text: str, limit: int = 400) -> str:
    """Format a person's comment as a Discord quote, shortened if it's long."""
    text = text.strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return "\n".join(f"> {line}" for line in text.splitlines())
