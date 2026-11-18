"""Parser for MapTap share text.

Format:
    www.maptap.gg November 17
    94🏅 92🏆 100🎯 91👑 90👑
    Final score: 929

Five rounds out of 100 each. The final score is out of 1,000, so the rounds are weighted
(later rounds count more). The weights below (1, 1, 2, 3, 3) reproduce the one real
sample we have exactly, but they are inferred, not documented, so the check allows a
small tolerance and should be tightened or corrected if more samples disagree.

There is no puzzle number, only a date with no year. The puzzle id is the date's ordinal,
with the year inferred from today's date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

ROUND_WEIGHTS = (1, 1, 2, 3, 3)
MAX_SCORE = 100 * sum(ROUND_WEIGHTS)  # 1000
TOLERANCE = 5  # allowed gap between the posted and the weighted-sum final score

_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
_MONTH_NUMBER = {name: i + 1 for i, name in enumerate(_MONTHS)}
_MONTH_NUMBER.update({name[:3]: i + 1 for i, name in enumerate(_MONTHS)})
_MONTH_ABBR = [name[:3].title() for name in _MONTHS]

_HEADER = re.compile(r"^(?:https?://)?(?:www\.)?maptap\.gg\s+([A-Za-z]+)\s+(\d{1,2})$", re.IGNORECASE)
_ROUND = re.compile(r"^(\d{1,3})[^\w\s]*$")  # a number, then optional emoji
_FINAL = re.compile(r"^Final score:\s*(\d{1,5})$", re.IGNORECASE)


def puzzle_label(puzzle: int) -> str:
    """Human label for a puzzle id (a date ordinal), e.g. 'Nov 17'."""
    d = date.fromordinal(puzzle)
    return f"{_MONTH_ABBR[d.month - 1]} {d.day}"


@dataclass(frozen=True)
class MapTapScore:
    puzzle: int  # date ordinal
    total: int
    rounds: tuple[int, ...]

    @property
    def detail(self) -> str:
        return ""

    def display(self) -> str:
        rounds = " ".join(str(r) for r in self.rounds)
        return f"MapTap · {puzzle_label(self.puzzle)} · {self.total:,} · {rounds}"


def _resolve_date(month: int, day: int, today: date) -> date | None:
    """Pick the year for a month/day with no year: this year, unless that's in the future."""
    try:
        candidate = date(today.year, month, day)
        if candidate > today + timedelta(days=1):  # 1 day of slack for timezones
            candidate = date(today.year - 1, month, day)
        return candidate
    except ValueError:  # e.g. Feb 29 in a non-leap year, or day out of range
        return None


def parse(text: str, today: date | None = None) -> MapTapScore | None:
    today = today or date.today()
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) != 3:
        return None

    header = _HEADER.match(lines[0])
    final = _FINAL.match(lines[2])
    tokens = lines[1].split()
    if not header or not final or len(tokens) != len(ROUND_WEIGHTS):
        return None

    month = _MONTH_NUMBER.get(header.group(1).lower())
    if month is None:
        return None
    puzzle_date = _resolve_date(month, int(header.group(2)), today)
    if puzzle_date is None:
        return None

    rounds: list[int] = []
    for token in tokens:
        match = _ROUND.match(token)
        if not match or int(match.group(1)) > 100:
            return None
        rounds.append(int(match.group(1)))

    total = int(final.group(1))
    expected = sum(w * r for w, r in zip(ROUND_WEIGHTS, rounds, strict=True))
    if total > MAX_SCORE or abs(total - expected) > TOLERANCE:
        return None

    return MapTapScore(puzzle=puzzle_date.toordinal(), total=total, rounds=tuple(rounds))
