"""Weekly / monthly / all-time boards, the Krillion emoji, and how boards are laid out."""

import sqlite3
from datetime import UTC, datetime

import pytest

from dailyslop.boards import SCOPES, build_board
from dailyslop.db import Database
from dailyslop.games import GAMES
from dailyslop.leaderboard import Entry, fit_name, render_page, text_width

K = GAMES["krillion"]
G = 1
ANN, BOB, CY = 10, 11, 12
EMOJI = "🦑🦑🐟🫧🦑🦑🏮"  # 365


def ts(y, m, d, h=12):
    return datetime(y, m, d, h, tzinfo=UTC).timestamp()


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def add(db, user, puzzle, total, name=None, when=None, extra=EMOJI):
    db.add_score(
        guild_id=G, user_id=user, user_name=name or f"u{user}", game="krillion",
        puzzle=puzzle, total=total, display=f"Krillion #{puzzle} · {total}", extra=extra,
    )
    if when is not None:  # backdate
        db.conn.execute(
            "UPDATE scores SET created_at = ? WHERE user_id = ? AND puzzle = ?", (when, user, puzzle)
        )


def board(db, scope, now=None, members=(ANN, BOB, CY)):
    return build_board(db, G, K, scope, set(members), None, now)


def test_scopes_are_the_four_periods():
    assert SCOPES == ("daily", "weekly", "monthly", "all-time")


def test_unknown_scope_is_rejected(db):
    with pytest.raises(ValueError):
        board(db, "yearly")


# --- daily -------------------------------------------------------------------------------


def test_daily_is_the_latest_puzzle_and_keeps_the_emoji(db):
    add(db, ANN, 125, 100, extra="old")
    add(db, ANN, 126, 365)
    add(db, BOB, 126, 400, extra="🌟🌟🌟🌟⬛⬛⬛")
    title, entries = board(db, "daily")
    assert title == "Krillion #126"
    assert entries == [Entry("u11", "400", "🌟🌟🌟🌟⬛⬛⬛"), Entry("u10", "365", EMOJI)]


# --- weekly: the last 7 puzzle days, not calendar time ----------------------------------------


def test_weekly_is_the_last_seven_puzzles_averaged_without_emoji(db):
    add(db, ANN, 119, 700)  # 8th-latest puzzle: outside the window
    add(db, ANN, 120, 100)  # oldest puzzle inside the window (126 - 6)
    add(db, ANN, 126, 300)
    add(db, BOB, 126, 250)
    title, entries = board(db, "weekly")
    assert title == "Krillion · last 7 days"
    assert entries == [Entry("u11", "250.0 avg · 1 play"), Entry("u10", "200.0 avg · 2 plays")]
    assert all(e.extra == "" for e in entries)


def test_weekly_ignores_how_long_ago_the_puzzles_were_posted(db):
    add(db, ANN, 125, 100, when=ts(2020, 1, 1))
    add(db, ANN, 126, 300, when=ts(2020, 1, 2))
    _, entries = board(db, "weekly", now=ts(2026, 11, 18))
    assert entries == [Entry("u10", "200.0 avg · 2 plays")]


# --- monthly ---------------------------------------------------------------------------------


def test_monthly_is_the_calendar_month_in_utc_and_names_the_month(db):
    add(db, ANN, 100, 500, when=ts(2026, 10, 31, 23))  # last month
    add(db, ANN, 101, 300, when=ts(2026, 11, 1, 0))
    add(db, ANN, 102, 100, when=ts(2026, 11, 17))
    add(db, BOB, 102, 350, when=ts(2026, 12, 1, 0))  # next month: not counted yet
    title, entries = board(db, "monthly", now=ts(2026, 11, 18))
    assert title == "Krillion · November 2026"
    assert entries == [Entry("u10", "200.0 avg · 2 plays")]


def test_monthly_with_nothing_this_month_is_empty(db):
    add(db, ANN, 1, 300, when=ts(2026, 10, 3))
    assert board(db, "monthly", now=ts(2026, 11, 18))[1] == []


# --- all-time --------------------------------------------------------------------------------


def test_all_time_is_every_score_averaged_and_never_shows_emoji(db):
    add(db, ANN, 1, 100)
    add(db, ANN, 2, 200)
    add(db, BOB, 1, 400)
    title, entries = board(db, "all-time")
    assert title == "Krillion · all-time"
    assert entries == [Entry("u11", "400.0 avg · 1 play"), Entry("u10", "150.0 avg · 2 plays")]


def test_equal_averages_put_the_more_active_player_first(db):
    add(db, ANN, 1, 200)
    add(db, BOB, 1, 100)
    add(db, BOB, 2, 300)
    assert [e.name for e in board(db, "all-time")[1]] == ["u11", "u10"]


def test_lower_is_better_games_rank_the_smallest_average_first(db):
    from dataclasses import replace

    golf = replace(K, key="golf", higher_is_better=False)
    for uid, total in ((ANN, 5), (BOB, 3)):
        db.add_score(guild_id=G, user_id=uid, user_name=f"u{uid}", game="golf", puzzle=1,
                     total=total, display="x")
    _, entries = build_board(db, G, golf, "weekly", {ANN, BOB})
    assert [e.name for e in entries] == ["u11", "u10"]


# --- migration ---------------------------------------------------------------------------


def test_old_databases_get_their_krillion_emoji_back(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """CREATE TABLE scores (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL, game TEXT NOT NULL, puzzle INTEGER NOT NULL,
        total INTEGER NOT NULL, display TEXT NOT NULL, created_at REAL NOT NULL,
        detail TEXT NOT NULL DEFAULT '', PRIMARY KEY (guild_id, user_id, game, puzzle));
        INSERT INTO scores VALUES (1, 10, 'ann', 'krillion', 126, 365,
          'Krillion #126 · 365 · 🦑🦑🐟🫧🦑🦑🏮', 1.0, '');
        INSERT INTO scores VALUES (1, 10, 'ann', 'chainle', 90, 2837,
          'Chainle #90 · 2,837', 1.0, 'beat 71%');"""
    )
    conn.commit()
    conn.close()
    db = Database(path)
    assert board(db, "daily")[1] == [Entry("ann", "365", EMOJI)]
    db.close()
    Database(path).close()  # migrating twice is harmless


# --- rendering ---------------------------------------------------------------------------------


def test_boards_with_emoji_are_a_table_with_aligned_columns():
    entries = [Entry("Alice", "385", "🦑🏮🦑⬛🦑🦑🦑"), Entry("Bo", "1,200", "🐟🐟🐟🐟🐟🫧🐟")]
    out = render_page(entries, 0).splitlines()
    assert out[0] == out[-1] == "```"
    first, second = out[1], out[2]
    assert first.index("385") + 3 == second.index("1,200") + 5  # totals end in the same column
    assert first.index("🦑") == second.index("🐟")  # emoji start in the same column


def test_long_and_wide_names_are_cut_so_lines_stay_short():
    assert fit_name("a" * 40) == "a" * 11 + "…"
    assert fit_name("Alice") == "Alice"
    cjk = fit_name("日本語のとても長い名前です")
    assert text_width(cjk) <= 12 and cjk.endswith("…")
    assert "`" not in fit_name("we`ird")


def test_boards_without_emoji_keep_the_medal_layout():
    out = render_page([Entry("Alice", "385"), Entry("Bo", "300")], 0)
    assert out == "🥇 **Alice** · 385\n🥈 **Bo** · 300"
