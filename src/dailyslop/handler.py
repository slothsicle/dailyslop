"""Discord-free core: turn message text into a stored score."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dailyslop.db import Database
from dailyslop.games import GAMES, Game


@dataclass(frozen=True)
class Handled:
    game: Game
    score: Any  # the parser's result: .puzzle, .total, .display()
    is_new: bool  # False if this user already posted this puzzle


def handle_message(
    db: Database, *, guild_id: int, user_id: int, user_name: str, text: str
) -> Handled | None:
    """Return None if the text isn't a score we can fully parse (message must be left alone)."""
    text = text.strip()
    for game in GAMES.values():
        score = game.parse(text)
        if score is None:
            continue
        is_new = db.add_score(
            guild_id=guild_id,
            user_id=user_id,
            user_name=user_name,
            game=game.key,
            puzzle=score.puzzle,
            total=score.total,
            display=score.display(),
            detail=score.detail,
        )
        return Handled(game, score, is_new)
    return None
