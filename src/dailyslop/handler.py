"""Discord-free core: turn message text into stored scores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dailyslop.db import Database
from dailyslop.games import GAMES, Game

# Safety valves: a message with this much going on is a conversation, not a score post,
# so we leave it alone instead of deleting it.
MAX_LINES = 30
MAX_ANNOTATION_CHARS = 500
ESCAPE = "\\"  # put this before a paste to make the bot ignore the message


@dataclass(frozen=True)
class Handled:
    game: Game
    score: Any  # the parser's result: .puzzle, .total, .detail, .display()
    is_new: bool  # False if this user already posted this puzzle


@dataclass(frozen=True)
class MessageResult:
    shares: list[Handled]  # every score found, in order
    annotation: str  # whatever else the person wrote (may be empty)


def _parse_window(lines: list[str]) -> tuple[Game, Any] | None:
    text = "\n".join(lines)
    for game in GAMES.values():
        score = game.parse(text)
        if score is not None:
            return game, score
    return None


def find_shares(text: str) -> tuple[list[tuple[Game, Any]], str] | None:
    """Find score blocks inside a message, even with comments around them.

    Returns (scores found, leftover text) or None if there's nothing safe to act on.
    Each parser stays strict about its own format; this only decides where a block starts
    and ends. Longer windows are tried first so a trailing link or squares line belongs to
    the share instead of being left behind as "comment".
    """
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines or len(lines) > MAX_LINES:
        return None
    if lines[0].startswith(ESCAPE):  # a backslash in front of the message opts out entirely
        return None

    consumed = [False] * len(lines)
    found: list[tuple[int, Game, Any]] = []
    progress = True
    while progress:
        progress = False
        for length in range(len(lines), 0, -1):
            for start in range(len(lines) - length + 1):
                end = start + length
                if any(consumed[start:end]):
                    continue
                parsed = _parse_window(lines[start:end])
                if parsed is not None:
                    for i in range(start, end):
                        consumed[i] = True
                    found.append((start, *parsed))
                    progress = True
                    break
            if progress:
                break

    if not found:
        return None
    # A backslash in front of a score block escapes it, like escaping markdown. The whole
    # message is left alone, not just that block.
    leftover = [ln for ln, used in zip(lines, consumed, strict=True) if not used]
    if any(lines[start].startswith(ESCAPE) for start, _, _ in found):
        return None
    # Some parsers don't even recognise an escaped block, so it shows up as leftover text.
    # A leftover line that begins with a backslash means the same thing.
    if any(ln.startswith(ESCAPE) for ln in leftover):
        return None
    annotation = "\n".join(leftover)
    if len(annotation) > MAX_ANNOTATION_CHARS:
        return None
    found.sort(key=lambda item: item[0])
    return [(game, score) for _, game, score in found], annotation


def handle_message(
    db: Database, *, guild_id: int, user_id: int, user_name: str, text: str
) -> MessageResult | None:
    """Store every score in the message. None means: not a score post, leave it alone."""
    extracted = find_shares(text)
    if extracted is None:
        return None
    shares, annotation = extracted

    handled = []
    for game, score in shares:
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
        handled.append(Handled(game, score, is_new))
    return MessageResult(handled, annotation)
