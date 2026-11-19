"""SQLite storage.

`scores` has one row per (server, user, game, puzzle): the server where it was pasted.
`prefs` holds each user's cross-server sharing choice. Who sees a score on which
leaderboard is decided at read time (see boards.py), so changing a preference needs no
data migration.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

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
    detail     TEXT    NOT NULL DEFAULT '',
    extra      TEXT    NOT NULL DEFAULT '',
    PRIMARY KEY (guild_id, user_id, game, puzzle)
);
CREATE INDEX IF NOT EXISTS idx_scores_lookup ON scores (guild_id, game, puzzle);
CREATE INDEX IF NOT EXISTS idx_scores_user ON scores (user_id, game, puzzle);

-- The bot's own leaderboard post for each (channel, game, puzzle), so the next one can
-- replace it. Old rows are harmless; they are only looked up by that exact key.
CREATE TABLE IF NOT EXISTS posts (
    channel_id INTEGER NOT NULL,
    game       TEXT    NOT NULL,
    puzzle     INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    PRIMARY KEY (channel_id, game, puzzle)
);

CREATE TABLE IF NOT EXISTS prefs (
    user_id  INTEGER PRIMARY KEY,
    sharing  INTEGER,                      -- NULL = undecided, 0 = private, 1 = share
    prompted INTEGER NOT NULL DEFAULT 0    -- 1 once we've asked them
);
"""


@dataclass(frozen=True)
class Score:
    guild_id: int  # server where it was pasted
    user_id: int
    user_name: str  # display name at the time of posting
    puzzle: int
    total: int
    created_at: float
    detail: str = ""  # extra text shown next to the total, e.g. Chainle's "71%"
    extra: str = ""  # shown only on a single day's board, e.g. Krillion's emoji row


