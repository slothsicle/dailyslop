"""Repeats, overwriting a wrong score, and the bot's own post bookkeeping."""

import pytest

from dailyslop.boards import build_board
from dailyslop.db import Database
from dailyslop.games import GAMES
from dailyslop.handler import handle_message, replace_score

K = GAMES["krillion"]
X, Y = 1, 2
ANN = 10
K126_375 = "Krillion #126 🦐\n375\n\n🐟🦑🐟🏮🏮🏮⬛"
K126_120 = "Krillion #126 🦐\n120\n\n⬛🐟🐟🫧🫧🫧🐟"


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def post(db, text, guild=X, user=ANN):
    return handle_message(db, guild_id=guild, user_id=user, user_name="ann", text=text).shares[0]


def totals(db, guild, members=(ANN,)):
    return [(e.value, e.extra) for e in build_board(db, guild, K, "daily", set(members))[1]]


def test_a_repeat_reports_the_score_it_collided_with(db):
    assert post(db, K126_375).previous_total is None
    again = post(db, K126_120)
    assert not again.is_new and again.previous_total == 375
    assert totals(db, X) == [("375", "🐟🦑🐟🏮🏮🏮⬛")]  # nothing changed yet


def test_replace_overwrites_the_score_and_its_emoji(db):
    post(db, K126_375)
    again = post(db, K126_120)
    replace_score(db, guild_id=X, user_id=ANN, user_name="ann", game=again.game, score=again.score)
    assert totals(db, X) == [("120", "⬛🐟🐟🫧🫧🫧🐟")]
    assert not post(db, K126_120).is_new  # and it is the stored one now


def test_replace_in_one_server_leaves_a_private_users_other_server_alone(db):
    post(db, K126_375, guild=X)
    post(db, K126_375, guild=Y)
    again = post(db, K126_120, guild=X)
    replace_score(db, guild_id=X, user_id=ANN, user_name="ann", game=again.game, score=again.score)
    assert totals(db, X)[0][0] == "120"
    assert totals(db, Y)[0][0] == "375"


def test_replace_for_a_sharing_user_removes_every_old_copy(db):
    post(db, K126_375, guild=X)
    db.set_sharing(ANN, True)
    # A copy pasted in Y before they opted in would otherwise outlive the overwrite.
    db.conn.execute(
        "INSERT INTO scores SELECT 2, user_id, user_name, game, puzzle, total, display, "
        "created_at + 1, detail, extra FROM scores"
    )
    again = post(db, K126_120, guild=Y)
    assert again.previous_total == 375
    replace_score(db, guild_id=Y, user_id=ANN, user_name="ann", game=again.game, score=again.score)
    assert totals(db, X) == [("120", "⬛🐟🐟🫧🫧🫧🐟")]
    assert totals(db, Y) == [("120", "⬛🐟🐟🫧🫧🫧🐟")]
    assert db.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 1


def test_swap_post_returns_the_previous_message_only_for_the_same_key(db):
    assert db.swap_post(500, "krillion", 126, 1) is None
    assert db.swap_post(500, "krillion", 126, 2) == 1
    assert db.swap_post(500, "krillion", 127, 3) is None  # another day: left alone
    assert db.swap_post(500, "chainle", 126, 4) is None  # another game: left alone
    assert db.swap_post(501, "krillion", 126, 5) is None  # another channel: left alone
    assert db.swap_post(500, "krillion", 126, 6) == 2


# --- how a message's shares are classified (bot.py just acts on this) ---------------------

K127 = "Krillion #127 🦐\n120\n\n⬛🐟🐟🫧🫧🫧🐟"
K126_375_ALT = "Krillion #126 🦐\n375\n\n🌟🌟🏮🐟🐟🐟⬛"  # same total, different emoji
COMMENT = "got it\n"


def result(db, text):
    return handle_message(db, guild_id=X, user_id=ANN, user_name="ann", text=text)


def test_all_new(db):
    r = result(db, K126_375)
    assert (len(r.new), len(r.same), len(r.changed), r.keep_original) == (1, 0, 0, False)


def test_all_identical_repeats_get_a_notice_and_no_prompt(db):
    result(db, K126_375)
    r = result(db, K126_375)
    assert (len(r.new), len(r.same), len(r.changed), r.keep_original) == (0, 1, 0, False)


def test_all_changed_repeats_keep_the_original_paste_for_the_prompt(db):
    result(db, K126_375)
    r = result(db, COMMENT + K126_120)
    assert (len(r.new), len(r.same), len(r.changed), r.keep_original) == (0, 0, 1, True)
    assert r.annotation == "got it"  # the comment survives until they answer


def test_same_total_with_different_emoji_still_counts_as_changed(db):
    result(db, K126_375)
    r = result(db, K126_375_ALT)
    assert len(r.changed) == 1 and not r.same


def test_new_plus_changed_deletes_the_paste_and_asks_only_about_the_repeat(db):
    result(db, K126_375)
    r = result(db, K126_120 + "\n" + K127)
    assert [s.score.puzzle for s in r.new] == [127]
    assert [s.score.puzzle for s in r.changed] == [126]
    assert r.keep_original is False


def test_identical_plus_changed_asks_about_the_changed_one_only(db):
    result(db, K126_375)
    result(db, K127)
    r = result(db, K126_375 + "\n" + "Krillion #127 🦐\n375\n\n🐟🦑🐟🏮🏮🏮⬛")
    assert [s.score.puzzle for s in r.same] == [126]
    assert [s.score.puzzle for s in r.changed] == [127]
    assert r.keep_original is True
