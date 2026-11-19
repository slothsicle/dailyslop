# Roadmap

## Done
- **v0.1.0**: Krillion parser, SQLite storage, `/leaderboard` with paging, bot skeleton,
  opt-in cross-server sharing (prompt + `/sharing`), systemd deploy + daily backups.
- **v0.2.0**: MapTap, Chainle, Wordle and Connections parsers; scores with comments or links
  around them (several per message); daily/weekly/monthly/all-time boards with period buttons;
  the bot replaces its previous post for a puzzle; overwrite-on-repeat prompt; `\` escape;
  `/leaderboard` replies delete after 5 minutes.
- **v0.2.1 / v0.2.2**: per-game extras on the daily board (Krillion emoji, MapTap rounds,
  Chainle squares, Connections solve order, Wordle greens per guess); auto-posts have no period
  buttons. Scores stored before a game's extra existed show without it.
- **v0.3.0**: `/purge` (deletes the bot's old posts in a channel, keeps each game's latest
  board); extras on a second line under each player; 5 players per page.
- **v0.3.1 / v0.3.2**: Chainle shows `71%` instead of `beat 71%` (stored rows migrated on
  start); boards are normal text again, with names never truncated.
- **v0.3.3**: docs refresh; README has an "Adding it to your server" section and the Discord-
  provided install link.
- **v0.3.4**: `/purge` takes `all:true` (also deletes each game's latest board) and can be run by
  anyone.
- **v0.3.5**: a sharing user with the same puzzle stored in several servers (pasted while private)
  now shows the latest paste, not the earliest; repeat checks compare against that copy.

## Needs verification
Everything in `bot.py` is tested offline only, so the first live use of each is a test:
the replace-or-keep prompt, period buttons, `/purge`, and the post-replacing behaviour
(including two pastes arriving at once).

With real posts:
- **Wordle and Connections** are built from the documented share format only. Collect real
  posts (hard mode, a fail, the colour-blind palette, a Connections fail) and check each is
  accepted. Also check how they read on a board (Wordle `3`, fail `7 · failed`; Connections
  `4 · perfect`).
- **MapTap scoring.** Rounds are weighted `(1, 1, 2, 3, 3)`, inferred from one sample
  (94 92 100 91 90 -> 929). If a real post is rejected, correct the weights in
  `parsers/maptap.py`.
- **Chainle.** The 5,000 maximum is stated on chainle.org but the site shows no share text, so
  the parser comes from four real posts. Still unconfirmed: that higher is better.
- **Cross-server sharing** needs a live check in two servers that share a member.

## Later
- Streaks.
- Persistent leaderboard buttons (they currently expire after 10 minutes or a restart), and a
  replace-or-keep question that survives a restart.
- Revisit the opt-in sharing prompt if it feels wrong in practice (it currently appears on the
  first score by someone in 2+ servers running the bot).
- A real home for `Krillion ∞` if people want it: it is a different game and is ignored today.
- Spoiler handling for emoji grids (Wordle).
- More games: paste a real share post and a parser can be added.
