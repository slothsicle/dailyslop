# dailyslop

Discord bot that keeps #general clean of daily-game score spam. When someone pastes a
score, the bot deletes it, posts a compact reformatted version, and shows a per-game
leaderboard.

## Status
Krillion parser, SQLite storage, and the bot skeleton are built. The Discord layer
(`bot.py`) has not been run against a real server yet. Next games are in `ROADMAP.md`.

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Config: copy `.env.example` to `.env` and set `DISCORD_TOKEN` (never commit `.env`).

## Layout
- `src/dailyslop/parsers/`: one module per game. Each parser takes raw message text and
  returns a parsed score (`.puzzle`, `.total`, `.display()`), or `None` if it isn't that game.
- `games.py`: registry of games and ranking direction. `handler.py`: Discord-free
  text -> stored score. `db.py`: SQLite (`scores`: one row per guild/user/game/puzzle,
  where the guild is where it was pasted; `prefs`: each user's cross-server sharing choice).
  `boards.py`: decides which scores appear on a server's board. `leaderboard.py`:
  rendering/paging. `bot.py`: Discord glue only; keep logic out of it.
- **Visibility rule:** a score shows on server G's board if it was pasted in G, or if its
  author opted in to sharing AND is currently a member of G. Decided at read time, so
  changing a preference needs no migration. Sharing users get one score per puzzle globally;
  everyone else one per puzzle per server. Default is private.
- The bot needs the Message Content *and* Server Members privileged intents.
- `tests/`: parser tests use real pasted samples. Storage/handler tests use `:memory:` DBs.
- Bot posts the compact message *before* deleting the original, so a failed post never loses a score.

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
