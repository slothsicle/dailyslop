# dailyslop

Discord bot that keeps #general clean of daily-game score spam. When someone pastes a
score, the bot deletes it, posts a compact reformatted version, and shows a per-game
leaderboard. User-facing docs are in `README.md` and `docs/`; this file is for working on the code.

## Status
Five games are supported (Krillion, Chainle, MapTap, Wordle, Connections) and the bot runs on a
real server. Everything in `bot.py` is tested offline only (the tests cover the pure modules);
what is still unverified against real posts or a live server is listed in `ROADMAP.md`.

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Config: copy `.env.example` to `.env` and set `DISCORD_TOKEN` (never commit `.env`).

## Layout
- `src/dailyslop/parsers/`: one module per game. A parser takes raw message text and returns a
  parsed score or `None` if it isn't that game. The score has `.puzzle`, `.total`, `.detail`
  (short text shown beside the total, e.g. Chainle's `71%`), `.extra` (text for a single day's
  board only: emoji, round scores, ...) and `.display()`. `Game.puzzle_label` controls how a
  puzzle id is shown (MapTap shows dates).
- `games.py`: registry of games and ranking direction. `handler.py`: Discord-free
  text -> stored scores, and classifying them (`MessageResult.new/same/changed/keep_original`).
  `boards.py`: decides which scores appear on a server's board and builds each period.
  `leaderboard.py`: rendering and paging (5 per page). `bot.py`: Discord glue only; keep logic
  out of it.
- `db.py`: SQLite. `scores`: one row per guild/user/game/puzzle (the guild is where it was
  pasted). `prefs`: each user's cross-server sharing choice. `posts`: the bot's latest board
  message per channel/game/puzzle. Migrations run on every start and are idempotent; older rows
  get `extra` backfilled from `display` (see `_backfill_extra`).
- `tests/`: parser tests use real pasted samples; storage/handler tests use `:memory:` DBs.
- The bot needs the Message Content *and* Server Members privileged intents.

## Behaviour to preserve
- **Visibility:** a score shows on server G's board if it was pasted in G, or if its author opted
  in to sharing AND is currently a member of G. Decided at read time, so changing a preference
  needs no migration. Sharing users get one score per puzzle globally; everyone else one per
  puzzle per server. Default is private.
- **Boards** (`boards.SCOPES`): `daily` = the latest puzzle anyone has a score for (raw totals,
  `extra` on a second line under each player, normal text, not monospace); `weekly` = the last 7
  *puzzle days* up to that puzzle; `monthly` = the UTC calendar month by when the score was
  posted; `all-time`. The last three are per-player **averages** and never show `extra`.
- **`/leaderboard game`** takes only the game; the period is a row of buttons. The reply deletes
  itself after 5 minutes (`LEADERBOARD_TTL`). The bot's auto-posts are always the daily board and
  have no period buttons.
