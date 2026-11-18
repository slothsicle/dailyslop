"""People often write something above or below their score. The score is still recorded,
and what they wrote is kept so the bot can repost it."""

import pytest

from dailyslop.db import Database
from dailyslop.handler import MAX_ANNOTATION_CHARS, MAX_LINES, find_shares, handle_message
from dailyslop.leaderboard import quote_annotation

# Copied as they were pasted.
REAL = [
    (
        "goml shitbags \nChainle #78 · 4,382 🔗\nBeat 98% of players\n🟨🟨🟩🟩🟨\nhttps://chainle.io/",
        ("chainle", 78, 4382),
        "goml shitbags",
    ),
    (
        ":eyes_googly:\nChainle #73 · 3,202 🔗\nBeat 45% of players\n🟨🟨🟥🟨🟩\nhttps://chainle.io/",
        ("chainle", 73, 3202),
        ":eyes_googly:",
    ),
    (
        (
            "first time playing, this is neat.\nChainle #73 · 2,965 🔗\nBeat 30% of players\n"
            "🟧🟧🟨🟧🟩\nhttps://chainle.io/"
        ),
        ("chainle", 73, 2965),
        "first time playing, this is neat.",
    ),
]
KRILLION = "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮"
CHAINLE = "Chainle #90 · 2,837 🔗\nBeat 71% of players\n🟧🟨🟨🟧🟧\nhttps://chainle.io/"


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


@pytest.mark.parametrize("text,expected,comment", REAL)
def test_real_annotated_posts(text, expected, comment):
    shares, annotation = find_shares(text)
    assert [(g.key, s.puzzle, s.total) for g, s in shares] == [expected]
    assert annotation == comment


def test_annotation_before_after_and_both():
    for text, comment in [
        (f"ugh\n{CHAINLE}", "ugh"),
        (f"{CHAINLE}\nugh", "ugh"),
        (f"before\n{CHAINLE}\nafter", "before\nafter"),
        (f"{CHAINLE}", ""),
    ]:
        shares, annotation = find_shares(text)
        assert len(shares) == 1 and annotation == comment


def test_the_squares_and_link_are_not_left_behind_as_comment():
    # They belong to the share, so the comment is only what the person actually wrote.
    _, annotation = find_shares(f"nice\n{CHAINLE}")
    assert "🟧" not in annotation and "chainle" not in annotation.lower()


def test_comment_is_kept_when_squares_and_link_share_a_line():
    text = "bad day\nChainle #90 · 2,371 🔗\nBeat 39% of players\n🟥🟧🟨🟩🟧https://chainle.io/"
    shares, annotation = find_shares(text)
    assert shares[0][1].total == 2371 and annotation == "bad day"


def test_two_games_in_one_message_are_both_found_in_order():
    shares, annotation = find_shares(f"morning!\n{KRILLION}\n\n{CHAINLE}")
    assert [g.key for g, _ in shares] == ["krillion", "chainle"]
    assert annotation == "morning!"


def test_comment_between_two_scores_is_kept():
    shares, annotation = find_shares(f"{KRILLION}\nand then\n{CHAINLE}")
    assert len(shares) == 2 and annotation == "and then"


def test_scores_are_stored_for_every_share(db):
    result = handle_message(
        db, guild_id=1, user_id=10, user_name="ann", text=f"hi\n{KRILLION}\n{CHAINLE}"
    )
    assert [s.is_new for s in result.shares] == [True, True]
    assert result.annotation == "hi"
    again = handle_message(db, guild_id=1, user_id=10, user_name="ann", text=f"x\n{KRILLION}")
    assert [s.is_new for s in again.shares] == [False]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "just chatting about the game today",
        "Chainle is fun lol\nBeat 71% of players",  # not a full share
        "Chainle #90 · 2,837 🔗\nthis was hard lol",  # header but no percentile
    ],
)
def test_messages_without_a_complete_score_are_left_alone(text):
    assert find_shares(text) is None


def test_long_conversations_are_left_alone_even_if_they_contain_a_score():
    novel = "x" * (MAX_ANNOTATION_CHARS + 1)
    assert find_shares(f"{novel}\n{CHAINLE}") is None
    many_lines = "\n".join(["word"] * MAX_LINES)
    assert find_shares(f"{many_lines}\n{CHAINLE}") is None
    assert find_shares(f"{'y' * MAX_ANNOTATION_CHARS}\n{CHAINLE}") is not None  # at the limit


def test_a_broken_score_is_never_extracted_from_the_middle_of_a_line():
    # A wrong total means the parser rejects it, so nothing is stored or deleted.
    assert find_shares("Krillion #125 🦐\n999\n\n🦑🦑🐟🫧🦑🦑🏮") is None


def test_quote_annotation():
    assert quote_annotation("") == ""
    assert quote_annotation("  ") == ""
    assert quote_annotation("hello") == "> hello"
    assert quote_annotation("a\nb") == "> a\n> b"
    long = quote_annotation("z" * 1000, limit=50)
    assert long.startswith("> zzz") and long.endswith("…") and len(long) <= 53
