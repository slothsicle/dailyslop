"""Turn stored scores into one server's leaderboard. No Discord code here."""

from __future__ import annotations

import time
from collections.abc import Collection, Mapping
from datetime import UTC, datetime

from dailyslop.db import Database, Score
from dailyslop.games import Game
from dailyslop.leaderboard import Entry

SCOPES = ("daily", "weekly", "monthly", "all-time")
WEEK_PUZZLES = 7  # "weekly" = the last 7 puzzle days, not 7 calendar days


def visible_scores(
    db: Database, guild_id: int, game: str, member_ids: Collection[int]
) -> list[Score]:
    """Scores that belong on this server's board.

    A score shows if it was pasted in this server, or if its author opted in to sharing
    and is currently a member here. A user who has the same puzzle stored from several
    servers (possible if they shared only after posting) is counted once, with the latest paste winning.
    """
    members = set(member_ids)
    candidates = [
        s
        for s in db.candidate_scores(guild_id, game)
        if s.guild_id == guild_id or s.user_id in members
    ]
    unique: dict[tuple[int, int], Score] = {}
    for score in sorted(candidates, key=lambda s: s.created_at, reverse=True):
        unique.setdefault((score.user_id, score.puzzle), score)
    return list(unique.values())


def _value(total: int, detail: str = "") -> str:
    text = f"{total:,}"
    return f"{text} · {detail}" if detail else text


def _average_entries(
    scores: list[Score], sign: int, names: Mapping[int, str]
) -> list[Entry]:
    """One line per player: their average over these scores. Best average first; on a tie,
    whoever played more, then by name."""
    by_user: dict[int, list[Score]] = {}
    for s in scores:
        by_user.setdefault(s.user_id, []).append(s)
    ranked = []
    for uid, rows in by_user.items():
        avg = sum(r.total for r in rows) / len(rows)
        latest = max(rows, key=lambda r: r.created_at)
        ranked.append((sign * avg, -len(rows), names.get(uid, latest.user_name), avg, len(rows)))
    ranked.sort(key=lambda r: r[:3])
    return [
        Entry(name, f"{avg:,.1f} avg · {n} play{'s' if n != 1 else ''}")
        for _, _, name, avg, n in ranked
    ]


def build_board(
    db: Database,
    guild_id: int,
    game: Game,
    scope: str,
    member_ids: Collection[int],
    names: Mapping[int, str] | None = None,
    now: float | None = None,
) -> tuple[str, list[Entry]]:
    """Return (title, entries) for one server. scope is one of SCOPES.

    daily    the most recent puzzle anyone has a score for (raw totals; Krillion adds its emoji)
    weekly   the last 7 puzzle days up to that puzzle, averaged
    monthly  scores posted this calendar month (UTC), averaged
    all-time everything, averaged

    `names` maps user id -> display name in *this* server; it overrides the name stored
    when the score was posted. `now` (unix time) exists for tests.
    """
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    names = names or {}
    scores = visible_scores(db, guild_id, game.key, member_ids)
    sign = -1 if game.higher_is_better else 1

    if scope == "all-time":
        return f"{game.title} · all-time", _average_entries(scores, sign, names)

    if scope == "monthly":
        current = datetime.fromtimestamp(time.time() if now is None else now, UTC)
        this_month = [
            s
            for s in scores
            if (d := datetime.fromtimestamp(s.created_at, UTC)).year == current.year
            and d.month == current.month
        ]
        return f"{game.title} · {current:%B %Y}", _average_entries(this_month, sign, names)

    if not scores:
        title = f"{game.title} · {'last 7 days' if scope == 'weekly' else 'today'}"
        return title, []
    latest_puzzle = max(s.puzzle for s in scores)

    if scope == "weekly":
        window = [s for s in scores if s.puzzle > latest_puzzle - WEEK_PUZZLES]
        return f"{game.title} · last 7 days", _average_entries(window, sign, names)

    today = [s for s in scores if s.puzzle == latest_puzzle]
    today.sort(key=lambda s: (sign * s.total, s.created_at))
    entries = [
        Entry(names.get(s.user_id, s.user_name), _value(s.total, s.detail), s.extra)
        for s in today
    ]
    return f"{game.title} {game.puzzle_label(latest_puzzle)}", entries
