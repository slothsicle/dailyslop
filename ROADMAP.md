# Roadmap / future versions

## v0.1: Krillion (current)
- Krillion parser + tests (samples: #110 535, #125 190 / 365 / 385).

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
- SQLite storage, one row per `(user, game, puzzle_id)`; repeat paste is deleted with a brief note.
- `/leaderboard game:<name>` slash command, button pagination (◀ ▶), default view today,
  all-time as an option. Possibly weekly and streaks.
- Compact repost format, e.g. `slothsicle · Krillion #125 · 365 · 🦑🦑🐟🫧🦑🦑🏮`
  (Krillion keeps all 7 emoji).
- Discord setup: bot needs Manage Messages and the Message Content intent.
- Single server for now; multi-server later.

### Open questions
- Spoiler handling for emoji grids (Wordle).
