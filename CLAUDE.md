# dailyslop

Discord bot that keeps #general clean of daily-game score spam. When someone pastes a
score, the bot deletes it, posts a compact reformatted version, and shows a per-game
leaderboard.

## Status
Scaffold only. Current milestone: **Krillion parser** (see `ROADMAP.md` for everything else).

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Config: copy `.env.example` to `.env` and set `DISCORD_TOKEN` (never commit `.env`).

## Layout
- `src/dailyslop/parsers/`: one module per game. Each parser takes raw message text and
  returns a parsed score, or `None` if the text isn't that game.
- `tests/`: one test file per parser, using real pasted samples.

## Conventions
- Adding a game = adding one parser module plus its tests.
- Parsers are pure functions with no Discord or database code, so they stay easy to test.
- **If a post fails validation or can't be parsed, the bot must leave the message alone.**
  Never delete a message we couldn't confidently parse.
- Never print or log the Discord token.

## Krillion facts (verified against real posts)
Header: `Krillion #<n> 🦐`, then the total, then 7 emoji. Each emoji is a rarity tier:
⬛ 0, 🫧 10, 🐟 30, 🦑 60, 🏮 85, 🌟 100. The emoji points must sum to the total
(max 700); if not, treat the post as unparseable.
