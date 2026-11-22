from datetime import UTC, date, datetime

import pytest

from dailyslop.parsers.maptap import MAX_SCORE, MapTapScore, parse, puzzle_label

TODAY = date(2026, 11, 17)
SAMPLE = "www.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑 90👑\nFinal score: 929"


def test_real_sample():
    score = parse(SAMPLE, today=TODAY)
    assert score == MapTapScore(
        puzzle=date(2026, 11, 17).toordinal(), total=929, rounds=(94, 92, 100, 91, 90)
    )
    assert score.display() == "MapTap · Nov 17 · 929 · 94 92 100 91 90"
    assert score.detail == ""
    assert score.extra == "94 92 100 91 90"  # shown on the daily board


def test_puzzle_label():
    assert puzzle_label(date(2026, 11, 17).toordinal()) == "Nov 17"
    assert puzzle_label(date(2026, 1, 3).toordinal()) == "Jan 3"


def test_tolerates_whitespace_blank_lines_and_https_prefix():
    text = "\n https://www.maptap.gg  November  17 \n\n94🏅 92🏆 100🎯 91👑 90👑\n\nFinal score:   929\n"
    assert parse(text, today=TODAY) is not None


def test_abbreviated_month_and_missing_emoji():
    assert parse("maptap.gg Nov 17\n94 92 100 91 90\nFinal score: 929", today=TODAY) is not None


def test_year_is_inferred_from_today():
    assert parse(SAMPLE, today=TODAY).puzzle == date(2026, 11, 17).toordinal()
    # Pasted just after midnight in another timezone: tomorrow is still this year.
    tomorrow = SAMPLE.replace("November 17", "November 18")
    assert parse(tomorrow, today=TODAY).puzzle == date(2026, 11, 18).toordinal()
    # A December date seen in January belongs to the previous year.
    dec = SAMPLE.replace("November 17", "December 31")
    assert parse(dec, today=date(2027, 1, 2)).puzzle == date(2026, 12, 31).toordinal()
    # A date well in the "future" this year is last year's.
    late = SAMPLE.replace("November 17", "December 25")
    assert parse(late, today=TODAY).puzzle == date(2025, 12, 25).toordinal()


def test_new_year_ahead_of_utc_is_next_year():
    # Dec 31 UTC, but a player in NZ is already on Jan 1: that's tomorrow, not last January.
    jan1 = SAMPLE.replace("November 17", "January 1")
    assert parse(jan1, today=date(2026, 12, 31)).puzzle == date(2027, 1, 1).toordinal()
    # Two days ahead is too far: it falls back to the most recent January 1 in the past.
    jan2 = SAMPLE.replace("November 17", "January 2")
    assert parse(jan2, today=date(2026, 12, 31)).puzzle == date(2026, 1, 2).toordinal()


def test_default_today_is_utc():
    # No `today` given: uses the UTC date, so a post for today's UTC date always parses as it.
    now = datetime.now(UTC).date()
    text = SAMPLE.replace("November 17", f"{now:%B} {now.day}")
    assert parse(text).puzzle == now.toordinal()


def test_impossible_dates_are_rejected():
    assert parse(SAMPLE.replace("November 17", "February 30"), today=TODAY) is None
    assert parse(SAMPLE.replace("November 17", "Smarch 17"), today=TODAY) is None
    # Feb 29 in a year with no Feb 29
    assert parse(SAMPLE.replace("November 17", "February 29"), today=date(2027, 3, 1)) is None


def test_final_score_must_match_the_weighted_rounds():
    assert parse(SAMPLE.replace("929", "930"), today=TODAY) is not None  # within tolerance
    assert parse(SAMPLE.replace("929", "800"), today=TODAY) is None
    assert parse(SAMPLE.replace("929", "1200"), today=TODAY) is None


def test_perfect_game_is_the_maximum():
    perfect = "maptap.gg November 17\n100🏅 100🏆 100🎯 100👑 100👑\nFinal score: 1000"
    assert parse(perfect, today=TODAY).total == MAX_SCORE


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "www.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑\nFinal score: 929",  # 4 rounds
        "www.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑 90👑 88🏅\nFinal score: 929",  # 6 rounds
        "www.maptap.gg November 17\n94🏅 92🏆 101🎯 91👑 90👑\nFinal score: 929",  # round > 100
        "www.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑 90👑",  # no final score
        "www.example.com November 17\n94🏅 92🏆 100🎯 91👑 90👑\nFinal score: 929",
        "nice one!\nwww.maptap.gg November 17\n94🏅 92🏆 100🎯 91👑 90👑\nFinal score: 929",
        "Krillion #125 🦐\n365\n\n🦑🦑🐟🫧🦑🦑🏮",
    ],
)
def test_malformed_returns_none(text):
    assert parse(text, today=TODAY) is None
