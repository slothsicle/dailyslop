"""Parser for Chainle share text.

Format:
    Chainle #90 · 2,837
    Beat 71% of players

    https://chainle.io/

Five rounds of up to 1,000 points each, so the total is at most 5,000 (stated on
chainle.org). The site shows no share text, so the format above comes from a real post. Its
link said chainle.io while the game's site is chainle.org, so the link line accepts either.
Posts may also carry per-round emoji; those don't matter, so any extra line with no letters
or digits is ignored. Anything else unexpected makes the post unparseable, and the bot
leaves it alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_SCORE = 5000

# The score can be followed by decorative symbols (real posts end the line with 🔗).
_HEADER = re.compile(
    r"^Chainle\s+#(\d+)\s*[·•|\-]\s*(\d{1,3}(?:,\d{3})+|\d+)\s*[^\w\s]*$", re.IGNORECASE
)
_BEAT = re.compile(r"^Beat\s+(\d{1,3})%\s+of\s+players$", re.IGNORECASE)
_URL = re.compile(r"^https?://(?:www\.)?chainle\.(?:org|io)/?\S*$", re.IGNORECASE)


@dataclass(frozen=True)
class ChainleScore:
    puzzle: int
    total: int
    percentile: int  # "beat N% of players"

    @property
    def detail(self) -> str:
        return f"beat {self.percentile}%"

    def display(self) -> str:
        return f"Chainle #{self.puzzle} · {self.total:,} · {self.detail}"


def _ignorable(line: str) -> bool:
    """The share link, or a line of pure emoji/symbols (the per-round squares).

    Real posts sometimes put the squares and the link on one line with no space between
    them, so any leading symbols are dropped before checking for the link.
    """
    if not any(ch.isalnum() for ch in line):
        return True
    return bool(_URL.match(re.sub(r"^[^\w]+", "", line)))


def parse(text: str) -> ChainleScore | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None

    header = _HEADER.match(lines[0])
    if not header:
        return None

    percentile = None
    for line in lines[1:]:
        beat = _BEAT.match(line)
        if beat and percentile is None:
            percentile = int(beat.group(1))
        elif not _ignorable(line):
            return None  # unexpected text: not a clean share
    if percentile is None or percentile > 100:
        return None

    total = int(header.group(2).replace(",", ""))
    if total > MAX_SCORE:
        return None

    return ChainleScore(puzzle=int(header.group(1)), total=total, percentile=percentile)
