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

> **Just want to add the bot to your server?** Use the [install link](https://discord.com/oauth2/authorize?client_id=1572409841748680875) and see
> [Adding it to your server](#adding-it-to-your-server).

## Supported games

| Game | Ranked by | Status |
|---|---|---|
| Krillion | Total points, higher is better (max 700) | ✅ Verified against real posts |
| Chainle | Total score, higher is better (max 5,000), with the percentile | ✅ Built from real posts; "higher is better" is assumed |
| MapTap | Final score, higher is better (max 1,000) | ✅ Built from real posts; the round weights are inferred, but match every real post seen so far |
| Farflung | Total points, higher is better (max 500) | ⚠️ Built from one real post; tier points beyond the sample are as reported by the game's author, and Miss is assumed to be 0. Tier names show as Krillion emoji for now |
| Wordle | Fewest guesses (a fail counts as 7) | ⚠️ Built from the documented format, not yet checked against real posts |
| Connections | Fewest guesses (a fail counts as 8) | ⚠️ Built from the documented format; one real post (a fail) has been accepted, wins not yet seen |

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

The board under a post is for the puzzle that was pasted, so a player in a timezone ahead of you
(already on tomorrow's MapTap, say) doesn't hide the day everyone else is still playing.

Each game's daily board also shows its extras (emoji, round scores, squares, ...) on a second
line under each name. For the grid games (Wordle, Connections) the bot's post also repeats the
poster's original grid above the leaderboard.

**Comments are kept.** Text above or below a score is reposted as a quote with the first new
score, with mentions turned off so a comment can never ping anyone. Several scores in one
message are each recorded. A message with a lot of other text (over about 500 characters or
30 lines) is treated as conversation and left alone.

**Put a `\` in front** of a paste (or any line of it) and the bot ignores the whole message.

**Repeats.** Only one score per person per puzzle counts. Pasting the same score again just
gets a short note that disappears after 10 seconds. Pasting a *different* score for a puzzle
you already posted asks you (a message only you can answer) whether to **replace** the old one,
so a wrong paste can be fixed. No answer within 60 seconds keeps the old score.

**Made-up puzzle numbers are ignored.** Every game is daily, so a score whose puzzle number is
more than a couple of days ahead of the newest one the bot has seen is treated as fake and the
message is left alone. (The first score ever posted for a game is always accepted.)

## Commands

- `/leaderboard game:<game>`: show a leaderboard. Buttons switch the period:
  **Daily** (the latest puzzle, raw totals), **Weekly** (the last 7 puzzle days),
  **Monthly** (the current calendar month, UTC) and **All-time**. Weekly and longer rank by
  average. Daily shows 5 players per page and the others 10. The reply deletes itself after
  5 minutes. Daily opens on the newest puzzle anyone has posted; **Earlier day** and **Later day** step
  through older puzzles that have scores.
- `/sharing [setting]`: choose whether your scores show on your other servers (see below).
  With no setting it shows the current one.
- `/purge [limit] [all]`: anyone can run it. Deletes the bot's old posts in the current channel
  (looking back through the last `limit` messages, default 200), keeping each game's latest
  board, or those too with `all:true`. It only deletes the bot's own messages, never scores.

## Using the bot in more than one server

Each server has its own leaderboard. By default a score shows only on the server where it was
pasted.

The first time someone who is in two or more servers running the bot pastes a score, the bot
asks them (once, in the channel, and only they can answer) whether to **share across servers**.
If they say yes:

- their scores appear on the leaderboard of every server they belong to that uses the bot,
  even ones where they never posted (and only on servers they are members of);
- they get one score per puzzle everywhere, so pasting it in a second server counts as a repeat;
- names are their nickname in the server being viewed.

If they say no or ignore the question, they stay private. Either way they can switch with
`/sharing`, and the change applies to their earlier scores too. If you pasted the same puzzle in
several servers before opting in, your most recent paste is the one that counts.

## Adding it to your server

You need the **Manage Server** permission. Open the [install link](https://discord.com/oauth2/authorize?client_id=1572409841748680875), pick your server
and authorize. The bot asks for View Channels, Send Messages, Embed Links, Read Message History
and Manage Messages. It does not ask for Administrator, and it ignores direct messages.

It reacts in every channel it can see. To keep it to `#general`, deny **View Channel** to its
role in the other channels. It reads messages there to spot scores but stores only scores: your
user ID, display name, the game, puzzle and score, and the extras shown on the daily board.
Scores stay on the server where they were pasted unless you opt in with `/sharing`.

**If something's off:**

- *Nothing happens on a paste:* the bot can't see the channel, or the paste isn't a complete,
  valid score (anything it can't fully parse is left alone). If a real score is being ignored,
  send the raw text to whoever runs the bot, since that is a parser bug.
- *The compact post appears but the original stays:* the bot lacks Manage Messages in that
  channel (check channel-level overrides).
- *A command is missing:* new commands can take a while. Reload Discord.

To remove the bot, kick it or use **Server Settings, then Integrations**. Its stored scores
stay in the database; ask whoever runs it to delete them.

## Setup

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and
   create a **New Application**.
2. On the **Bot** tab, copy the token (**Reset Token** if you need a new one). Treat it like a
   password.
3. On the same tab, turn on **Message Content Intent** and **Server Members Intent** (under
   *Privileged Gateway Intents*). Without the first the bot can't read pastes; without the
   second it can't tell who is a member of which server.
4. Set up the install link. On the **Installation** tab:
   - under *Installation Contexts*, tick **Guild Install**;
   - under *Default Install Settings → Guild Install*, add the scopes `bot` and
     `applications.commands` and these permissions: View Channels, Send Messages, Embed
     Links, Read Message History and **Manage Messages** (to delete pastes and the bot's own
     old posts);
   - set *Install Link* to **Discord Provided Link**, and open it to add the bot to a server.

   Back on the **Bot** tab, turn on **Public Bot** if anyone other than you will add it.
   Without it, only the app's owner can.

### 2. Run it

Requires Python 3.11+.

```bash
git clone https://github.com/slothsicle/dailyslop.git
cd dailyslop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -e .

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
pip install -r requirements.txt -e '.[dev]'
pytest          # run tests
ruff check .    # lint
```

Layout:

- `src/dailyslop/parsers/`: one pure parser per game (text in, score or `None` out).
- `games.py`: registry of games and how each is ranked.
- `handler.py`: Discord-free logic that finds scores in a message, checks them and stores them.
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
- The bot has run live in two servers, and cross-server sharing has so far been used by one
  person. Larger cases are covered by offline tests only.
