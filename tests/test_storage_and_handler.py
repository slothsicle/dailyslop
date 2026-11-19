from dataclasses import replace

import pytest

from dailyslop.boards import build_board
from dailyslop.db import Database
from dailyslop.games import GAMES
from dailyslop.handler import handle_message
from dailyslop.leaderboard import PAGE_SIZE, Entry, page_count, render_page

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


def post_all(db, user_id, name, text, guild_id=X):
    """The full result: every score found plus the leftover comment, or None."""
    return handle_message(db, guild_id=guild_id, user_id=user_id, user_name=name, text=text)


def post(db, user_id, name, text, guild_id=X):
    """Convenience for single-score messages: the first score found, or None."""
    result = post_all(db, user_id, name, text, guild_id)
    return result.shares[0] if result else None


def board(db, guild_id, members, scope="daily", names=None, keep_extra=False):
    """(title, entries). The per-entry extra (Krillion's emoji) is dropped unless asked for."""
    title, entries = build_board(db, guild_id, KRILLION, scope, members, names)
    if not keep_extra:
        entries = [replace(e, extra="") for e in entries]
    return title, entries


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
    pages = -(-25 // PAGE_SIZE)
    assert PAGE_SIZE == 5 and page_count(entries) == pages == 5
    first = render_page(entries, 0)
    assert first.splitlines()[0].startswith("🥇")
    assert f"u{PAGE_SIZE}" in first and f"u{PAGE_SIZE + 1}" not in first
    last = render_page(entries, pages - 1)
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


def test_latest_paste_wins_when_a_private_user_pasted_twice_then_opts_in(db):
    # Pasted in Y while private, corrected in X while private, then opted in.
    post(db, ANN, "ann", K125_190, guild_id=Y)
    post(db, ANN, "ann", K125_365, guild_id=X)
    db.set_sharing(ANN, True)
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]
    assert board(db, Y, {ANN})[1] == [Entry("ann", "365")]


def test_repeat_check_for_a_sharing_user_compares_with_the_latest_copy(db):
    post(db, ANN, "ann", K125_190, guild_id=Y)
    post(db, ANN, "ann", K125_365, guild_id=X)
    db.set_sharing(ANN, True)
    assert post(db, ANN, "ann", K125_365, guild_id=X).identical_repeat


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


# --- more games, labels, and the schema migration ---------------------------

CHAINLE_90 = "Chainle #90 · 2,837\nBeat 71% of players\n\nhttps://chainle.io/"
CHAINLE_90_LOW = "Chainle #90 · 1,200\nBeat 20% of players"


def test_chainle_is_detected_and_board_shows_total_and_percentile(db):
    result = post(db, ANN, "ann", CHAINLE_90)
    assert result.game.key == "chainle" and result.is_new
    post(db, BOB, "bob", CHAINLE_90_LOW)
    title, entries = build_board(db, X, GAMES["chainle"], "daily", {ANN, BOB})
    assert title == "Chainle #90"
    assert entries == [Entry("ann", "2,837 · 71%"), Entry("bob", "1,200 · 20%")]


def test_games_do_not_mix_on_a_board(db):
    post(db, ANN, "ann", CHAINLE_90)
    post(db, ANN, "ann", K125_365)  # same user, different game
    assert board(db, X, {ANN})[1] == [Entry("ann", "365")]
    assert build_board(db, X, GAMES["chainle"], "daily", {ANN})[1] == [
        Entry("ann", "2,837 · 71%")
    ]


def test_maptap_board_title_uses_the_date_label(db):
    from datetime import date

    ordinal = date(2026, 11, 17).toordinal()
    db.add_score(
        guild_id=X, user_id=ANN, user_name="ann", game="maptap",
        puzzle=ordinal, total=929, display="MapTap · Nov 17 · 929",
    )
    title, entries = build_board(db, X, GAMES["maptap"], "daily", {ANN})
    assert title == "MapTap Nov 17" and entries == [Entry("ann", "929")]


def test_duplicate_chainle_is_rejected(db):
    assert post(db, ANN, "ann", CHAINLE_90).is_new
    assert not post(db, ANN, "ann", CHAINLE_90_LOW).is_new


def test_old_database_without_detail_column_is_migrated(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE scores (
            guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, user_name TEXT NOT NULL,
            game TEXT NOT NULL, puzzle INTEGER NOT NULL, total INTEGER NOT NULL,
            display TEXT NOT NULL, created_at REAL NOT NULL,
            PRIMARY KEY (guild_id, user_id, game, puzzle)
        );
        INSERT INTO scores VALUES (1, 10, 'ann', 'krillion', 125, 365, 'x', 1.0);
        """
    )
    old.commit()
    old.close()

    migrated = Database(path)
    assert build_board(migrated, 1, KRILLION, "daily", {10}) == (
        "Krillion #125", [Entry("ann", "365")]
    )
    assert post(migrated, 11, "bob", CHAINLE_90, guild_id=1).is_new  # new column is writable
    migrated.close()
    Database(path).close()  # reopening an already-migrated file is fine
