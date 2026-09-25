# Scheduling reset bot

Clears chosen channels on a schedule, separately for every server the bot is in.
Also supports clearing on demand and logging what gets deleted.

## Setup, start to finish

### 1. Install Python

Python 3.10 or newer. Check with `python --version` (or `python3 --version` on
Mac/Linux). Get it from [python.org/downloads](https://www.python.org/downloads/)
if needed. On Windows, check **Add python.exe to PATH** in the installer.

### 2. Create the bot in Discord

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Open the **Bot** tab → **Reset Token**. Copy it and keep it private.
3. On the same tab, turn on **Message Content Intent** under Privileged Gateway
   Intents. This lets deletion logs include the text of deleted messages. The
   bot still works without it, just without message text in the log.

### 3. Invite it to your server

1. **OAuth2 → URL Generator**.
2. Scopes: check **`bot`** and **`applications.commands`** (the second one is what
   makes the slash commands appear).
3. Bot permissions: **View Channels**, **Read Message History**, **Manage Messages**,
   **Send Messages**, **Attach Files**.
4. Open the generated URL and pick your server.

### 4. Install the dependencies

```
pip install -r requirements.txt
```
`tzdata` (in that file) is required on Windows for timezone support.

### 5. Add your token

Edit `start_bot.bat` and replace `PASTE-YOUR-TOKEN-HERE`, or set the
`DISCORD_TOKEN` environment variable yourself. Don't commit your token anywhere
(see the Git section below).

### 6. Run it

```
python bot.py
```
or double-click `start_bot.bat`. On first run it logs in, loads every file in
`cogs/`, and registers the slash commands. They can take a few minutes to show
up in Discord the first time.

If you used the old single-file version of this bot, put its `reset_settings.json`
in this folder before the first run — it's imported once into the new per-server
files, then renamed to `.migrated`.

### 7. Configure each server

Run these in each server the bot is in:
```
/resetchannels add channel:#your-channel     (repeat for each channel)
/resetdays set days:daily                    (optional — daily is the default)
/resettime time:4:00 AM                      (optional — 4:00 AM is the default)
/resettimezone timezone:Eastern              (optional — Eastern is the default)
/resetlog set channel:#deleted-log           (optional — off by default)
```
Check it worked with `/resetnext`.

## Commands

All commands need the **Manage Server** permission, except `/resetdays view` and
`/resetnext`, which anyone can run. Settings are per server.

| Command | What it does |
|---|---|
| `/resetchannels list` | Show the channels being cleared in this server |
| `/resetchannels add channel:#name` | Add a channel to the schedule |
| `/resetchannels remove channel:#name` | Stop clearing a channel |
| `/resetchannels cleanup` | Drop saved channels that no longer exist |
| `/resetdays view` | Show the current days, time, timezone and log setting |
| `/resetdays set days:...` | Replace the reset days. Accepts `mon wed fri`, `weekdays`, `weekends`, or `daily` |
| `/resetdays add days:...` | Add days to the schedule |
| `/resetdays remove days:...` | Remove days (at least one must remain) |
| `/resettime time:...` | Set the time of day. Accepts `4:30 AM`, `4am`, `16:30`, `noon`, `midnight` |
| `/resettimezone timezone:...` | Set the timezone. Accepts an IANA name (autocompletes as you type) or `Eastern`/`Central`/`Mountain`/`Pacific`/`Alaska`/`Hawaii`/`UTC`/`UK` |
| `/resetnext` | Show the next few scheduled runs |
| `/resetamount set amount:N` | Scheduled resets delete only the N newest messages per channel |
| `/resetamount all` | Scheduled resets delete everything (the default) |
| `/clearnow` | Delete messages in the listed channels right now, with a Delete/Cancel confirmation |
| `/clearnow amount:N` | Delete only the N newest messages per channel |
| `/clearnow channel:#name` | Limit to one listed channel |
| `/resetlog set channel:#name` | Log every deletion (and the deleted messages) to that channel |
| `/resetlog off` | Stop logging (nothing is posted anywhere — this is the default) |
| `/resetlog view` | Show the current log channel |

A change made with any command takes effect immediately: if that day's reset time
hasn't passed yet, it runs today at the new time; if it has already passed, it
starts from the next scheduled day instead.

## Layout

| File | What it is |
|---|---|
| `bot.py` | Entry point. Loads every file in `cogs/`, registers slash commands. Rarely changes. |
| `config.py` | Code-level defaults (default timezone/time, data folder). |
| `settings.py` | Per-server settings storage and the schedule logic. |
| `timeutils.py` | Parsing of days/times/timezones and the text the bot replies with. |
| `clearing.py` | Deleting messages from a channel. Used by both the schedule and `/clearnow`. |
| `deletion_log.py` | Writes the deletion log to a server's log channel (if it has one). |
| `cogs/scheduler.py` | The clock check and the channel clearing. |
| `cogs/schedule_commands.py` | `/resetdays`, `/resettime`, `/resettimezone`, `/resetnext` |
| `cogs/channel_commands.py` | `/resetchannels list / add / remove / cleanup` |
| `cogs/clear_commands.py` | `/clearnow` (delete now, with confirmation) and `/resetamount` |
| `cogs/log_commands.py` | `/resetlog set / off / view`: the deletion log channel |
| `data/guilds/<server id>.json` | Created automatically: each server's saved settings. |

## Clearing messages manually

`/clearnow` deletes messages in this server's listed channels immediately. It always
shows a Delete / Cancel confirmation first, and nothing is removed until you press Delete.

- `/clearnow` deletes everything in every listed channel.
- `/clearnow amount:50` deletes up to the 50 newest messages in each listed channel.
- `/clearnow channel:#raid-a` limits it to one listed channel. Combine with `amount` if you like.

It only works on channels added with `/resetchannels add`.

## How much the scheduled reset deletes

By default each scheduled reset deletes everything in every listed channel.

- `/resetamount set amount:50` makes it delete only the 50 newest messages in each channel.
- `/resetamount all` goes back to deleting everything.

This is saved per server and only affects the schedule. `/clearnow` always asks how much
each time, so the two never change each other. If a channel holds more than the amount you
set, the older messages stay, because each run removes only the newest ones.

`/clearnow` and the schedule never run on the same channel at the same time: whichever starts
second waits for the first to finish.

## Deletion log

`/resetlog set channel:#deleted-log` makes the bot post a record every time it deletes
messages, for both scheduled resets and `/clearnow`: which channel they came from, what
triggered it, and the deleted messages themselves (author, time, text, attachment names).
Short logs are posted as a message; long ones are attached as a `.txt` file.

- **Off by default.** With no log channel set, nothing is posted anywhere. `/resetlog off` turns it off again.
- Set per server. The log channel can't also be a reset channel.
- Pings inside logged messages (`@everyone`, roles, users) are shown as text and never notify anyone.
- Anyone who can read the log channel can read the deleted messages, so keep it private.
- To include message **text**, turn on the **Message Content Intent**: Developer Portal >
  your app > Bot > Privileged Gateway Intents. If it's off, the bot still runs and still logs
  which channel was cleared and who wrote what, but not the text. It prints a reminder at startup.

## License, Privacy Policy and Terms of Service

- **`LICENSE`** — MIT. Says other people can use, copy, and modify this code,
  with no warranty, as long as they keep the copyright notice.
- **`PRIVACY_POLICY.md`** and **`TERMS_OF_SERVICE.md`** — templates covering what
  the Bot stores and how it may be used. Fill in the bracketed placeholders
  (date, contact method, where you host the settings) before using them.
  You need these two if you ever apply for Discord's bot verification (required
  once a bot is in 100+ servers) — the Developer Portal asks for a Privacy
  Policy URL and a Terms of Service URL. For a bot running only in your own
  server(s), verification isn't required and these files are optional, but
  they're good practice to have regardless.
- To give them a URL Discord can use: push this repo to GitHub, then turn on
  **Settings → Pages** for the repo. Your files will be reachable at
  `https://your-name.github.io/your-repo/PRIVACY_POLICY.html` (GitHub Pages
  renders `.md` files as pages). Paste that URL, and the equivalent one for
  Terms of Service, into the Developer Portal under your app's **General
  Information** tab.

## Updating the bot

Settings live in `data/`, separate from the code, so you can replace any `.py` file
(or the whole code folder) and keep every server's settings, as long as you leave
`data/` in place. To make that automatic, set `BOT_DATA_DIR` to a folder outside the
bot folder (see `start_bot.bat`).

- **New commands:** add a new `.py` file to `cogs/` (copy an existing one as a pattern),
  then restart. It's found and loaded automatically and the slash commands are re-registered.
- **Changing a command:** replace just that file in `cogs/` and restart.
- A cog file with an error is skipped and logged; the rest of the bot keeps running.
- Files in `cogs/` whose names start with `_` are helpers, not commands.

## Back-ups

To back up or move the bot's settings, copy the `data/` folder.
