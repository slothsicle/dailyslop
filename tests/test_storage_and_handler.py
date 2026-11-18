import pytest

from dailyslop.boards import build_board
from dailyslop.db import Database
from dailyslop.games import GAMES
from dailyslop.handler import handle_message
from dailyslop.leaderboard import Entry, page_count, render_page

K125_365 = "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮"
K125_190 = "Krillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐟"
K126_385 = "Krillion #126 🦐\n385\n\n🦑🏮🦑⬛🦑🦑🦑"
KRILLION = GAMES["krillion"]

X, Y = 1, 2  # two servers
ANN, BOB = 10, 11


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def post(db, user_id, name, text, guild_id=X):
    return handle_message(db, guild_id=guild_id, user_id=user_id, user_name=name, text=text)


def board(db, guild_id, members, scope="today", names=None):
    return build_board(db, guild_id, KRILLION, scope, members, names)


# --- handler / parsing ------------------------------------------------------


def test_new_score_is_stored(db):
    result = post(db, ANN, "ann", K125_365)
    assert result.is_new and result.game.key == "krillion"
    assert board(db, X, {ANN}) == ("Krillion #125", [Entry("ann", "365")])


def test_unparseable_text_is_ignored_and_stores_nothing(db):
    assert post(db, ANN, "ann", "good morning everyone") is None
    assert post(db, ANN, "ann", "Krillion #125 🦐\n999\n\n🦑🦑🐟🫧🦑🦑🏮") is None  # bad sum
    assert board(db, X, {ANN}) == ("Krillion · today", [])


def test_duplicate_in_same_server_is_rejected_and_keeps_first_score(db):
    assert post(db, ANN, "ann", K125_365).is_new
    assert not post(db, ANN, "ann", K125_190).is_new
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]


# --- ordering and paging ----------------------------------------------------


def test_puzzle_board_orders_best_first(db):
    post(db, ANN, "ann", K125_190)
    post(db, BOB, "bob", K125_365)
    assert [e.name for e in board(db, X, {ANN, BOB})[1]] == ["bob", "ann"]


def test_all_time_board_averages_across_puzzles(db):
    post(db, ANN, "ann", K125_365)
    post(db, ANN, "ann", K126_385)
    post(db, BOB, "bob", K125_190)
    _, entries = board(db, X, {ANN, BOB}, scope="all-time")
    assert entries == [Entry("ann", "375.0 avg · 2 plays"), Entry("bob", "190.0 avg · 1 play")]


def test_data_survives_reopening_the_file(tmp_path):
    path = tmp_path / "nested" / "slop.db"
    first = Database(path)
    post(first, ANN, "ann", K125_365)
    first.set_sharing(ANN, True)
    first.close()
    second = Database(path)
    assert board(second, X, {ANN})[1] == [Entry("ann", "365")]
    assert second.get_sharing(ANN) is True
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
    assert render_page(entries, 99) == last
    assert render_page(entries, -5) == first


# --- cross-server visibility ------------------------------------------------


def test_private_by_default_scores_stay_in_their_server(db):
    post(db, ANN, "ann", K125_365, guild_id=X)
    post(db, BOB, "bob", K125_190, guild_id=Y)
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]
    assert board(db, Y, {ANN, BOB})[1] == [Entry("bob", "190")]  # Ann is a member of Y, still hidden


def test_opted_in_user_shows_on_every_server_they_belong_to(db):
    """The scenario: A is in X and Y and posts in X; B is only in Y and posts in Y."""
    db.set_sharing(ANN, True)
    post(db, ANN, "ann", K125_365, guild_id=X)
    post(db, BOB, "bob", K125_190, guild_id=Y)
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]  # B is not in X
    assert board(db, Y, {ANN, BOB})[1] == [Entry("ann", "365"), Entry("bob", "190")]


