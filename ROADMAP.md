# Roadmap / future versions

## Done
- **v0.1.0**: Krillion parser, SQLite storage, `/leaderboard` with paging, bot skeleton,
  opt-in cross-server sharing (prompt + `/sharing`), systemd deploy + daily backups.
- **v0.2** (deployed): MapTap and Chainle parsers; scores with comments/links around them.
- **Next release**: weekly/monthly/all-time boards with period buttons, Krillion emoji on the daily
  board, replacing the bot's previous post, overwrite-on-repeat prompt, `\` escape. Tested offline
  only for everything in `bot.py`; verify live.

## Needs verification with real posts
- **MapTap scoring.** Rounds are weighted `(1, 1, 2, 3, 3)` in the sanity check, inferred from
  one sample (94 92 100 91 90 -> 929). Collect more real posts; if any are rejected or the fit
  is off, correct the weights in `parsers/maptap.py`.
- **Chainle.** The 5,000 maximum is stated on chainle.org, but the site shows no share text,
  so the parser is built from one real post. The sample post's link said `chainle.io`; confirm which domain
  real posts carry (both are accepted). Parser is tested against four real posts (with the 🔗
  header and colored squares). Still unconfirmed: that higher is better.
- **Cross-server sharing** is tested offline only. Check live in two real servers that share
  a member.

- **Wordle and Connections** are built from the documented share format only. Collect real
  posts (hard mode, fails, the colour-blind palette, a Connections fail) and check each parses.
  Also confirm how they look on a board: Wordle shows `3`, a fail `7 · failed`; Connections shows
  guesses made (`4 · perfect`).

## Later
### More games

### Bot
- Streaks.
- Persistent leaderboard buttons (currently expire after 10 minutes / restart).
- Revisit the opt-in prompt trigger if it feels wrong in practice (currently: first score
  posted by someone in 2+ servers running the bot).

### Open questions
- Spoiler handling for emoji grids (Wordle).
