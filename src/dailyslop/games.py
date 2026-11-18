"""Registry of supported games. Adding a game = add its parser module and one entry here."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dailyslop.parsers import krillion


@dataclass(frozen=True)
class Game:
    key: str  # stable id stored in the database
    title: str
    # parse(text) -> object with .puzzle, .total and .display(), or None if not this game
    parse: Callable[[str], Any | None]
    higher_is_better: bool


GAMES: dict[str, Game] = {
    "krillion": Game("krillion", "Krillion", krillion.parse, higher_is_better=True),
}
