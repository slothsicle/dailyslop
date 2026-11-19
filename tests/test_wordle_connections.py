"""Wordle and Connections. The samples follow the games' share format as documented; they have
not (yet) been checked against real posts from this server, so treat a rejected real post as
a parser bug to fix, not as proof the format is wrong."""

import pytest

from dailyslop.games import GAMES
from dailyslop.handler import find_shares
from dailyslop.parsers import connections, wordle

W3 = "Wordle 1,234 3/6\n\n⬛🟨⬛⬛⬛\n🟨⬛🟩⬛⬛\n🟩🟩🟩🟩🟩"
W_FAIL = "Wordle 1,234 X/6\n\n" + "\n".join(["⬛🟨⬛⬛🟩"] * 6)
W_HARD = "Wordle 1,234 2/6*\n⬛🟨⬛⬛⬛\n🟩🟩🟩🟩🟩"
W_HUNDRED = "Wordle 999 1/6\n🟩🟩🟩🟩🟩"

C_PERFECT = "Connections\nPuzzle #512\n🟨🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪"
C_TWO_MISSES = (
    "Connections\nPuzzle #512\n🟨🟩🟨🟨\n🟨🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟪🟦🟦\n🟦🟦🟦🟦\n🟪🟪🟪🟪"
)
C_FAIL = "Connections\nPuzzle #512\n🟨🟨🟨🟨\n🟩🟦🟩🟩\n🟦🟪🟦🟦\n🟩🟩🟪🟩\n🟪🟦🟪🟪"


# --- Wordle ------------------------------------------------------------------------------


def test_wordle_solved():
    s = wordle.parse(W3)
    assert (s.puzzle, s.total, s.solved, s.hard) == (1234, 3, True, False)
    assert s.display() == "Wordle #1,234 · 3/6" and s.detail == ""


def test_wordle_hard_mode_and_small_numbers():
    s = wordle.parse(W_HARD)
    assert (s.total, s.hard) == (2, True) and s.display().endswith("2/6*") and s.detail == "hard"
    assert wordle.parse(W_HUNDRED).puzzle == 999


def test_wordle_fail_counts_as_seven():
    s = wordle.parse(W_FAIL)
    assert (s.total, s.solved) == (7, False)
    assert s.display() == "Wordle #1,234 · X/6" and s.detail == "failed"


@pytest.mark.parametrize(
    "text",
    [
        "Wordle 1,234 3/6\n⬛🟨⬛⬛⬛\n🟩🟩🟩🟩🟩",  # header says 3 guesses, grid has 2
        "Wordle 1,234 2/6\n⬛🟨⬛⬛⬛\n⬛🟩🟩🟩🟩",  # says solved, last row isn't green
        "Wordle 1,234 3/6\n🟩🟩🟩🟩🟩\n⬛🟨⬛⬛⬛\n🟩🟩🟩🟩🟩",  # solved before the last row
        "Wordle 1,234 X/6\n" + "\n".join(["⬛🟨⬛⬛⬛"] * 5),  # a fail needs 6 rows
        "Wordle 1,234 X/6\n" + "\n".join(["⬛🟨⬛⬛⬛"] * 5 + ["🟩🟩🟩🟩🟩"]),  # fail, but won
        "Wordle 1,234 3/6\n⬛🟨⬛⬛\n🟨⬛🟩⬛⬛\n🟩🟩🟩🟩🟩",  # a 4-square row
        "Wordle 1,234 7/6\n🟩🟩🟩🟩🟩",
        "Wordle 1,234 3/6",  # no grid
        "Wordle 1,234 1/6 lol\n🟩🟩🟩🟩🟩",
        "wordle is fun",
    ],
)
def test_wordle_rejects_anything_inconsistent(text):
    assert wordle.parse(text) is None


# --- Connections -----------------------------------------------------------------------------


def test_connections_perfect():
    s = connections.parse(C_PERFECT)
    assert (s.puzzle, s.total, s.solved_groups, s.won) == (512, 4, 4, True)
    assert s.detail == "perfect" and s.display() == "Connections #512 · perfect"


def test_connections_win_with_mistakes_counts_every_guess():
    s = connections.parse(C_TWO_MISSES)
    assert (s.total, s.won, s.detail) == (6, True, "")
    assert s.display() == "Connections #512 · 6 guesses"


def test_connections_fail_after_four_mistakes():
    s = connections.parse(C_FAIL)
    assert (s.total, s.solved_groups, s.won) == (8, 1, False)
    assert s.detail == "failed · 1/4 groups" and s.display() == "Connections #512 · failed (1/4)"


@pytest.mark.parametrize(
    "text",
    [
        "Connections\nPuzzle #512\n🟨🟨🟨🟨\n🟩🟩🟩🟩",  # unfinished game
        "Connections\nPuzzle #512\n🟨🟨🟨🟨\n🟨🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪",  # colour solved twice
        "Connections\nPuzzle #512\n" + "🟨🟩🟨🟨\n" * 5 + "🟨🟨🟨🟨",  # five mistakes
        "Connections\nPuzzle #512\n🟨🟨🟨🟨\n🟩🟦🟩🟩\n🟦🟪🟦🟦\n🟩🟩🟪🟩\n🟪🟦🟪🟪\n🟪🟪🟪🟪",  # plays on after losing
        "Connections\nPuzzle #512\n🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪",  # a 3-square row
        "Connections\n🟨🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪",  # no puzzle number
        "Connections #512\n🟨🟨🟨🟨\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪",
    ],
)
def test_connections_rejects_anything_inconsistent(text):
    assert connections.parse(text) is None


# --- registry / handler integration --------------------------------------------------------


def test_registry_ranks_fewest_guesses_first():
    assert not GAMES["wordle"].higher_is_better and not GAMES["connections"].higher_is_better


@pytest.mark.parametrize(
    ("text", "key"),
    [(W3, "wordle"), (C_PERFECT, "connections"), ("nice one!\n" + W3, "wordle")],
)
def test_handler_finds_them_even_with_a_comment(text, key):
    shares, _ = find_shares(text)
    assert shares[0][0].key == key


def test_a_backslash_escapes_both():
    assert find_shares("\\" + W3) is None
    assert find_shares("\\" + C_PERFECT) is None
    assert find_shares("hi\n\\" + C_PERFECT) is None


def test_wordle_and_connections_in_one_message():
    shares, note = find_shares(W3 + "\n\n" + C_PERFECT)
    assert [g.key for g, _ in shares] == ["wordle", "connections"] and note == ""


def test_lowest_guess_count_tops_the_board(tmp_path):
    from dailyslop.boards import build_board
    from dailyslop.db import Database

    db = Database()
    for uid, total in ((1, 4), (2, 3), (3, 7)):
        db.add_score(guild_id=1, user_id=uid, user_name=f"u{uid}", game="wordle", puzzle=9,
                     total=total, display="x", detail="failed" if total == 7 else "")
    _, entries = build_board(db, 1, GAMES["wordle"], "daily", {1, 2, 3})
    assert [(e.name, e.value) for e in entries] == [
        ("u2", "3"), ("u1", "4"), ("u3", "7 · failed")
    ]
