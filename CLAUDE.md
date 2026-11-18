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
  returns a parsed score (`.puzzle`, `.total`, `.detail`, `.display()`), or `None` if it isn't
  that game. `.detail` is optional extra text shown beside the total on a board (Chainle's
  percentile); `Game.puzzle_label` controls how a puzzle id is displayed (MapTap shows dates).
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
- **If no complete, valid score is found in a message, the bot must leave it alone.**
  Never delete a message we couldn't confidently parse. Parsers stay strict about their own
  format; `handler.find_shares` locates share blocks inside longer messages (comments above or
  below, several scores at once) and the leftover text is reposted as a quote so nothing the
  person wrote is lost. Messages with >500 chars of other text or >30 lines are left alone.
- Never print or log the Discord token.

## MapTap facts
Share text: `www.maptap.gg <Month> <day>` / five `<score><emoji>` tokens / `Final score: N`.
No puzzle number and no year, so the puzzle id is the date's ordinal, with the year inferred
from today's date (this year unless that would be more than a day in the future).
Final score is out of 1000. The rounds are weighted `(1, 1, 2, 3, 3)`; this reproduces the one
real sample exactly (94 92 100 91 90 -> 929) but is **inferred from that one sample plus loose
sources**, so the parser only enforces it within `TOLERANCE` (5). If more real posts disagree,
fix the weights or loosen the check; don't assume the formula is right.

## Chainle facts
Share text: `Chainle #N · 2,837 🔗` / `Beat 71% of players` / a line of 5 colored squares (🟥🟧🟨🟩) / optional link (the real post said `https://chainle.io/`, the game's site is chainle.org; both accepted). Any
extra line with no letters or digits (the squares) is ignored; the squares may be glued directly to the link
with no space (seen in a real post), and the header may end in a decorative `🔗`. Ranked by total
(max 5,000, stated on chainle.org; it doesn't say higher is better, but points accumulate),
with the percentile shown as `detail`. chainle.org shows no share text, so the format comes from four real posts.
Lines of any other text make it unparseable, so the bot leaves the message alone.

## Krillion facts (verified against real posts)
Header: `Krillion #<n> 🦐`, then the total, then 7 emoji. Each emoji is a rarity tier:
⬛ 0, 🫧 10, 🐟 30, 🦑 60, 🏮 85, 🌟 100. The emoji points must sum to the total
(max 700); if not, treat the post as unparseable.
