# Roadmap / future versions

## v0.1: Krillion (current)
- Done: Krillion parser + tests, SQLite storage, `/leaderboard` with paging, bot skeleton.
- TODO: run against a real Discord server and fix whatever breaks (the Discord layer is untested).

## Later
### More games
- **Wordle**: fewest guesses wins. Stable share format.
- **Chainle**: `Chainle #90 · 2,837` / `Beat 71% of players`. Higher is better (5 rounds,
  up to 1,000 each, max 5,000). Rank by total, show percentile next to it, drop per-round
  emoji. Scoring rules came from third-party sources, not chainle.io: verify against more
  samples. Re-ask for a paste with the colored squares if we ever want them.
- **MapTap**: `www.maptap.gg November 17` / 5 round scores / `Final score: 929`. Rank by
  final score, higher is better. No puzzle number, so key on the date.

### Bot
- Weekly boards and streaks.
- Persistent leaderboard buttons (currently expire after 10 minutes / restart).
- Optionally find a score inside a longer message instead of requiring an exact paste.
- Cross-server sharing with opt-in (prompt + `/sharing`) is done and tested. Still to check
  live: run the bot in two real servers that share a member.
- Revisit the opt-in prompt trigger if it feels wrong in practice (currently: first score
  posted by someone in 2+ servers running the bot).

### Open questions
- Spoiler handling for emoji grids (Wordle).
