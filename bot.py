"""
Scheduling reset bot: entry point.

Loads every command file in ./cogs, registers the slash commands, and runs the
bot. To add commands, drop a new .py file into ./cogs (see any existing file
for the pattern) and restart. Nothing here needs to change.

Run:
    python bot.py            # normal
    python bot.py --test     # also runs one reset for every server at startup
"""
from __future__ import annotations

import os
import sys
import traceback
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

import config
from settings import SettingsStore


class ResetBot(commands.Bot):
    def __init__(self, message_content: bool = True):
        # The Message Content intent lets the bot read the text of the messages it
        # deletes, so deletion logs can include it. Everything else works without it.
        # Only slash commands are used, so the text-command prefix is just
        # "@mention the bot" and is never used.
        intents = discord.Intents.default()
        intents.message_content = message_content
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.message_content_enabled = message_content
        self.store = SettingsStore()
        self.test_mode = "--test" in sys.argv
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self):
        # Runs once, before the bot connects.
        await self.load_cogs()
        try:
            synced = await self.tree.sync()   # register the slash commands with Discord
            print(f"[OK]   synced {len(synced)} slash command(s)")
        except discord.HTTPException as e:
            print(f"[ERR]  couldn't sync slash commands: {e}")

    async def load_cogs(self):
        """Load every .py file in ./cogs (skipping names that start with _)."""
        for path in sorted((config.BASE_DIR / "cogs").glob("*.py")):
            if path.name.startswith("_"):
                continue
            name = f"cogs.{path.stem}"
            try:
                await self.load_extension(name)
                print(f"[OK]   loaded {name}")
            except Exception:
                # A broken command file must not stop the rest of the bot.
                print(f"[ERR]  couldn't load {name}, skipping it:")
                traceback.print_exc()

    async def on_ready(self):
        print(f"Logged in as {self.user} (id: {self.user.id}), in {len(self.guilds)} server(s)")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "You need the Manage Server permission to change the reset settings."
        else:
            print(f"[ERR]  command error: {type(error).__name__}: {error}")
            msg = "Something went wrong running that command."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


def main():
    try:
        ZoneInfo(config.DEFAULT_TIMEZONE)
    except Exception:
        sys.exit("Timezone data is missing. Run: pip install tzdata")
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("Set the DISCORD_TOKEN environment variable first.")
    try:
        ResetBot(message_content=True).run(token)
    except discord.PrivilegedIntentsRequired:
        # The intent is switched off in the Developer Portal. Don't crash: run
        # without it, and say how to fix it.
        print(
            "[WARN] The Message Content intent is not enabled for this bot, so deletion logs\n"
            "       can't include message text. Everything else works. To fix it: Discord\n"
            "       Developer Portal > your app > Bot > Privileged Gateway Intents >\n"
            "       Message Content Intent (turn it on), then restart the bot."
        )
        ResetBot(message_content=False).run(token)


if __name__ == "__main__":
    main()
