# Adding dailyslop to your Discord server

This is for server owners and admins who want to try the bot. (If you're running your own copy
of the bot, start with [Setup in the README](../README.md#setup) instead.)

## What it does, in one minute

When someone pastes a daily-game score (Krillion, Chainle, MapTap, Wordle, Connections), the
bot reads it, deletes the original, and posts a compact version with that game's leaderboard
underneath. If it can't fully understand a message, it leaves it alone.

## What you need

- The **Manage Server** permission on your Discord server (owners and admins have it).
- The bot's **invite link** (ask whoever runs the bot; see the note at the bottom if that's you).

## Steps

1. **Open the invite link** and pick your server from the dropdown. Only servers where you
   have Manage Server are listed.
2. **Review the permissions**, then click **Authorize**. The bot asks for exactly these, and
   needs all of them:

   | Permission | Why |
   |---|---|
   | View Channels | to see messages in channels it can read |
   | Read Message History | for `/purge`, which looks back through recent messages |
   | Send Messages | to post the compact score and leaderboard |
   | Embed Links | the leaderboard is an embed |
   | Manage Messages | to delete the original paste (and the bot's own old posts) |

   It does **not** ask for Administrator, and it ignores direct messages.
3. **Check where it can see.** The bot reacts in every channel it can view. To limit it to
   `#general` (or wherever your score spam lives), open a channel you *don't* want it in, go to
   **Edit Channel, then Permissions**, add the bot's role, and turn off **View Channel**.
4. **Try it.** In a channel the bot can see, paste a score. You should see the original
   disappear and a compact post with a leaderboard appear. Then type `/leaderboard` and pick a
   game.

## What people can do

- **Paste a score as usual.** A comment above or below is kept and reposted as a quote.
  Several scores in one message are each recorded.
- **Put a `\` in front** of a message to make the bot ignore it entirely (like escaping
  markdown), for example when you want to share a score without it being converted.
- **`/leaderboard game:<game>`**: show a leaderboard. Buttons switch between **Daily**,
  **Weekly** (last 7 puzzle days), **Monthly** and **All-time**; weekly and up are averages.
  The reply deletes itself after 5 minutes.
- **`/sharing`**: choose whether your scores also show on the leaderboards of *other* servers
  you share with the bot. The default is private.
- **`/purge`** (Manage Messages only): delete the bot's old posts in the current channel. It
  keeps each game's latest board.
- **Pasting a puzzle you already posted** with a different score asks you whether to replace
  the old one (only you can answer), which fixes a wrong paste.

## What the bot stores

Scores only: your Discord user ID, your display name at the time, the game, puzzle number and
score, and (for some games) the emoji or round scores shown on the daily board. It reads the
text of messages in the channels it can see so it can spot scores, but it doesn't keep
messages that aren't scores. Each server has its own leaderboard, and your scores never appear
in another server unless you opt in with `/sharing`.

## Troubleshooting

| Problem | Likely cause |
|---|---|
| Nothing happens when someone pastes a score | The bot can't see that channel (**View Channel**), or the paste isn't a complete valid score. It deliberately ignores anything it can't fully parse. |
| It posts the compact score but the original stays | The bot lacks **Manage Messages** in that channel (check channel-level overrides). |
| `/leaderboard` or `/purge` doesn't show up | Discord can take a while to show new commands. Reload Discord. `/purge` only appears for people with Manage Messages. |
| The leaderboard buttons stop working | They expire after 10 minutes or when the bot restarts. Run `/leaderboard` again. |
| A real score is being ignored | Send the raw text to whoever runs the bot. A rejected real post is a parser bug, not user error. |

## Removing the bot

Kick it from **Server Settings, then Members**, or remove it under **Server Settings, then
Integrations**. Its stored scores for your server stay in the bot's database; ask whoever runs
it to delete them if you want them gone.

---

*If you run the bot yourself:* the invite link is
`https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=93184`
with `YOUR_CLIENT_ID` replaced by the **Application ID** from your app's *General Information*
tab in the [Developer Portal](https://discord.com/developers/applications). Share that
link with server admins. You also need **Message Content Intent** and **Server Members
Intent** switched on under the *Bot* tab, or the bot can't read pastes or tell who is in
which server.
