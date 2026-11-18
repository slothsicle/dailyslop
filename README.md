# dailyslop

A Discord bot that keeps `#general` clean of daily-game score spam.

People love posting their Wordle-style results, and it buries real conversation. When
someone pastes a score, dailyslop:

1. reads it and works out which game it is,
2. posts a compact, reformatted version in its place,
3. deletes the original paste, and
4. shows that game's leaderboard right under it, with ◀ ▶ buttons to scroll.

If the bot can't fully understand a message, **it leaves it alone**. It never deletes
anything it couldn't parse.

## Supported games

| Game | Ranked by | Status |
|---|---|---|
| Krillion | Total points (higher is better, max 700) | ✅ Supported |
| Wordle | Fewest guesses | Planned |
| Chainle | Total score, with percentile | Planned |
| MapTap | Final score | Planned |

See [ROADMAP.md](ROADMAP.md) for details.

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
> 🥇 **slothsicle** · 365

Only one score per person per puzzle counts. A repeat paste is deleted, and the bot
posts a short note that disappears after 10 seconds.

## Commands

- `/leaderboard game:<game> [scope]`: show a leaderboard. Scope is **Latest puzzle**
  (default) or **All-time** (ranked by average score).

## Setup

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and
   create a **New Application**.
2. Open the **Bot** tab and copy the token (**Reset Token** if you need a new one). Treat
   it like a password.
3. On the same tab, turn on **Message Content Intent** (under *Privileged Gateway
   Intents*). The bot can't read score pastes without it.
4. Invite the bot with this URL, replacing `YOUR_CLIENT_ID` with the Application ID from
   the **General Information** tab:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=93184
   ```

   The permissions requested are View Channels, Send Messages, Embed Links, Read Message
   History, and **Manage Messages** (needed to delete the original pastes).

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

To keep it running 24/7, see [docs/deploy.md](docs/deploy.md) (a small Hetzner VPS with
systemd and daily backups).

### Configuration

Set these in `.env`:

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Your bot token. **Never commit `.env`.** |
| `DEV_GUILD_ID` | no | Your test server's ID. Makes slash commands appear instantly instead of waiting for global sync. |
| `DAILYSLOP_DB` | no | Path to the SQLite file (default `data/dailyslop.db`). |

Scores are stored in a local SQLite file, one row per user, game and puzzle. Back that file
up if you care about history.

## Development

```bash
pip install -e '.[dev]'
pytest          # run tests
ruff check .    # lint
```

How it's laid out:

- `src/dailyslop/parsers/`: one pure parser per game (text in, score or `None` out).
- `src/dailyslop/games.py`: registry of supported games and how each is ranked.
- `src/dailyslop/handler.py`: Discord-free logic that turns message text into a stored score.
- `src/dailyslop/db.py`: SQLite storage.
- `src/dailyslop/leaderboard.py`: leaderboard rendering and paging.
- `src/dailyslop/bot.py`: the Discord glue.

To add a game, write a parser in `parsers/`, add tests with real pasted samples, and add one
entry to `games.py`.

## Known limitations

- The leaderboard buttons stop working after 10 minutes or a bot restart. Run
  `/leaderboard` again for a fresh one.
- A paste with extra text around it (like a comment above the score) is not recognized, so
  the bot leaves it alone.
- One server at a time is the tested setup.
