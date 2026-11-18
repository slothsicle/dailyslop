import pytest

from dailyslop.parsers.chainle import ChainleScore, parse

SAMPLE = "Chainle #90 · 2,837 \nBeat 71% of players\n\nhttps://chainle.io/"


def test_real_sample():
    score = parse(SAMPLE)
    assert score == ChainleScore(puzzle=90, total=2837, percentile=71)
    assert score.display() == "Chainle #90 · 2,837 · beat 71%"
    assert score.detail == "beat 71%"


def test_link_is_optional():
    assert parse("Chainle #90 · 2,837\nBeat 71% of players") == ChainleScore(90, 2837, 71)


def test_link_may_point_at_either_domain():
    for link in ("https://chainle.org/", "https://www.chainle.org", "https://chainle.io/"):
        assert parse(f"Chainle #90 · 2,837\nBeat 71% of players\n\n{link}") is not None
    # A link to anything else is unexpected text, so the post is left alone.
    assert parse("Chainle #90 · 2,837\nBeat 71% of players\n\nhttps://example.com/") is None


def test_total_without_comma_and_low_scores():
    assert parse("Chainle #5 · 950\nBeat 3% of players").total == 950
    assert parse("Chainle #5 · 0\nBeat 0% of players").total == 0


def test_round_emoji_lines_are_ignored_wherever_they_appear():
    with_squares = "Chainle #90 · 2,837\n🟩🟩🟨🟧🟥\nBeat 71% of players\n\nhttps://chainle.io/"
    assert parse(with_squares) == ChainleScore(90, 2837, 71)
    after = "Chainle #90 · 2,837\nBeat 71% of players\n🟩🟩🟨🟧🟥"
    assert parse(after) == ChainleScore(90, 2837, 71)


def test_maximum_score_is_accepted_but_not_beyond():
    assert parse("Chainle #1 · 5,000\nBeat 99% of players") is not None
    assert parse("Chainle #1 · 5,001\nBeat 99% of players") is None


def test_percentile_over_100_is_rejected():
    assert parse("Chainle #1 · 2,000\nBeat 101% of players") is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "Chainle #90 · 2,837",  # no percentile line
        "Chainle 90 · 2,837\nBeat 71% of players",  # no '#'
        "Chainle #90 · 2,837\nBeat 71% of players\nBeat 10% of players",  # two percentile lines
        "Chainle #90 · 2,837\nBeat 71% of players\nthis was hard lol",  # extra chatter
        "lol\nChainle #90 · 2,837\nBeat 71% of players",  # chatter before
        "Chainle #90 · 2,8,37\nBeat 71% of players",  # malformed number
        "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮",
    ],
)
def test_malformed_returns_none(text):
    assert parse(text) is None
