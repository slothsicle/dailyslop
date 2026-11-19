import pytest

from dailyslop.parsers.farflung import FarflungScore, parse

SAMPLE = (
    "Farflung #46 · 205/500 km\n"
    "Common · Common · Miss · Uncommon · Rare\n"
    "https://farflung.game/s/7hv642?e=46"
)


def test_real_sample():
    score = parse(SAMPLE)
    assert score == FarflungScore(puzzle=46, total=205, emojis="🫧🫧⬛🐟🦑")
    assert score.display() == "Farflung #46 · 205 · 🫧🫧⬛🐟🦑"
    assert score.extra == "🫧🫧⬛🐟🦑"
    assert score.detail == ""


def test_link_and_km_are_optional():
    text = "Farflung #46 · 205/500\nCommon · Common · Miss · Uncommon · Rare"
    assert parse(text) == parse(SAMPLE)


def test_all_tiers():
    score = parse("Farflung #1 · 350/500 km\nFarflung · Elusive · Rare · Uncommon · Common")
    assert score.emojis == "🌟🏮🦑🐟🫧"
    assert score.total == 350


def test_perfect_and_empty_games():
    assert parse("Farflung #1 · 500/500 km\n" + " · ".join(["Farflung"] * 5)).total == 500
    assert parse("Farflung #1 · 0/500 km\n" + " · ".join(["Miss"] * 5)).total == 0


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "Farflung #46 · 206/500 km\nCommon · Common · Miss · Uncommon · Rare",  # sum mismatch
        "Farflung #46 · 205/500 km\nCommon · Common · Miss · Uncommon",  # four rounds
        "Farflung #46 · 205/500 km\nCommon · Common · Miss · Uncommon · Rare · Miss",
        "Farflung #46 · 205/500 km\nCommon · Common · Miss · Uncommon · Mythic",
        "Farflung #46 · 205/400 km\nCommon · Common · Miss · Uncommon · Rare",  # wrong max
        "Farflung 46 · 205/500 km\nCommon · Common · Miss · Uncommon · Rare",  # no '#'
        SAMPLE + "\nso close",  # extra chatter
        "lol\n" + SAMPLE,
        SAMPLE.replace("farflung.game", "example.com"),
        "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮",
    ],
)
def test_unparseable_returns_none(text):
    assert parse(text) is None
