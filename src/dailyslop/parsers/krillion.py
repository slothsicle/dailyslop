"""Parser for Krillion share text.

Format:
    Krillion #125 🦐
    365

    🦑🦑🐟🫧🦑🦑🏮

Each of the 7 emoji is a rarity tier worth a fixed number of points, and the posted
total must equal their sum. Anything that doesn't validate returns None so the bot
leaves the message alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TIER_POINTS: dict[str, int] = {
    "⬛": 0,  # miss
    "🫧": 10,  # Plankton
    "🐟": 30,  # Schooler
    "🦑": 60,  # Rare
    "🏮": 85,  # Deep Cut
    "🌟": 100,  # One in a Krillion
}

PROMPTS_PER_DAY = 7
MAX_SCORE = 100 * PROMPTS_PER_DAY

_HEADER = re.compile(r"Krillion\s+#(\d+)")
_TOTAL = re.compile(r"^\s*(\d+)\s*$")


@dataclass(frozen=True)
class KrillionScore:
    puzzle: int
    total: int
    emojis: str  # the 7 tier emoji, in order

    @property
    def detail(self) -> str:
        return ""  # nothing extra to show next to the total on a leaderboard

    @property
    def extra(self) -> str:
        return self.emojis  # shown on that day's board, not on aggregated ones

    def display(self) -> str:
        return f"Krillion #{self.puzzle} · {self.total} · {self.emojis}"


def _tier_emojis(line: str) -> list[str] | None:
    """Split a line into tier emoji, or None if it contains anything else."""
    chars: list[str] = []
    for ch in line.strip():
        if ch.isspace() or ch == "️":  # ignore whitespace / variation selectors
            continue
        if ch not in TIER_POINTS:
            return None
        chars.append(ch)
    return chars


def parse(text: str) -> KrillionScore | None:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) != 3:
        return None

    header = _HEADER.search(lines[0])
    total_match = _TOTAL.match(lines[1])
    if not header or not total_match:
        return None

    emojis = _tier_emojis(lines[2])
    if emojis is None or len(emojis) != PROMPTS_PER_DAY:
        return None

    total = int(total_match.group(1))
    if total > MAX_SCORE or sum(TIER_POINTS[e] for e in emojis) != total:
        return None

    return KrillionScore(puzzle=int(header.group(1)), total=total, emojis="".join(emojis))
