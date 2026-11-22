"""Turn stored scores into one server's leaderboard. No Discord code here."""

from __future__ import annotations

import time
from collections.abc import Collection, Mapping
from dataclasses import dataclass
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


def daily_puzzles(
    db: Database, guild_id: int, game: Game, member_ids: Collection[int]
) -> list[int]:
    """Every puzzle this server's board has a score for, newest first."""
    return sorted({s.puzzle for s in visible_scores(db, guild_id, game.key, member_ids)}, reverse=True)


def build_board(
    db: Database,
    guild_id: int,
    game: Game,
    scope: str,
    member_ids: Collection[int],
    names: Mapping[int, str] | None = None,
    now: float | None = None,
    puzzle: int | None = None,
) -> tuple[str, list[Entry]]:
    """Return (title, entries) for one server. scope is one of SCOPES.

    daily    `puzzle` if given (the bot's auto-posts pass the puzzle just pasted, so a player
             in a timezone ahead doesn't hide the day everyone else is still on), otherwise
             the most recent puzzle anyone has a score for (raw totals; Krillion adds its emoji)
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

    shown = latest_puzzle if puzzle is None else puzzle
    today = [s for s in scores if s.puzzle == shown]
    today.sort(key=lambda s: (sign * s.total, s.created_at))
    entries = [
        Entry(names.get(s.user_id, s.user_name), _value(s.total, s.detail), s.extra)
        for s in today
    ]
    return f"{game.title} {game.puzzle_label(shown)}", entries


# --- records -----------------------------------------------------------------------------

RECORD_SCOPES = ("all-time", "monthly", "weekly")  # biggest first: only the biggest is announced
# A record only counts once the window already holds this many earlier puzzle days, so the
# 2nd of the month (or a brand-new server) doesn't hand out "monthly record" for beating one day.
MIN_RECORD_PUZZLES = 3


@dataclass(frozen=True)
class Record:
    scope: str  # one of RECORD_SCOPES
    label: str  # how the period reads in a sentence: "this week", "November", "all-time"
    previous: int  # the best total before this score
    holders: tuple[int, ...] = ()  # server records: who held `previous` (never the scorer)


@dataclass(frozen=True)
class Records:
    server: Record | None = None
    personal: Record | None = None  # None when a server record already says as much


def _beaten(mine: Score, others: list[Score], sign: int) -> int | None:
    """The previous best that `mine` strictly beats, or None (a tie is not a record)."""
    if len({s.puzzle for s in others}) < MIN_RECORD_PUZZLES:
        return None
    best = min(sign * s.total for s in others)
    return sign * best if sign * mine.total < best else None


def find_records(
    db: Database,
    guild_id: int,
    game: Game,
    user_id: int,
    puzzle: int,
    member_ids: Collection[int],
    now: float | None = None,
) -> Records:
    """Did this user's stored score for `puzzle` set a single-day best on this server's board?

    Windows match the boards: weekly = the last 7 puzzle days, monthly = the UTC month the
    score was posted in, all-time = everything. Only the biggest window is reported, for the
    server and for the player; a personal best is dropped if a server record of the same or a
    bigger window already covers it. Server holders are limited to current members.
    """
    members = set(member_ids)
    scores = visible_scores(db, guild_id, game.key, members)
    mine = next((s for s in scores if s.user_id == user_id and s.puzzle == puzzle), None)
    if mine is None:
        return Records()
    sign = -1 if game.higher_is_better else 1
    current = datetime.fromtimestamp(time.time() if now is None else now, UTC)
    latest_puzzle = max(s.puzzle for s in scores)

    def window(scope: str) -> list[Score]:
        if scope == "weekly":
            return [s for s in scores if s.puzzle > latest_puzzle - WEEK_PUZZLES]
        if scope == "monthly":
            return [
                s
                for s in scores
                if (d := datetime.fromtimestamp(s.created_at, UTC)).year == current.year
                and d.month == current.month
            ]
        return scores

    labels = {"weekly": "this week", "monthly": f"{current:%B}", "all-time": "all-time"}
    server = personal = None
    for scope in RECORD_SCOPES:
        rows = window(scope)
        if mine not in rows:
            continue
        others = [s for s in rows if s is not mine]
        if server is None and (prev := _beaten(mine, others, sign)) is not None:
            holders = sorted(
                {s.user_id for s in others if s.total == prev and s.user_id != user_id}
                & members
            )
            server = Record(scope, labels[scope], prev, tuple(holders))
        own = [s for s in others if s.user_id == user_id]
        if personal is None and (prev := _beaten(mine, own, sign)) is not None:
            personal = Record(scope, labels[scope], prev)
    if server and personal and (
        RECORD_SCOPES.index(personal.scope) >= RECORD_SCOPES.index(server.scope)
    ):
        personal = None
    return Records(server, personal)
