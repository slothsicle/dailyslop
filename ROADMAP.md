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
- **v0.3.6**: weekly, monthly and all-time boards show 10 players per page (daily stays at 5).
- **v0.3.7**: puzzle numbers from the future are ignored (a forged `#99999` can no longer become
  the daily board); runtime dependencies pinned in `requirements.txt`, Dependabot enabled.
- **v0.4.0**: hardening and docs round. The database and backups are private to the bot's user
  (`UMask=0077`; the deploy docs now go through `sudo` for backups), and the deploy, security and
  verification docs are brought up to date.
- **v0.5.0**: Wordle and Connections auto-posts keep the poster's original grid above the
  leaderboard (shown in the post only, not stored).
- **v0.5.1**: auto-posts show the board for the puzzle just pasted, so a player in a timezone ahead
  no longer hides the day everyone else is on (#1); `/leaderboard` Daily gets Earlier day / Later
  day buttons.
- **v0.6.0**: Farflung is supported (stand-in emoji for the tier words until the game has its own).
- **v0.7.0**: new weekly / monthly / all-time bests get a shout-out: a 🏆 message that pings
  whoever was knocked off the server's top spot, or a 🎉 line for a personal best. MapTap reads
  its date in UTC and no longer files `January 1` under last year when posted ahead of UTC.
- **v0.7.1**: docs only. Connections is verified against real posts, and MapTap has held up
  in heavy daily use.
- **v0.8.0**: `/checkperms` reports what the bot can do in the current channel and whether a
  missing permission comes from its role or a channel/category override. Wordle is verified
  against real wins.
- **v0.8.1**: docs only. `docs/deploy.md` gains step 2e (firewall, fail2ban, swap, reboot after
  kernel updates) to match the production server.

## Needs verification
`bot.py` has no unit tests, so the first live use of each feature is the test. Seen working live:
the period buttons, post-replacing, `/purge`, and cross-server sharing for one person across two
servers. Not yet confirmed live: the replace-or-keep prompt, two pastes arriving at once, and the
record shout-outs (🏆 message and its ping, 🎉 line), and `/checkperms` (unit-tested logic only;
try it in a channel with a deliberate override).

With real posts:
- **Wordle** has held up against real wins. Still unseen: a fail, hard mode and the colour-blind
  palette; check each is accepted, and how a fail reads on a board (`7 · failed`).
- **Chainle.** The 5,000 maximum is stated on chainle.org but the site shows no share text, so
  the parser comes from four real posts. Still unconfirmed: that higher is better.
- **Farflung** (waiting on more posts) comes from one real post (`205/500 km`: Common, Common, Miss, Uncommon, Rare). It has no round emoji yet, so stand-ins are used (Common 🏠, Uncommon 🚗, Rare ✈️, Elusive 🚀, Farflung 🛸, Miss ⬛); swap them when the game adds its own.
- **Cross-server sharing** has been used by one person; it still wants a wider check.

## Later
- Add a firewall (and optionally fail2ban) on the server; passwords are already off.
- Streaks.
- Persistent leaderboard buttons (they currently expire after 10 minutes or a restart), and a
  replace-or-keep question that survives a restart.
- Revisit the opt-in sharing prompt if it feels wrong in practice (it currently appears on the
  first score by someone in 2+ servers running the bot).
- A real home for `Krillion ∞` if people want it: it is a different game and is ignored today.
- Spoiler handling for emoji grids (Wordle).
- More games: paste a real share post and a parser can be added.
