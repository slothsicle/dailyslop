"""Parser for Wordle share text (NYT).

Format (from the game's share button; not yet checked against real posts here):
    Wordle 1,234 3/6        <- puzzle number (comma after 1,000), guesses/6, `*` = hard mode
    ⬛🟨⬛⬛⬛
    🟨⬛🟩⬛⬛
    🟩🟩🟩🟩🟩           <- one row per guess, 5 squares each

`X/6` means the puzzle wasn't solved. Fewer guesses is better; a fail counts as 7.
The grid has to agree with the header (one row per guess, last row all green if and only if
it was solved), otherwise the post is treated as unparseable and left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SQUARES = set("🟩🟨⬛⬜🟦🟧")  # incl. light-mode and colour-blind palettes
GREENS = {"🟩", "🟧"}  # "right letter, right place" (🟧 is the colour-blind green)
FAIL_TOTAL = 7

_HEADER = re.compile(r"^Wordle\s+([\d,.]+)\s+([1-6X])/6(\*?)$")


@dataclass(frozen=True)
class WordleScore:
    puzzle: int
    total: int  # guesses, or 7 for a fail
    solved: bool
    hard: bool
    greens: tuple[int, ...] = ()  # green squares in each guess, in order
    rows: tuple[str, ...] = ()  # the pasted grid, one string of squares per guess

    @property
    def detail(self) -> str:
        return " · ".join(p for p in ("failed" if not self.solved else "", "hard" if self.hard else "") if p)

    @property
    def extra(self) -> str:
        """One-line summary for the daily board (the full grid is too wide): greens per guess."""
        return "🟩 " + "·".join(str(g) for g in self.greens) if self.greens else ""

    @property
    def grid(self) -> str:
        """The original grid, shown above the board in the bot's post (never stored)."""
        return "\n".join(self.rows)

    def display(self) -> str:
        shown = f"{self.total}" if self.solved else "X"
        return f"Wordle #{self.puzzle:,} · {shown}/6{'*' if self.hard else ''}"


def _row(line: str) -> list[str] | None:
    chars = [ch for ch in line if not ch.isspace() and ch != "️"]
    if len(chars) != 5 or any(ch not in SQUARES for ch in chars):
        return None
    return chars


def parse(text: str) -> WordleScore | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2 or len(lines) > 7:
        return None
    header = _HEADER.match(lines[0])
    if not header:
        return None
    digits = re.sub(r"[,.]", "", header.group(1))
    if not digits.isdigit():
        return None

    rows = [_row(ln) for ln in lines[1:]]
    if any(r is None for r in rows):
        return None
    solved = header.group(2) != "X"
    guesses = int(header.group(2)) if solved else 6
    if len(rows) != guesses:
        return None
    won = [all(ch in GREENS for ch in r) for r in rows if r is not None]
    if solved != won[-1] or any(won[:-1]):
        return None

    return WordleScore(
        puzzle=int(digits),
        total=guesses if solved else FAIL_TOTAL,
        solved=solved,
        hard=header.group(3) == "*",
        greens=tuple(sum(ch in GREENS for ch in r) for r in rows if r is not None),
        rows=tuple("".join(r) for r in rows if r is not None),
    )
