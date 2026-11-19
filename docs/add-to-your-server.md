# Adding dailyslop to your Discord server

This is for server owners and admins who want to try the bot. (If you're running your own copy
of the bot, start with [Setup in the README](../README.md#setup) instead.)

## What it does

When someone pastes a daily-game score, the bot deletes it and posts a compact version with
that game's leaderboard underneath. Anything it can't fully parse is left alone. The
[README](../README.md) has the details and the supported games.

## What you need

- The **Manage Server** permission on your Discord server (owners and admins have it).
- The bot's **install link**: <https://discord.com/oauth2/authorize?client_id=1572409841748680875>

## Steps

1. **Open the install link** and pick your server from the dropdown. Only servers where you
   have Manage Server are listed.
2. **Review the permissions**, then click **Authorize**. The bot needs all of these:

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

Paste scores as usual (comments are kept), or put a `\` in front of a message to make the bot
ignore it. Three commands: `/leaderboard` (daily, weekly, monthly and all-time boards),
`/sharing` (show your scores on your other servers too; private by default) and `/purge`
(Manage Messages only: delete the bot's old posts in a channel). Pasting a different score for a
puzzle you already posted asks whether to replace the old one. See the
[README](../README.md#commands) for details.

## What the bot stores

Scores only: your Discord user ID, display name, the game, puzzle and score, and the emoji or
round scores shown on the daily board. The bot reads messages in the channels it can see to
spot scores, but doesn't keep anything that isn't one. Each server has its own leaderboard, and
your scores never show in another server unless you opt in with `/sharing`.

## Troubleshooting

| Problem | Likely cause |
|---|---|
| Nothing happens when someone pastes a score | The bot can't see that channel (**View Channel**), or the paste isn't a complete valid score. It deliberately ignores anything it can't fully parse. |
| It posts the compact score but the original stays | The bot lacks **Manage Messages** in that channel (check channel-level overrides). |
| `/leaderboard` or `/purge` doesn't show up | New commands can take a while. Reload Discord. `/purge` only shows for people with Manage Messages. |
| The leaderboard buttons stop working | They expire after 10 minutes or when the bot restarts. Run `/leaderboard` again. |
| A real score is being ignored | Send the raw text to whoever runs the bot; that's a parser bug. |

## Removing the bot

Kick it from **Server Settings, then Members**, or remove it under **Server Settings, then
Integrations**. Its stored scores for your server stay in the bot's database; ask whoever runs
it to delete them if you want them gone.
