# dailyslop

Discord bot that keeps #general clean of daily-game score spam. When someone pastes a
score, the bot deletes it, posts a compact reformatted version, and shows a per-game
leaderboard.

## Status
Krillion parser, SQLite storage, and the bot skeleton are built. The Discord layer
(`bot.py`) is running on a real server; behaviour added since v0.2 (period buttons, replacing posts,
the overwrite prompt) is only tested offline, see ROADMAP.md. Next games are in `ROADMAP.md`.

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
  where the guild is where it was pasted; `prefs`: each user's cross-server sharing choice;
  `posts`: the bot's latest board message per channel/game/puzzle). `scores.extra` is text shown
  only on a single day's board (Krillion's emoji row, MapTap's five round scores). The migration
  fills `extra` for older rows from `display` on every start (idempotent).
  `boards.py`: decides which scores appear on a server's board. `leaderboard.py`:
  rendering/paging. `bot.py`: Discord glue only; keep logic out of it.
- **Visibility rule:** a score shows on server G's board if it was pasted in G, or if its
  author opted in to sharing AND is currently a member of G. Decided at read time, so
  changing a preference needs no migration. Sharing users get one score per puzzle globally;
  everyone else one per puzzle per server. Default is private.
- **Boards** (`boards.SCOPES`): `daily` = the latest puzzle anyone has a score for (raw totals,
  plus `extra`); `weekly` = the last 7 *puzzle days* up to that puzzle; `monthly` = the UTC
  calendar month by when the score was posted; `all-time`. The last three are per-player
  **averages** and never show `extra`. `/leaderboard` takes only the game; the period is a row of
  buttons on the message (the bot's auto-posts do not: they are always the daily board). `/leaderboard` replies delete
  themselves after 5 minutes (`LEADERBOARD_TTL`); the bot's auto-posts do not.
- **Replacing posts:** posting a score deletes the bot's previous post for the same
  channel + game + puzzle (never another game or another day, never anyone's own messages). The
  new post carries only its own author's comment, so replaced posts lose their comment; that is
  accepted. A per-channel lock keeps two quick pastes from deleting each other's posts.
- **Repeat pastes:** same puzzle already stored with a different total -> a public prompt (not
  ephemeral: Discord only allows that for interactions) with buttons only the poster can press.
  Replace swaps the stored score (for sharing users, in every server) and the post; Keep old or
  60s of silence deletes the prompt and the paste. An identical repeat (same total and same `extra`) just gets a short notice.
  The classification lives in `handler.MessageResult` (`new`/`same`/`changed`/`keep_original`).
- The bot needs the Message Content *and* Server Members privileged intents.
- `tests/`: parser tests use real pasted samples. Storage/handler tests use `:memory:` DBs.
- Bot posts the compact message *before* deleting the original, so a failed post never loses a score.

## Releases
Whenever work is merged into `main` and pushed, version it in the same step (don't wait to be
asked). Following how v0.1.0 and v0.2.0 were cut:
1. Pick the bump: **minor** (0.2.0 -> 0.3.0) for a new game, command, or user-visible feature;
   **patch** (0.2.0 -> 0.2.1) for bug fixes, parser corrections, docs, or internal cleanups.
   A schema migration alone is not a reason for a minor bump.
2. Edit `version` in `pyproject.toml`; update the "Done" list in `ROADMAP.md` (add a line for
   the new version, or fold small fixes into it).
3. Run `pytest` and `ruff check .` first. Commit as `Release vX.Y.Z`, then
   `git tag vX.Y.Z` and `git push origin main vX.Y.Z`.
4. If the release adds a migration, say so in the deploy instructions and remind the user to
   check the latest backup in `/opt/dailyslop/backups` first.
Only tag `main`. If unsure whether a change is minor or patch, pick patch and say which.

## Conventions
- Adding a game = adding one parser module plus its tests.
- Parsers are pure functions with no Discord or database code, so they stay easy to test.
- **If no complete, valid score is found in a message, the bot must leave it alone.**
  Never delete a message we couldn't confidently parse. Parsers stay strict about their own
  format; `handler.find_shares` locates share blocks inside longer messages (comments above or
  below, several scores at once) and the leftover text is reposted as a quote so nothing the
  person wrote is lost. Messages with >500 chars of other text or >30 lines are left alone.
- **Escape:** a `\` at the start of the message, or at the start of any line of it, makes the
  bot ignore the whole message (like escaping markdown). Needed because some parsers search for
  their header rather than anchor to it.
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

## Wordle and Connections facts (built from the documented share format, NOT yet verified against real posts)
- **Wordle:** `Wordle 1,234 3/6` (optional `*` = hard mode; `X/6` = fail) then one 5-square row per
  guess. The grid must agree with the header (row count, last row green iff solved). Fewest guesses
  wins; a fail counts as 7 and shows `· failed`.
- **Connections:** `Connections` / `Puzzle #512` / rows of 4 of 🟨🟩🟦🟪. A one-colour row is a solved
  group, a mixed row is a mistake; 4 mistakes end the game. Score = guesses made (4 = perfect,
  max 7 for a win); a fail counts as 8 and shows `· failed · n/4 groups`. Fewest wins. Inconsistent
  grids (unfinished, a colour solved twice, playing on after 4 mistakes) are left alone.
- If a real post is rejected, fix the parser rather than assuming the post is wrong.
