"""Parser for NYT Connections share text.

Format (from the game's share button; not yet checked against real posts here):
    Connections
    Puzzle #512
    🟨🟩🟨🟨
    🟨🟨🟨🟨         <- one row per guess; a row of one colour is a solved group
    🟩🟩🟩🟩
    🟦🟦🟦🟦
    🟪🟪🟪🟪

Four wrong guesses end the game. Score = number of guesses (4 is perfect, 7 is the most a win
can take); a failed game counts as 8. Fewer is better. The rows must be consistent with a
finished game (each colour solved at most once, at most 4 wrong guesses, and either all four
groups solved or exactly four wrong guesses), otherwise the post is left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

COLOURS = set("🟨🟩🟦🟪")
GROUPS = 4
MAX_MISTAKES = 4
FAIL_TOTAL = 8
MISTAKE = "❌"
MAX_ROWS = 7  # a win with 3 mistakes, or a fail with 4 mistakes and 3 groups solved

_HEADER = re.compile(r"^Connections$")
_PUZZLE = re.compile(r"^Puzzle\s+#([\d,]+)$")


@dataclass(frozen=True)
class ConnectionsScore:
    puzzle: int
    total: int  # guesses made, or 8 for a fail
    solved_groups: int
    path: str = ""  # one mark per guess: the group's colour if solved, ❌ for a mistake

    @property
    def won(self) -> bool:
        return self.solved_groups == GROUPS

    @property
    def detail(self) -> str:
        if not self.won:
            return f"failed · {self.solved_groups}/{GROUPS} groups"
        return "perfect" if self.total == GROUPS else ""

    @property
    def extra(self) -> str:
        return self.path  # shown on the daily board

    def display(self) -> str:
        if not self.won:
            result = f"failed ({self.solved_groups}/{GROUPS})"
        else:
            result = "perfect" if self.total == GROUPS else f"{self.total} guesses"
        return f"Connections #{self.puzzle:,} · {result}"


def _row(line: str) -> str | None:
    chars = "".join(ch for ch in line if not ch.isspace() and ch != "️")
    if len(chars) != GROUPS or any(ch not in COLOURS for ch in chars):
        return None
    return chars


def parse(text: str) -> ConnectionsScore | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not 2 + GROUPS <= len(lines) <= 2 + MAX_ROWS:
        return None
    if not _HEADER.match(lines[0]):
        return None
    puzzle = _PUZZLE.match(lines[1])
    if not puzzle:
        return None

    rows = [_row(ln) for ln in lines[2:]]
    if any(r is None for r in rows):
        return None
    guesses = [r for r in rows if r is not None]

    solved = [r[0] for r in guesses if len(set(r)) == 1]
    mistakes = len(guesses) - len(solved)
    if len(set(solved)) != len(solved) or mistakes > MAX_MISTAKES:
        return None
    if mistakes < MAX_MISTAKES and len(solved) != GROUPS:
        return None  # not a finished game
    if mistakes == MAX_MISTAKES and (len(solved) == GROUPS or len(set(guesses[-1])) == 1):
        return None  # the game ends on the 4th mistake

    won = len(solved) == GROUPS
    return ConnectionsScore(
        puzzle=int(puzzle.group(1).replace(",", "")),
        total=len(guesses) if won else FAIL_TOTAL,
        solved_groups=len(solved),
        path="".join(r[0] if len(set(r)) == 1 else MISTAKE for r in guesses),
    )