class Database:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Bring databases created by older versions up to date."""
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(scores)")}
        if "detail" not in columns:  # added in v0.2
            self.conn.execute("ALTER TABLE scores ADD COLUMN detail TEXT NOT NULL DEFAULT ''")
        if "extra" not in columns:  # added with the daily Krillion emoji
            self.conn.execute("ALTER TABLE scores ADD COLUMN extra TEXT NOT NULL DEFAULT ''")
        self._backfill_extra()
        # Chainle used to store "beat 71%"; it is now just "71%". Idempotent.
        self.conn.execute(
            "UPDATE scores SET detail = substr(detail, 6) "
            "WHERE game = 'chainle' AND detail LIKE 'beat %'"
        )
        self.conn.commit()

    # Games whose `extra` was only ever stored inside `display` ("Krillion #126 · 375 · 🐟🦑...",
    # "MapTap · Nov 17 · 929 · 94 92 100 91 90"): game -> (segments in display, index of extra).
    _EXTRA_IN_DISPLAY: ClassVar[dict[str, tuple[int, int]]] = {"krillion": (3, 2), "maptap": (4, 3)}

    def _backfill_extra(self) -> None:
        """Recover `extra` for scores stored before a game had one. Safe to run every start:
        it only touches rows whose extra is still empty."""
        for game, (segments, index) in self._EXTRA_IN_DISPLAY.items():
            rows = self.conn.execute(
                "SELECT rowid, display FROM scores WHERE game = ? AND extra = ''", (game,)
            ).fetchall()
            for rowid, display in rows:
                parts = display.split(" · ")
                if len(parts) == segments:
                    self.conn.execute(
                        "UPDATE scores SET extra = ? WHERE rowid = ?", (parts[index], rowid)
                    )

    def close(self) -> None:
        self.conn.close()

    # --- preferences ---------------------------------------------------------

    def get_sharing(self, user_id: int) -> bool | None:
        """True = share across servers, False = keep private, None = never answered."""
        row = self.conn.execute(
            "SELECT sharing FROM prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return bool(row[0])

    def set_sharing(self, user_id: int, share: bool) -> None:
        self.conn.execute(
            "INSERT INTO prefs (user_id, sharing, prompted) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET sharing = excluded.sharing, prompted = 1",
            (user_id, int(share)),
        )
        self.conn.commit()

    def needs_share_prompt(self, user_id: int) -> bool:
        """True if we've never asked this user and they haven't set a preference."""
        row = self.conn.execute(
            "SELECT sharing, prompted FROM prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is None or (row[0] is None and not row[1])

    def mark_prompted(self, user_id: int) -> None:
        self.conn.execute(
            "INSERT INTO prefs (user_id, sharing, prompted) VALUES (?, NULL, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET prompted = 1",
            (user_id,),
        )
        self.conn.commit()

    # --- scores --------------------------------------------------------------

    def _shares_everywhere(self, user_id: int) -> bool:
        return bool(self.get_sharing(user_id))

    def find_score(self, *, guild_id: int, user_id: int, game: str, puzzle: int) -> Score | None:
        """The score that blocks a new paste: this user's stored score for the puzzle.

        Users who share across servers have one per puzzle everywhere (latest wins);
        everyone else one per server.
        """
        where = "user_id = ? AND game = ? AND puzzle = ?"
        args: tuple = (user_id, game, puzzle)
        if not self._shares_everywhere(user_id):
            where += " AND guild_id = ?"
            args += (guild_id,)
        row = self.conn.execute(
            "SELECT guild_id, user_id, user_name, puzzle, total, created_at, detail, extra "
            f"FROM scores WHERE {where} ORDER BY created_at DESC LIMIT 1",
            args,
        ).fetchone()
        return Score(*row) if row else None

    def _insert(self, *, guild_id, user_id, user_name, game, puzzle, total, display, detail, extra):
        return self.conn.execute(
            "INSERT OR IGNORE INTO scores "
            "(guild_id, user_id, user_name, game, puzzle, total, display, created_at, detail, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, user_name, game, puzzle, total, display, time.time(), detail, extra),
        )

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
        detail: str = "",
        extra: str = "",
    ) -> bool:
        """Store a score. Returns False if it's a duplicate (use replace_score to overwrite)."""
        if self.find_score(guild_id=guild_id, user_id=user_id, game=game, puzzle=puzzle):
            return False
        cur = self._insert(
            guild_id=guild_id, user_id=user_id, user_name=user_name, game=game, puzzle=puzzle,
            total=total, display=display, detail=detail, extra=extra,
        )
        self.conn.commit()
        return cur.rowcount == 1

    def replace_score(
        self,
        *,
        guild_id: int,
        user_id: int,
        user_name: str,
        game: str,
        puzzle: int,
        total: int,
        display: str,
        detail: str = "",
        extra: str = "",
    ) -> None:
        """Overwrite this user's score for a puzzle, in one transaction.

        A user who shares across servers has their old copy deleted from *every* server;
        a leftover copy could still be the one a board shows.
        """
        with self.conn:
            if self._shares_everywhere(user_id):
                self.conn.execute(
                    "DELETE FROM scores WHERE user_id = ? AND game = ? AND puzzle = ?",
                    (user_id, game, puzzle),
                )
            else:
                self.conn.execute(
                    "DELETE FROM scores WHERE guild_id = ? AND user_id = ? AND game = ? "
                    "AND puzzle = ?",
                    (guild_id, user_id, game, puzzle),
                )
            self._insert(
                guild_id=guild_id, user_id=user_id, user_name=user_name, game=game,
                puzzle=puzzle, total=total, display=display, detail=detail, extra=extra,
            )

    def swap_post(self, channel_id: int, game: str, puzzle: int, message_id: int) -> int | None:
        """Record the bot's newest board post for this channel/game/puzzle.
        Returns the previous one's message id (for the caller to delete), if any."""
        with self.conn:
            row = self.conn.execute(
                "SELECT message_id FROM posts WHERE channel_id = ? AND game = ? AND puzzle = ?",
                (channel_id, game, puzzle),
            ).fetchone()
            self.conn.execute(
                "INSERT INTO posts (channel_id, game, puzzle, message_id) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(channel_id, game, puzzle) DO UPDATE SET message_id = excluded.message_id",
                (channel_id, game, puzzle, message_id),
            )
        return row[0] if row else None

    def newest_puzzle(self, game: str) -> tuple[int, float] | None:
        """The highest puzzle stored for a game and when it first appeared (earliest paste),
        or None if the game has no scores yet. Used to sanity-check new puzzle numbers."""
        row = self.conn.execute(
            "SELECT puzzle, MIN(created_at) FROM scores WHERE game = ? "
            "AND puzzle = (SELECT MAX(puzzle) FROM scores WHERE game = ?)",
            (game, game),
        ).fetchone()
        return (row[0], row[1]) if row and row[0] is not None else None

    def latest_post_ids(self, channel_id: int) -> set[int]:
        """The bot's current board posts in a channel: the newest puzzle of each game.
        Everything else it posted there is history that /purge may delete."""
        rows = self.conn.execute(
            "SELECT message_id FROM posts p WHERE channel_id = ? AND puzzle = "
            "(SELECT MAX(puzzle) FROM posts WHERE channel_id = p.channel_id AND game = p.game)",
            (channel_id,),
        ).fetchall()
        return {row[0] for row in rows}

    def forget_posts(self, channel_id: int, keep: set[int]) -> None:
        """Drop the bookkeeping for every post in the channel except the ones in `keep`."""
        rows = self.conn.execute(
            "SELECT message_id FROM posts WHERE channel_id = ?", (channel_id,)
        ).fetchall()
        with self.conn:
            for (message_id,) in rows:
                if message_id not in keep:
                    self.conn.execute("DELETE FROM posts WHERE message_id = ?", (message_id,))

    def candidate_scores(self, guild_id: int, game: str) -> list[Score]:
        """Scores that *might* belong on this server's board: those pasted here, plus
        those from users who opted in to sharing. The caller still has to check that
        shared users are actually members here (see boards.py)."""
        rows = self.conn.execute(
            "SELECT guild_id, user_id, user_name, puzzle, total, created_at, detail, extra FROM scores "
            "WHERE game = ? AND (guild_id = ? OR user_id IN "
            "(SELECT user_id FROM prefs WHERE sharing = 1))",
            (game, guild_id),
        ).fetchall()
        return [Score(*row) for row in rows]
