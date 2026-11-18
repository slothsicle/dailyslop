"""Turn stored scores into one server's leaderboard. No Discord code here."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from dailyslop.db import Database, Score
from dailyslop.games import Game
from dailyslop.leaderboard import Entry


def visible_scores(
    db: Database, guild_id: int, game: str, member_ids: Collection[int]
) -> list[Score]:
    """Scores that belong on this server's board.

    A score shows if it was pasted in this server, or if its author opted in to sharing
    and is currently a member here. A user who has the same puzzle stored from several
    servers (possible if they shared only after posting) is counted once, earliest first.
    """
    members = set(member_ids)
    candidates = [
        s
        for s in db.candidate_scores(guild_id, game)
        if s.guild_id == guild_id or s.user_id in members
    ]
    unique: dict[tuple[int, int], Score] = {}
    for score in sorted(candidates, key=lambda s: s.created_at):
        unique.setdefault((score.user_id, score.puzzle), score)
    return list(unique.values())


def _value(total: int, detail: str = "") -> str:
    text = f"{total:,}"
    return f"{text} · {detail}" if detail else text


def build_board(
    db: Database,
    guild_id: int,
    game: Game,
    scope: str,
    member_ids: Collection[int],
    names: Mapping[int, str] | None = None,
) -> tuple[str, list[Entry]]:
    """Return (title, entries) for one server. scope is 'today' or 'all-time'.

    `names` maps user id -> display name in *this* server; it overrides the name stored
    when the score was posted.
    """
    names = names or {}
    scores = visible_scores(db, guild_id, game.key, member_ids)
    sign = -1 if game.higher_is_better else 1

    if scope == "all-time":
        by_user: dict[int, list[Score]] = {}
        for s in scores:
            by_user.setdefault(s.user_id, []).append(s)
        ranked = []
        for uid, rows in by_user.items():
            avg = sum(r.total for r in rows) / len(rows)
            latest = max(rows, key=lambda r: r.created_at)
            ranked.append((sign * avg, -len(rows), names.get(uid, latest.user_name), avg, len(rows)))
        ranked.sort(key=lambda r: r[:3])
        entries = [
            Entry(name, f"{avg:,.1f} avg · {n} play{'s' if n != 1 else ''}")
            for _, _, name, avg, n in ranked
        ]
        return f"{game.title} · all-time", entries

    if not scores:
        return f"{game.title} · today", []
    latest_puzzle = max(s.puzzle for s in scores)
    today = [s for s in scores if s.puzzle == latest_puzzle]
    today.sort(key=lambda s: (sign * s.total, s.created_at))
    entries = [
        Entry(names.get(s.user_id, s.user_name), _value(s.total, s.detail)) for s in today
    ]
    return f"{game.title} {game.puzzle_label(latest_puzzle)}", entries
