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
          'Chainle #90 · 2,837', 1.0, 'beat 71%');
        INSERT INTO scores VALUES (1, 10, 'ann', 'maptap', 738000, 929,
          'MapTap · Nov 17 · 929 · 94 92 100 91 90', 1.0, '');"""
    )
    conn.commit()
    conn.close()
    db = Database(path)
    assert board(db, "daily")[1] == [Entry("ann", "365", EMOJI)]
    maptap = db.conn.execute("SELECT extra FROM scores WHERE game = 'maptap'").fetchone()[0]
    chainle = db.conn.execute("SELECT extra FROM scores WHERE game = 'chainle'").fetchone()[0]
    assert (maptap, chainle) == ("94 92 100 91 90", "")
    db.close()
    Database(path).close()  # migrating twice is harmless


def test_a_database_that_already_has_the_column_still_gets_maptap_rounds_back(tmp_path):
    """The server migrated before MapTap had an extra; the next start must fill it in."""
    path = tmp_path / "mid.db"
    first = Database(path)  # current schema, so the column already exists
    first.conn.execute(
        "INSERT INTO scores (guild_id, user_id, user_name, game, puzzle, total, display, "
        "created_at, detail, extra) VALUES (1, 10, 'ann', 'maptap', 738000, 929, "
        "'MapTap · Nov 17 · 929 · 94 92 100 91 90', 1.0, '', '')"
    )
    first.conn.commit()
    first.close()
    second = Database(path)
    assert second.conn.execute("SELECT extra FROM scores").fetchone()[0] == "94 92 100 91 90"
    second.close()


def test_maptap_daily_board_shows_the_rounds():
    from dailyslop.parsers.maptap import parse

    db = Database()
    from datetime import date

    s = parse("www.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑 90👑\nFinal score: 929",
              today=date(2026, 11, 17))
    db.add_score(guild_id=1, user_id=10, user_name="ann", game="maptap", puzzle=s.puzzle,
                 total=s.total, display=s.display(), extra=s.extra)
    title, entries = build_board(db, 1, GAMES["maptap"], "daily", {10})
    assert title == "MapTap Nov 17" and entries == [Entry("ann", "929", "94 92 100 91 90")]
    assert build_board(db, 1, GAMES["maptap"], "all-time", {10})[1][0].extra == ""


# --- rendering ---------------------------------------------------------------------------------


def test_boards_with_extras_put_them_on_a_second_line_under_the_name():
    entries = [Entry("Alice", "385", "🦑🏮🦑⬛🦑🦑🦑"), Entry("Bo", "1,200", "🐟🐟🐟🐟🐟🫧🐟")]
    out = render_page(entries, 0).splitlines()
    assert out[0] == out[-1] == "```"
    assert out[1:5] == [
        " 1. Alice    385",
        "    🦑🏮🦑⬛🦑🦑🦑",
        " 2. Bo     1,200",
        "    🐟🐟🐟🐟🐟🫧🐟",
    ]
    assert out[1].index("385") + 3 == out[3].index("1,200") + 5  # totals end in the same column


def test_an_entry_without_an_extra_gets_no_second_line():
    out = render_page([Entry("Alice", "385", "🦑"), Entry("Bo", "300")], 0).splitlines()
    assert out[1:4] == [" 1. Alice  385", "    🦑", " 2. Bo     300"]


def test_long_and_wide_names_are_cut_so_lines_stay_short():
    assert fit_name("a" * 40) == "a" * 19 + "…"  # NAME_MAX = 20
    assert fit_name("a" * 40, 12) == "a" * 11 + "…"
    assert fit_name("Alice") == "Alice"
    cjk = fit_name("日本語のとても長い名前です", 12)
    assert text_width(cjk) <= 12 and cjk.endswith("…")
    assert "`" not in fit_name("we`ird")


def test_boards_without_emoji_keep_the_medal_layout():
    out = render_page([Entry("Alice", "385"), Entry("Bo", "300")], 0)
    assert out == "🥇 **Alice** · 385\n🥈 **Bo** · 300"


def test_names_get_more_room_when_the_total_column_is_narrow():
    long_name = "Bartholomew Featherstonehaugh"
    short = render_page([Entry(long_name, "375", "🐟")], 0).splitlines()[1]
    wide = render_page([Entry(long_name, "2,837 · 71%", "🟥")], 0).splitlines()[1]
    assert short.startswith(" 1. Bartholomew Feather")  # roomy: Krillion-sized totals
    assert len(wide.split("…")[0]) < len(short.split("…")[0])  # Chainle's is tighter


def test_a_first_line_never_exceeds_the_budget_unless_the_name_floor_forces_it():
    from dailyslop.leaderboard import LINE_BUDGET, NAME_MIN

    for value in ("375", "1,000", "2,837 · 71%"):
        line = render_page([Entry("x" * 60, value, "🟥")], 0).splitlines()[1]
        assert text_width(line) <= max(LINE_BUDGET, 4 + NAME_MIN + 2 + len(value))


def test_old_chainle_details_lose_the_word_beat_and_stay_that_way(tmp_path):
    path = tmp_path / "chainle.db"
    db = Database(path)
    for uid, detail in ((1, "beat 71%"), (2, "20%")):
        db.conn.execute(
            "INSERT INTO scores (guild_id, user_id, user_name, game, puzzle, total, display, "
            "created_at, detail) VALUES (1, ?, 'x', 'chainle', 90, 1000, 'd', 1.0, ?)",
            (uid, detail),
        )
    db.conn.execute(  # another game's detail must never be touched
        "INSERT INTO scores (guild_id, user_id, user_name, game, puzzle, total, display, "
        "created_at, detail) VALUES (1, 3, 'x', 'wordle', 9, 3, 'd', 1.0, 'beat this')"
    )
    db.conn.commit()
    db.close()
    for _ in range(2):  # twice: harmless
        again = Database(path)
        rows = dict(again.conn.execute("SELECT user_id, detail FROM scores"))
        assert rows == {1: "71%", 2: "20%", 3: "beat this"}
        again.close()
