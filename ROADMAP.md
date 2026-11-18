# Roadmap / future versions

## Done
- **v0.1.0**: Krillion parser, SQLite storage, `/leaderboard` with paging, bot skeleton,
  opt-in cross-server sharing (prompt + `/sharing`), systemd deploy + daily backups.
- **Next release**: MapTap and Chainle parsers (built, tested offline, not yet run live).

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

## Later
### More games
- **Wordle**: fewest guesses wins. Stable share format.

### Bot
- Weekly boards and streaks.
- Persistent leaderboard buttons (currently expire after 10 minutes / restart).
- Revisit the opt-in prompt trigger if it feels wrong in practice (currently: first score
  posted by someone in 2+ servers running the bot).

### Open questions
- Spoiler handling for emoji grids (Wordle).