def test_opted_in_user_does_not_show_where_they_are_not_a_member(db):
    db.set_sharing(ANN, True)
    post(db, ANN, "ann", K125_365, guild_id=X)
    assert board(db, Y, {BOB})[1] == []


def test_opting_out_hides_scores_from_other_servers_again(db):
    db.set_sharing(ANN, True)
    post(db, ANN, "ann", K125_365, guild_id=X)
    assert board(db, Y, {ANN})[1] == [Entry("ann", "365")]
    db.set_sharing(ANN, False)
    assert board(db, Y, {ANN})[1] == []
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]  # still on the server they posted in


def test_opting_in_later_includes_earlier_scores(db):
    post(db, ANN, "ann", K125_365, guild_id=X)
    assert board(db, Y, {ANN})[1] == []
    db.set_sharing(ANN, True)
    assert board(db, Y, {ANN})[1] == [Entry("ann", "365")]


def test_sharing_users_cannot_post_the_same_puzzle_twice_anywhere(db):
    db.set_sharing(ANN, True)
    assert post(db, ANN, "ann", K125_365, guild_id=X).is_new
    assert not post(db, ANN, "ann", K125_365, guild_id=Y).is_new


def test_private_users_can_post_the_same_puzzle_once_per_server(db):
    assert post(db, ANN, "ann", K125_365, guild_id=X).is_new
    assert post(db, ANN, "ann", K125_365, guild_id=Y).is_new
    assert not post(db, ANN, "ann", K125_365, guild_id=X).is_new


def test_same_puzzle_stored_in_two_servers_is_counted_once_after_opting_in(db):
    post(db, ANN, "ann", K125_365, guild_id=X)
    post(db, ANN, "ann", K125_365, guild_id=Y)
    db.set_sharing(ANN, True)
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]
    _, entries = board(db, Y, {ANN}, scope="all-time")
    assert entries == [Entry("ann", "365.0 avg · 1 play")]


def test_names_come_from_the_server_being_viewed(db):
    db.set_sharing(ANN, True)
    post(db, ANN, "ann-in-x", K125_365, guild_id=X)
    assert board(db, X, {ANN}, names={ANN: "Annie (X nick)"})[1] == [Entry("Annie (X nick)", "365")]
    assert board(db, Y, {ANN}, names={ANN: "Ann (Y nick)"})[1] == [Entry("Ann (Y nick)", "365")]
    assert board(db, Y, {ANN})[1] == [Entry("ann-in-x", "365")]  # falls back to stored name


def test_latest_puzzle_and_all_time_use_only_visible_scores(db):
    db.set_sharing(ANN, True)
    post(db, ANN, "ann", K126_385, guild_id=X)  # newest puzzle, Ann shared
    post(db, BOB, "bob", K125_190, guild_id=Y)
    assert board(db, Y, {BOB})[0] == "Krillion #125"  # Ann not a member of Y: #126 invisible
    assert board(db, Y, {ANN, BOB})[0] == "Krillion #126"
    _, entries = board(db, Y, {BOB}, scope="all-time")
    assert entries == [Entry("bob", "190.0 avg · 1 play")]


def test_other_servers_with_no_scores_have_empty_boards(db):
    post(db, ANN, "ann", K125_365, guild_id=X)
    assert board(db, 99, set()) == ("Krillion · today", [])


# --- the opt-in prompt ------------------------------------------------------


def test_prompt_is_needed_until_asked_or_answered(db):
    assert db.needs_share_prompt(ANN)
    db.mark_prompted(ANN)
    assert not db.needs_share_prompt(ANN)  # asked once, even if ignored
    assert db.get_sharing(ANN) is None  # ignoring leaves them private


def test_answering_the_prompt_records_the_choice(db):
    db.set_sharing(ANN, False)
    assert db.get_sharing(ANN) is False and not db.needs_share_prompt(ANN)
    db.set_sharing(ANN, True)
    assert db.get_sharing(ANN) is True


def test_unknown_user_has_no_preference(db):
    assert db.get_sharing(999) is None
