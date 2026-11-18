"""SQLite storage: one row per (guild, user, game, puzzle)."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    user_name  TEXT    NOT NULL,
    game       TEXT    NOT NULL,
    puzzle     INTEGER NOT NULL,
    total      INTEGER NOT NULL,
    display    TEXT    NOT NULL,
    created_at REAL    NOT NULL,
    PRIMARY KEY (guild_id, user_id, game, puzzle)
);
CREATE INDEX IF NOT EXISTS idx_scores_lookup ON scores (guild_id, game, puzzle);
"""


@dataclass(frozen=True)
class Entry:
    """One leaderboard line."""

    name: str
    value: str  # already formatted for display, e.g. "365" or "412.5 avg · 8 plays"


class Database:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def add_score(
        self,
        *,
        guild_id: int,
        user_id: int,
        user_name: str,
        game: str,
        puzzle: int,
        total: int,
        display: str,
    ) -> bool:
        """Store a score. Returns False if this user already has one for that puzzle."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, user_name, game, puzzle, total, display, time.time()),
        )
        self.conn.commit()
        return cur.rowcount == 1

    def latest_puzzle(self, guild_id: int, game: str) -> int | None:
        row = self.conn.execute(
            "SELECT MAX(puzzle) FROM scores WHERE guild_id = ? AND game = ?",
            (guild_id, game),
        ).fetchone()
        return row[0]

    def puzzle_board(
        self, guild_id: int, game: str, puzzle: int, *, higher_is_better: bool
    ) -> list[Entry]:
        order = "DESC" if higher_is_better else "ASC"
        rows = self.conn.execute(
            f"SELECT user_name, total FROM scores "
            f"WHERE guild_id = ? AND game = ? AND puzzle = ? "
            f"ORDER BY total {order}, created_at ASC",
            (guild_id, game, puzzle),
        ).fetchall()
        return [Entry(name, str(total)) for name, total in rows]

    def all_time_board(
        self, guild_id: int, game: str, *, higher_is_better: bool
    ) -> list[Entry]:
        """Ranked by average score. The name shown is the user's most recent one."""
        order = "DESC" if higher_is_better else "ASC"
        rows = self.conn.execute(
            f"SELECT user_name, AVG(total) AS avg_total, COUNT(*), MAX(created_at) "
            f"FROM scores WHERE guild_id = ? AND game = ? "
            f"GROUP BY user_id ORDER BY avg_total {order}, COUNT(*) DESC",
            (guild_id, game),
        ).fetchall()
        return [
            Entry(name, f"{avg:.1f} avg · {n} play{'s' if n != 1 else ''}")
            for name, avg, n, _ in rows
        ]
