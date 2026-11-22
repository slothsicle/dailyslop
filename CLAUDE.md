# dailyslop

Discord bot that keeps #general clean of daily-game score spam. When someone pastes a
score, the bot deletes it, posts a compact reformatted version, and shows a per-game
leaderboard. User-facing docs are in `README.md` and `docs/`; this file is for working on the code.

## Status
Six games are supported (Krillion, Chainle, MapTap, Farflung, Wordle, Connections) and the bot runs on a
real server (two Discord servers so far). `bot.py` has no unit tests (the tests cover the pure
modules), so changes to it are only proven by running the bot; what is still unverified against
real posts or a live server is listed in `ROADMAP.md`.

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -e '.[dev]'`
  (`requirements.txt` pins the runtime dependencies to what production runs; bump it deliberately,
  Dependabot opens PRs for it)
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
  `boards.py`: decides which scores appear on a server's board, builds each period, and spots
  new records (`find_records`).
  `leaderboard.py`: rendering and paging (5 per page on the daily board, 10 on the
  weekly/monthly/all-time averages). `bot.py`: Discord glue only; keep logic out of it.
- `db.py`: SQLite. `scores`: one row per guild/user/game/puzzle (the guild is where it was
  pasted). `prefs`: each user's cross-server sharing choice. `posts`: the bot's latest board
  message per channel/game/puzzle. Migrations run on every start and are idempotent; older rows
  get `extra` backfilled from `display` (see `_backfill_extra`).
- `tests/`: parser tests use real pasted samples; storage/handler tests use `:memory:` DBs.
- The bot needs the Message Content *and* Server Members privileged intents.

## Behaviour to preserve
- **Visibility:** a score shows on server G's board if it was pasted in G, or if its author opted
  in to sharing AND is currently a member of G. Decided at read time, so changing a preference
  needs no migration. Sharing users get one score per puzzle globally (if copies from several
  servers exist, e.g. pasted while private, the latest paste wins); everyone else one per puzzle
  per server. Default is private.
- **Boards** (`boards.SCOPES`): `daily` = the latest puzzle anyone has a score for (raw totals,
  `extra` on a second line under each player, normal text, not monospace); `weekly` = the last 7
  *puzzle days* up to that puzzle; `monthly` = the UTC calendar month by when the score was
  posted; `all-time`. The last three are per-player **averages** and never show `extra`.
- **`/leaderboard game`** takes only the game; the period is a row of buttons. The reply deletes
  itself after 5 minutes (`LEADERBOARD_TTL`). The bot's auto-posts are always the daily board and
  have no period buttons. An auto-post shows the board for the puzzle that was just pasted
  (`build_board(..., puzzle=...)`), not the latest one, so someone in a timezone ahead (already on
  the next date) doesn't hide the day everyone else is still playing. `/leaderboard` opens on the latest
  puzzle; its Daily board has Earlier day / Later day buttons (`boards.daily_puzzles`) to step
  through the puzzles that have scores.
- **Grid games:** Wordle and Connections scores expose `.grid` (the pasted rows). `bot.post_share`
  puts it between the header line and the comment, above the board embed. Not stored in the DB.
- **Records** (`boards.find_records`): after a score is stored, `post_share` checks whether it
  strictly beats (ties don't count) every other *single-day* score in the weekly / monthly /
  all-time window on this server (same windows as the boards), and the player's own scores in
  that window. Only the biggest window is reported for each, and a personal best is dropped when
  a server record of the same or a bigger window covers it. A window needs `MIN_RECORD_PUZZLES`
  (3) earlier puzzle days. A personal best is a 🎉 line on the post, with no ping. A server
  record is its own 🏆 message, so it survives post replacement (`/purge` treats it like any
  other bot message), and pings only the previous holders who are still members
  (`AllowedMentions` limited to them; never everyone or roles). Nothing is stored, so replacing a
  record-setting score announces it again.
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
- Runtime dependencies are pinned in `requirements.txt` (what production runs); bump them
  deliberately. On the server the data directory and backups are `700`/`600` (`UMask=0077`).
- **Puzzle numbers are sanity-checked** (`handler.puzzle_is_plausible`): a score whose puzzle is
  more than ~2 days ahead of what the newest stored puzzle plus elapsed time allows is treated as
  forged: the whole message is left alone and nothing is stored. The first score for a game is
  always accepted.
- **Keep the docs current.** When behaviour changes, update `README.md` (user-facing),
  this file, and `ROADMAP.md`.

## Releases
Whenever work is merged into `main` and pushed, version it in the same step (don't wait to be
asked), as the earlier releases were cut:
1. Pick the bump: **minor** (0.3.0 -> 0.4.0) for a new game, command or user-visible feature;
   **patch** (0.3.0 -> 0.3.1) for fixes, parser corrections, docs or cleanups. A schema migration
   alone is not a reason for a minor bump. If unsure, pick patch and say so.
2. Edit `version` in `pyproject.toml` and add a line for it to the "Done" list in `ROADMAP.md`.
3. Run `pytest` and `ruff check .`. Commit as `Release vX.Y.Z`, then `git tag vX.Y.Z` and
   `git push origin main vX.Y.Z`. Only tag `main`.
   For **minor** bumps only, also publish a GitHub release (tags alone don't show as Releases):
   `gh release create vX.Y.Z --verify-tag --title vX.Y.Z --notes-file <file>`, with notes laid out
   as in the existing releases: a one-line summary, **Features**, **Upgrading** (migrations,
   deploy steps) and **Known limitations**. Patches get a tag but no GitHub release.
4. If the release adds a migration, say so in the deploy instructions and have the user take a
   backup first (`sudo systemctl start dailyslop-backup`). Pushing is the user's call: ask first
   unless they already said to push.
5. Deploying: `ssh slothbots` works non-interactively from this machine (user `admin`), but only
   while the user's ssh-agent holds the unlocked key (`ssh-add -t 8h ~/.ssh/id_ed25519`); on
   `Permission denied (publickey)`, ask them to run that. After the push, ask before deploying
   unless the user already said to. Then run the "Updating the bot" steps from `docs/deploy.md`
   (`git pull`, `pip install -r requirements.txt -e .`, copy the unit files if they changed,
   restart, with the backup first if there is a migration) and confirm with
   `systemctl is-active dailyslop` plus a `Logged in as` line in the journal (it takes ~8s).

## Game facts
- **Krillion** (verified against real posts): `Krillion #<n> 🦐`, the total, then 7 emoji, each a
  rarity tier: ⬛ 0, 🫧 10, 🐟 30, 🦑 60, 🏮 85, 🌟 100. The points must sum to the total (max 700),
  otherwise the post is unparseable. `Krillion ∞ #n` is a different game and is ignored.
