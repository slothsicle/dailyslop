"""New single-day bests for the week / month / all-time, per server and per player."""

from datetime import UTC, datetime

import pytest

from dailyslop.boards import MIN_RECORD_PUZZLES, Record, Records, find_records
from dailyslop.db import Database
from dailyslop.games import GAMES

K = GAMES["krillion"]
W = GAMES["wordle"]
G, OTHER = 1, 2
ANN, BOB, CY = 10, 11, 12
MEMBERS = {ANN, BOB, CY}
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC).timestamp()


def ts(m, d):
    return datetime(2026, m, d, 12, tzinfo=UTC).timestamp()


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def add(db, user, puzzle, total, when=NOW, game="krillion", guild=G):
    db.add_score(
        guild_id=guild, user_id=user, user_name=f"u{user}", game=game, puzzle=puzzle,
        total=total, display=f"{game} #{puzzle} · {total}",
    )
    db.conn.execute(
        "UPDATE scores SET created_at = ? WHERE user_id = ? AND puzzle = ? AND game = ?",
        (when, user, puzzle, game),
    )


def records(db, user, puzzle, game=K, members=MEMBERS):
    return find_records(db, G, game, user, puzzle, members, NOW)


def history(db):
    """Three earlier November days: Bob holds the best (500), Ann's best is 300."""
    for p, (a, b) in zip((100, 101, 102), ((200, 500), (300, 400), (250, 450)), strict=True):
        add(db, ANN, p, a, ts(11, 14 + p - 100))
        add(db, BOB, p, b, ts(11, 14 + p - 100))


def test_min_puzzles_is_three():
    assert MIN_RECORD_PUZZLES == 3


def test_all_time_server_record_pings_the_old_holder(db):
    history(db)
    add(db, ANN, 103, 600)
    assert records(db, ANN, 103) == Records(server=Record("all-time", "all-time", 500, (BOB,)))


def test_tie_is_not_a_record(db):
    history(db)
    add(db, ANN, 103, 500)
    r = records(db, ANN, 103)
    assert r.server is None
    assert r.personal == Record("all-time", "all-time", 300)  # still her own best


def test_personal_best_without_server_record(db):
    history(db)
    add(db, ANN, 103, 350)
    assert records(db, ANN, 103) == Records(personal=Record("all-time", "all-time", 300))


def test_beating_your_own_server_record_pings_nobody(db):
    history(db)
    add(db, BOB, 103, 650)
    assert records(db, BOB, 103) == Records(server=Record("all-time", "all-time", 500, ()))


def test_not_enough_history_means_no_record(db):
    add(db, ANN, 100, 200)
    add(db, BOB, 100, 300)
    add(db, ANN, 101, 400)
    assert records(db, ANN, 101) == Records()


def test_monthly_record_when_all_time_is_held_earlier(db):
    for p in (90, 91, 92):  # October: Cy's 690 stands all-time
        add(db, CY, p, 690, ts(10, p - 80))
    history(db)
    add(db, ANN, 103, 600)
    r = records(db, ANN, 103)
    assert r.server == Record("monthly", "November", 500, (BOB,))
    # Her three November days are all she has ever played, so it is also her all-time best.
    assert r.personal == Record("all-time", "all-time", 300)


def test_personal_scope_bigger_than_server_scope_is_kept(db):
    for p in (90, 91, 92):
        add(db, CY, p, 690, ts(10, p - 80))
        add(db, ANN, p, 100, ts(10, p - 80))
    history(db)
    add(db, ANN, 103, 600)
    r = records(db, ANN, 103)
    assert r.server == Record("monthly", "November", 500, (BOB,))
    assert r.personal == Record("all-time", "all-time", 300)


def test_personal_scope_same_as_server_is_dropped(db):
    history(db)
    add(db, ANN, 103, 600)
    assert records(db, ANN, 103).personal is None


def test_weekly_window_is_seven_puzzle_days(db):
    for p in range(100, 110):
        add(db, BOB, p, 300, ts(11, 1))
    add(db, CY, 100, 700, ts(11, 1))  # outside the last 7 puzzles once 110 is in
    add(db, ANN, 110, 400)
    r = records(db, ANN, 110)
    assert r.server == Record("weekly", "this week", 300, (BOB,))


def test_lower_is_better_games(db):
    for p in (1000, 1001, 1002):
        add(db, BOB, p, 3, game="wordle", when=ts(11, 1))
    add(db, ANN, 1003, 2, game="wordle")
    assert records(db, ANN, 1003, W).server == Record("all-time", "all-time", 3, (BOB,))


def test_tied_holders_are_all_pinged_but_not_ex_members(db):
    history(db)
    add(db, CY, 101, 500, ts(11, 15))
    add(db, ANN, 103, 600)
    assert records(db, ANN, 103).server.holders == (BOB, CY)
    assert records(db, ANN, 103, members={ANN, BOB}).server.holders == (BOB,)


def test_other_servers_private_scores_do_not_count(db):
    history(db)
    add(db, CY, 100, 700, guild=OTHER)
    add(db, ANN, 103, 600)
    assert records(db, ANN, 103).server.previous == 500


def test_unknown_score_gives_nothing(db):
    history(db)
    assert records(db, CY, 103) == Records()
