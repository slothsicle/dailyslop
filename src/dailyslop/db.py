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
    detail: str = ""  # extra text shown next to the total, e.g. "beat 71%"
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
            # Krillion's emoji were only ever stored inside `display`
            # ("Krillion #126 · 375 · 🐟🦑..."), so recover them for the scores already there.
            rows = self.conn.execute(
                "SELECT rowid, display FROM scores WHERE game = 'krillion'"
            ).fetchall()
            for rowid, display in rows:
                parts = display.split(" · ")
                if len(parts) == 3:
                    self.conn.execute("UPDATE scores SET extra = ? WHERE rowid = ?", (parts[2], rowid))
        self.conn.commit()

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
        """Store a score. Returns False if it's a duplicate.

        Users who share across servers get one score per puzzle everywhere; everyone
        else gets one per puzzle per server.
        """
        if self.get_sharing(user_id):
            exists = self.conn.execute(
                "SELECT 1 FROM scores WHERE user_id = ? AND game = ? AND puzzle = ?",
                (user_id, game, puzzle),
            ).fetchone()
            if exists:
                return False
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO scores "
            "(guild_id, user_id, user_name, game, puzzle, total, display, created_at, detail, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, user_name, game, puzzle, total, display, time.time(), detail, extra),
        )
        self.conn.commit()
        return cur.rowcount == 1

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
