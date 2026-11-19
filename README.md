# dailyslop

A Discord bot that keeps `#general` clean of daily-game score spam.

People love posting their Wordle-style results, and it buries real conversation. When someone
pastes a score, dailyslop:

1. works out which game it is,
2. posts a compact version in its place and deletes the original paste,
3. shows that game's leaderboard right under it, and
4. deletes its own post from earlier in the day, so the channel only ever holds the latest board.

If the bot can't fully understand a message, **it leaves it alone**. It never deletes anything
it couldn't parse.

> **Just want to add the bot to your server?** See
> [docs/add-to-your-server.md](docs/add-to-your-server.md).

## Supported games

| Game | Ranked by | Status |
|---|---|---|
| Krillion | Total points, higher is better (max 700) | ✅ Verified against real posts |
| Chainle | Total score, higher is better (max 5,000), with the percentile | ✅ Built from real posts; "higher is better" is assumed |
| MapTap | Final score, higher is better (max 1,000) | ✅ Built from real posts; round weights inferred from one sample |
| Wordle | Fewest guesses (a fail counts as 7) | ⚠️ Built from the documented format, not yet checked against real posts |
| Connections | Fewest guesses (a fail counts as 8) | ⚠️ Same |

`Krillion ∞` (infinity mode) is a different game and is ignored. See [ROADMAP.md](ROADMAP.md).

### Example

Someone pastes:

```
Krillion #125 🦐
365

🦑🦑🐟🫧🦑🦑🏮
```

The bot replaces it with:

> **slothsicle** · Krillion #125 · 365 · 🦑🦑🐟🫧🦑🦑🏮
>
> **Krillion #125**
> 🥇 **slothsicle** · 365
> 🦑🦑🐟🫧🦑🦑🏮

The daily board also shows each player's emoji (Krillion), round scores (MapTap), squares
(Chainle), solve order (Connections) or greens per guess (Wordle) on a second line under their
name.

**Comments are kept.** Text above or below a score is reposted as a quote with the first new
score, with mentions turned off so a comment can never ping anyone. Several scores in one
message are each recorded. A message with a lot of other text (over about 500 characters or
30 lines) is treated as conversation and left alone.

**Put a `\` in front** of a paste (or any line of it) and the bot ignores the whole message.

**Repeats.** Only one score per person per puzzle counts. Pasting the same score again just
gets a short note that disappears after 10 seconds. Pasting a *different* score for a puzzle
you already posted asks you (a message only you can answer) whether to **replace** the old one,
so a wrong paste can be fixed. No answer within 60 seconds keeps the old score.

## Commands

- `/leaderboard game:<game>`: show a leaderboard. Buttons switch the period:
  **Daily** (the latest puzzle, raw totals), **Weekly** (the last 7 puzzle days),
  **Monthly** (the current calendar month, UTC) and **All-time**. Weekly and longer rank by
  average. The reply deletes itself after 5 minutes.
- `/sharing [setting]`: choose whether your scores show on your other servers (see below).
  With no argument it shows your current setting.
- `/purge [limit]`: needs Manage Messages. Deletes the bot's old posts in the current channel
  (looking back through the last `limit` messages, default 200), keeping each game's latest
  board. It only ever deletes the bot's own messages.

## Using the bot in more than one server

Each server has its own leaderboard. By default a score shows only on the server where it was
pasted.

The first time someone who is in two or more servers running the bot pastes a score, the bot
asks them (once, in the channel, and only they can answer) whether to **share across servers**.
If they say yes:

- their scores appear on the leaderboard of every server they belong to that uses the bot,
  even ones where they never posted;
- people only appear on servers they are members of;
- they get one score per puzzle everywhere, so pasting the same puzzle in a second server
  counts as a repeat;
- names are the person's nickname in the server being viewed.

If they say no or ignore the question, they stay private. Either way they can switch with
`/sharing`, and the change applies to their earlier scores too.

## Setup

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and
   create a **New Application**.
2. On the **Bot** tab, copy the token (**Reset Token** if you need a new one). Treat it like a
   password.
3. On the same tab, turn on **Message Content Intent** and **Server Members Intent** (under
   *Privileged Gateway Intents*). Without the first the bot can't read pastes; without the
   second it can't tell who is a member of which server.
4. Invite the bot with this URL, replacing `YOUR_CLIENT_ID` with the Application ID from the
   **General Information** tab:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=93184
   ```

   The permissions are View Channels, Send Messages, Embed Links, Read Message History and
   **Manage Messages** (to delete pastes and the bot's own old posts).

### 2. Run it

Requires Python 3.11+.

```bash
git clone https://github.com/slothsicle/dailyslop.git
cd dailyslop
python -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env     # then edit .env and set DISCORD_TOKEN
python -m dailyslop
```

To keep it running 24/7, see [docs/deploy.md](docs/deploy.md) (a small VPS with systemd and
daily backups).

### Configuration

Set these in `.env`:

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Your bot token. **Never commit `.env`.** |
| `DEV_GUILD_ID` | no | Your test server's ID. Slash commands then appear instantly instead of waiting for global sync. |
| `DAILYSLOP_DB` | no | Path to the SQLite file (default `data/dailyslop.db`). |

Scores live in one SQLite file. Back it up if you care about history (the deploy guide sets up
daily backups).

## Development

```bash
pip install -e '.[dev]'
pytest          # run tests
ruff check .    # lint
```

Layout:

- `src/dailyslop/parsers/`: one pure parser per game (text in, score or `None` out).
- `games.py`: registry of games and how each is ranked.
- `handler.py`: Discord-free logic that finds scores in a message and stores them.
- `db.py`: SQLite storage. `boards.py`: which scores appear on which board.
  `leaderboard.py`: rendering and paging.
- `bot.py`: the Discord glue. Keep logic out of it.

To add a game, write a parser in `parsers/`, add tests using real pasted samples, and add one
entry to `games.py`. See [CLAUDE.md](CLAUDE.md) for conventions and the release process.

## Known limitations

- Leaderboard buttons stop working after 10 minutes or a bot restart. Run `/leaderboard` again.
- A replace-or-keep question that is open when the bot restarts stops working (its buttons go
  dead), so paste again if that happens.
- Scores stored before a game's daily-board extras existed (for example Chainle squares) show
  without them.
- Cross-server sharing and everything added since v0.2 has so far been tested offline and in one
  server.
