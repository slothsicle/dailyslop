"""Parser for Farflung share text.

Format:
    Farflung #46 · 205/500 km
    Common · Common · Miss · Uncommon · Rare
    https://farflung.game/s/7hv642?e=46

Five rounds, each a rarity word worth fixed points: Farflung 100, Elusive 85, Rare 70,
Uncommon 55, Common 40, Miss 0. The posted total must equal their sum, otherwise the post is unparseable. The share has
no emoji yet, so each word is shown as a distance-themed emoji of the same rank (🏠 to 🛸). The link line
is optional; any other text makes the post unparseable and the bot leaves it alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TIER_POINTS: dict[str, int] = {
    "miss": 0,
    "common": 40,
    "uncommon": 55,
    "rare": 70,
    "elusive": 85,
    "farflung": 100,
}

# Our own stand-ins, closer to home when common and farther out when rare, until the game has its own.
TIER_EMOJI: dict[str, str] = {
    "miss": "⬛",
    "common": "🏠",
    "uncommon": "🚗",
    "rare": "✈️",
    "elusive": "🚀",
    "farflung": "🛸",
}

ROUNDS = 5
MAX_SCORE = 100 * ROUNDS

_HEADER = re.compile(
    r"^Farflung\s+#(\d+)\s*[·•|\-]\s*(\d+)\s*/\s*(\d+)(?:\s*km)?\s*$", re.IGNORECASE
)
_SEPARATOR = re.compile(r"\s*[·•|,]\s*")
_URL = re.compile(r"^https?://(?:www\.)?farflung\.game/\S*$", re.IGNORECASE)


@dataclass(frozen=True)
class FarflungScore:
    puzzle: int
    total: int
    emojis: str  # one tier emoji per round

    @property
    def detail(self) -> str:
        return ""

    @property
    def extra(self) -> str:
        return self.emojis  # shown on that day's board, not on aggregated ones

    def display(self) -> str:
        return f"Farflung #{self.puzzle} · {self.total} · {self.emojis}"


def parse(text: str) -> FarflungScore | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) not in (2, 3):
        return None
    if len(lines) == 3 and not _URL.match(lines[2]):
        return None

    header = _HEADER.match(lines[0])
    if not header or int(header.group(3)) != MAX_SCORE:
        return None

    tiers = [t.lower() for t in _SEPARATOR.split(lines[1])]
    if len(tiers) != ROUNDS or any(t not in TIER_POINTS for t in tiers):
        return None

    total = int(header.group(2))
    if sum(TIER_POINTS[t] for t in tiers) != total:
        return None

    return FarflungScore(
        puzzle=int(header.group(1)),
        total=total,
        emojis="".join(TIER_EMOJI[t] for t in tiers),
    )
