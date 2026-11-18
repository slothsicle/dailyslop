"""Registry of supported games. Adding a game = add its parser module and one entry here."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dailyslop.parsers import chainle, krillion, maptap


def default_label(puzzle: int) -> str:
    return f"#{puzzle}"


@dataclass(frozen=True)
class Game:
    key: str  # stable id stored in the database
    title: str
    # parse(text) -> object with .puzzle, .total, .detail and .display(), or None
    parse: Callable[[str], Any | None]
    higher_is_better: bool
    # How a puzzle id is shown to people (e.g. "#125", or "Nov 17" for date-based games).
    puzzle_label: Callable[[int], str] = default_label


GAMES: dict[str, Game] = {
    "krillion": Game("krillion", "Krillion", krillion.parse, higher_is_better=True),
    "maptap": Game(
        "maptap", "MapTap", maptap.parse, higher_is_better=True, puzzle_label=maptap.puzzle_label
    ),
    "chainle": Game("chainle", "Chainle", chainle.parse, higher_is_better=True),
}