- **Replacing posts:** posting a score deletes the bot's previous post for the same
  channel + game + puzzle (never another game or day, never anyone else's messages). A new post
  carries only its own author's comment, so a replaced post's comment is lost; that is
  accepted. A per-channel lock stops two quick pastes deleting each other's posts.
- **`/purge [limit] [all]`** (anyone can run it): deletes the bot's own messages among the last
  `limit` (default 200, max 1000), except each game's newest-puzzle post (`db.latest_post_ids`);
  `all:true` deletes those too. Only ever the bot's messages, and scores are never touched.
- **Repeat pastes:** same puzzle already stored with a different total or `extra` -> a public
  prompt (not ephemeral: Discord only allows that for interactions) with buttons only the poster
  can press. Replace swaps the stored score (for sharing users, in every server) and the post;
  Keep old, or 60s of silence, deletes the prompt and the paste. An identical repeat just gets a
  short notice.
- The bot posts the compact message *before* deleting the original, so a failed post never loses
  a score.

## Conventions
- Adding a game = one parser module plus its tests, one entry in `games.py`.
- Parsers are pure functions with no Discord or database code.
- **If no complete, valid score is found in a message, the bot must leave it alone.** Never
  delete a message we couldn't confidently parse. Parsers stay strict about their own format;
  `handler.find_shares` locates share blocks inside longer messages (comment above or below,
  several scores at once) and the leftover text is reposted as a quote with the first new
  score. Messages with >500 chars of other text or >30 lines are left alone.
- **Escape:** a `\` at the start of the message, or of any line of it, makes the bot ignore the
  whole message. Some parsers search for their header rather than anchor to it, so this is checked
  on leftover lines too.
- Never print or log the Discord token.
- **Keep the docs current.** When behaviour changes, update `README.md` (user-facing),
  this file, and `ROADMAP.md`.

## Releases
Whenever work is merged into `main` and pushed, version it in the same step (don't wait to be
asked), as v0.1.0 to v0.3.x were cut:
1. Pick the bump: **minor** (0.3.0 -> 0.4.0) for a new game, command or user-visible feature;
   **patch** (0.3.0 -> 0.3.1) for fixes, parser corrections, docs or cleanups. A schema migration
   alone is not a reason for a minor bump. If unsure, pick patch and say so.
2. Edit `version` in `pyproject.toml` and add a line for it to the "Done" list in `ROADMAP.md`.
3. Run `pytest` and `ruff check .`. Commit as `Release vX.Y.Z`, then `git tag vX.Y.Z` and
   `git push origin main vX.Y.Z`. Only tag `main`.
   For **minor** bumps only, also publish a GitHub release (tags alone don't show as Releases):
   `gh release create vX.Y.Z --verify-tag --title vX.Y.Z --notes "<the ROADMAP line>"`.
   Patches get a tag but no GitHub release.
4. If the release adds a migration, say so in the deploy instructions and have the user take a
   backup first (`sudo systemctl start dailyslop-backup`). Pushing is the user's call: ask first
   unless they already said to push.
5. Deploying: `ssh slothbots` works non-interactively from this machine (user `admin`). After the
   push, ask before deploying unless the user already said to. Then run the update from
   `docs/deploy.md` (`sudo -u dailyslop git pull`, `sudo systemctl restart dailyslop`, with the
   backup first if there is a migration) and confirm with `systemctl is-active dailyslop`.

## Game facts
- **Krillion** (verified against real posts): `Krillion #<n> 🦐`, the total, then 7 emoji, each a
  rarity tier: ⬛ 0, 🫧 10, 🐟 30, 🦑 60, 🏮 85, 🌟 100. The points must sum to the total (max 700),
  otherwise the post is unparseable. `Krillion ∞ #n` is a different game and is ignored.
- **MapTap:** `www.maptap.gg <Month> <day>` / five `<score><emoji>` tokens / `Final score: N`.
  No puzzle number or year, so the puzzle id is the date's ordinal, with the year inferred from
  today (this year unless that would be more than a day in the future). Final score is out of
  1000. Rounds are weighted `(1, 1, 2, 3, 3)`; this reproduces the one real sample exactly
  (94 92 100 91 90 -> 929) but is **inferred from that sample plus loose sources**, so the parser
  only enforces it within `TOLERANCE` (5). If more real posts disagree, fix the weights or loosen
  the check; don't assume the formula is right.
- **Chainle:** `Chainle #N · 2,837 🔗` / `Beat 71% of players` / a line of 5 squares (🟥🟧🟨🟩) /
  an optional link (real posts said `chainle.io`, the site is chainle.org; both accepted). Any
  extra line with no letters or digits is ignored; the squares may be glued to the link and the
  header may end in a decorative `🔗` (both seen in real posts). Ranked by total (max 5,000;
  chainle.org doesn't say higher is better, but points accumulate); the percentile is the
  `detail` and the squares are the `extra`. Any other text makes it unparseable. Built from four
  real posts, since chainle.org shows no share text.
- **Wordle** (documented format only, NOT yet verified against real posts): `Wordle 1,234 3/6`
  (optional `*` = hard mode; `X/6` = fail), then one 5-square row per guess. The grid must agree
  with the header (row count; last row green iff solved). Fewest guesses wins; a fail counts as
  7. The `extra` is greens per guess.
- **Connections** (documented format only, NOT yet verified): `Connections` / `Puzzle #512` / rows
  of 4 of 🟨🟩🟦🟪. A one-colour row is a solved group, a mixed row a mistake; 4 mistakes end the
  game. Score = guesses made (4 = perfect, 7 at most for a win); a fail counts as 8. Fewest
  wins. Inconsistent grids (unfinished, a colour solved twice, play after 4 mistakes) are left
  alone. The `extra` is the solve order, with ❌ for each mistake.
- If a real post is rejected, fix the parser rather than assuming the post is wrong.