- **MapTap:** `www.maptap.gg <Month> <day>` / five `<score><emoji>` tokens / `Final score: N`.
  No puzzle number or year, so the puzzle id is the date's ordinal, with the year inferred from
  today's UTC date (the most recent of next/this/last year that is at most a day in the future,
  so `January 1` seen on Dec 31 UTC is tomorrow, not last January). Final score is out of
  1000. Rounds are weighted `(1, 1, 2, 3, 3)`; this reproduces all three real samples seen so far
  exactly (94 92 100 91 90 -> 929, 100 69 88 100 93 -> 924, 100 100 85 99 31 -> 760) but is
  **inferred from them plus loose sources**, so the parser only enforces it within `TOLERANCE` (5). If more real posts disagree, fix the weights or loosen
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
- **Connections** (documented format; one real post, a fail, has been accepted, wins not yet
  seen): `Connections` / `Puzzle #512` / rows
  of 4 of 🟨🟩🟦🟪. A one-colour row is a solved group, a mixed row a mistake; 4 mistakes end the
  game. Score = guesses made (4 = perfect, 7 at most for a win); a fail counts as 8. Fewest
  wins. Inconsistent grids (unfinished, a colour solved twice, play after 4 mistakes) are left
  alone. The `extra` is the solve order, with ❌ for each mistake.
- **Farflung** (one real post): `Farflung #46 · 205/500 km` / five tier words joined by `·` / optional
  `farflung.game` link. Points: Farflung 100, Elusive 85, Rare 70, Uncommon 55, Common 40, Miss 0.
  The total must equal their sum (max 500). The words are shown as stand-in emoji
  (🏠 🚗 ✈️ 🚀 🛸, ⬛ for a miss; an interim measure) in `extra`; `km` is dropped.
- If a real post is rejected, fix the parser rather than assuming the post is wrong.
