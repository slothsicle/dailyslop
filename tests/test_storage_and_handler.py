import pytest

from dailyslop.db import Database, Entry
from dailyslop.handler import handle_message
from dailyslop.leaderboard import page_count, render_page

K125_365 = "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮"
K125_190 = "Krillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐟"
K126_385 = "Krillion #126 🦐\n385\n\n🦑🏮🦑⬛🦑🦑🦑"


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def post(db, user_id, name, text, guild_id=1):
    return handle_message(db, guild_id=guild_id, user_id=user_id, user_name=name, text=text)


def test_new_score_is_stored(db):
    result = post(db, 10, "ann", K125_365)
    assert result.is_new
    assert result.game.key == "krillion"
    assert db.latest_puzzle(1, "krillion") == 125


def test_duplicate_is_not_stored_twice_and_keeps_first_score(db):
    assert post(db, 10, "ann", K125_365).is_new
    assert not post(db, 10, "ann", K125_190).is_new  # same user, same puzzle
    board = db.puzzle_board(1, "krillion", 125, higher_is_better=True)
    assert board == [Entry("ann", "365")]


def test_unparseable_text_is_ignored_and_stores_nothing(db):
    assert post(db, 10, "ann", "good morning everyone") is None
    assert post(db, 10, "ann", "Krillion #125 🦐\n999\n\n🦑🦑🐟🫧🦑🦑🏮") is None  # bad sum
    assert db.latest_puzzle(1, "krillion") is None


def test_puzzle_board_orders_best_first(db):
    post(db, 10, "ann", K125_190)
    post(db, 11, "bob", K125_365)
    names = [e.name for e in db.puzzle_board(1, "krillion", 125, higher_is_better=True)]
    assert names == ["bob", "ann"]
    names = [e.name for e in db.puzzle_board(1, "krillion", 125, higher_is_better=False)]
    assert names == ["ann", "bob"]


def test_boards_are_per_guild(db):
    post(db, 10, "ann", K125_365, guild_id=1)
    assert db.puzzle_board(2, "krillion", 125, higher_is_better=True) == []
    assert db.latest_puzzle(2, "krillion") is None


def test_all_time_board_averages_across_puzzles(db):
    post(db, 10, "ann", K125_365)
    post(db, 10, "ann", K126_385)
    post(db, 11, "bob", K125_190)
    board = db.all_time_board(1, "krillion", higher_is_better=True)
    assert board == [Entry("ann", "375.0 avg · 2 plays"), Entry("bob", "190.0 avg · 1 play")]


def test_data_survives_reopening_the_file(tmp_path):
    path = tmp_path / "nested" / "slop.db"
    first = Database(path)
    post(first, 10, "ann", K125_365)
    first.close()
    second = Database(path)
    assert second.latest_puzzle(1, "krillion") == 125
    second.close()


def test_render_page_empty():
    assert "No scores" in render_page([], 0)


def test_render_page_paginates_and_clamps():
    entries = [Entry(f"u{i}", str(100 - i)) for i in range(1, 26)]
    assert page_count(entries) == 3
    first = render_page(entries, 0)
    assert first.splitlines()[0].startswith("🥇") and "u10" in first and "u11" not in first
    last = render_page(entries, 2)
    assert "`21.`" in last and "u25" in last
    assert render_page(entries, 99) == last  # clamped
    assert render_page(entries, -5) == first
