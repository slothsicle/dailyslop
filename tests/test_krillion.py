import pytest

from dailyslop.parsers.krillion import KrillionScore, parse

SAMPLES = [
    ("Krillion #110 🦐\n535\n\n🏮🏮🦑🏮🌟🦑🦑", 110, 535, "🏮🏮🦑🏮🌟🦑🦑"),
    ("Krillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐟", 125, 190, "🐟🐟🐟🐟🐟🫧🐟"),
    ("Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮", 125, 365, "🦑🦑🐟🫧🦑🦑🏮"),
    ("Krillion #125 🦐\n385\n\n🦑🏮🦑⬛🦑🦑🦑", 125, 385, "🦑🏮🦑⬛🦑🦑🦑"),
]


@pytest.mark.parametrize("text,puzzle,total,emojis", SAMPLES)
def test_real_samples(text, puzzle, total, emojis):
    assert parse(text) == KrillionScore(puzzle=puzzle, total=total, emojis=emojis)


def test_display_keeps_all_emojis():
    score = parse(SAMPLES[2][0])
    assert score.display() == "Krillion #125 · 365 · 🦑🦑🐟🫧🦑🦑🏮"


def test_tolerates_surrounding_whitespace_and_blank_lines():
    assert parse("\n  Krillion #125 🦐  \n\n365\n\n🦑🦑🐟🫧🦑🦑🏮\n\n") is not None


def test_tolerates_variation_selectors():
    assert parse("Krillion #125 🦐\n385\n\n🦑🏮🦑⬛️🦑🦑🦑") is not None


def test_sum_mismatch_is_rejected():
    assert parse("Krillion #125 🦐\n366\n\n🦑🦑🐟🫧🦑🦑🏮") is None


def test_wrong_emoji_count_is_rejected():
    assert parse("Krillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧") is None
    assert parse("Krillion #125 🦐\n220\n\n🐟🐟🐟🐟🐟🫧🐟🐟") is None


def test_unknown_emoji_is_rejected():
    assert parse("Krillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐠") is None


def test_total_over_max_is_rejected():
    assert parse("Krillion #1 🦐\n800\n\n🌟🌟🌟🌟🌟🌟🌟") is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello world",
        "Wordle 1,234 4/6\n\n⬛🟨⬛⬛⬛",
        "Krillion #125 🦐\n190",  # missing emoji line
        "Krillion 125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐟",  # no '#'
        "I got this on Krillion today!\nKrillion #125 🦐\n190\n\n🐟🐟🐟🐟🐟🫧🐟",  # extra chatter
    ],
)
def test_non_krillion_or_malformed_returns_none(text):
    assert parse(text) is None
