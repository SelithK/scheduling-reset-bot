"""
Choose where deleted messages are logged, for the server the command is used in:
    /resetlog set channel:#deleted-log    log every deletion there
    /resetlog off                         stop logging (nothing is posted anywhere)
    /resetlog view                        show the current setting
Applies to both scheduled resets and /clearnow. Needs the Manage Server permission.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from cogs._common import reply, save, settings_for


class LogCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    resetlog = app_commands.Group(
        name="resetlog",
        description="Choose where deleted messages are logged",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @resetlog.command(name="set", description="Log every deletion (and the deleted messages) to this channel")
    @app_commands.describe(channel="The channel that receives the deletion logs. Keep it private")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        gs = settings_for(interaction)
        if channel.id in gs.channels:
            return await reply(
                interaction,
                f"{channel.mention} is on the reset list, so it would be cleared and logged into itself. "
                "Pick a different channel, or remove it first with `/resetchannels remove`.",
            )
        gs.log_channel = channel.id
        save(interaction, gs)

        perms = channel.permissions_for(channel.guild.me)
        missing = [
            name for name, ok in (
                ("View Channel", perms.view_channel),
                ("Send Messages", perms.send_messages),
                ("Attach Files", perms.attach_files),
            ) if not ok
        ]
        msg = (
            f"Deleted messages will now be logged to {channel.mention}, along with which channel they "
            "came from.\nAnyone who can read that channel can read the deleted messages, so keep it private."
        )
        if missing:
            msg += f"\nHeads up: I'm missing **{', '.join(missing)}** there, so logging will fail until that's fixed."
        if not self.bot.message_content_enabled:
            msg += (
                "\nThe Message Content intent is off for this bot, so logs will show who deleted what "
                "and where, but not the message text."
            )
        await reply(interaction, msg)

    @resetlog.command(name="off", description="Stop logging deleted messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def log_off(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        gs.log_channel = None
        save(interaction, gs)
        await reply(interaction, "Logging is off. Deleted messages will not be posted anywhere.")

    @resetlog.command(name="view", description="Show where deleted messages are logged")
    async def log_view(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        if gs.log_channel is None:
            return await reply(interaction, "Logging is off. Turn it on with `/resetlog set`.")
        await reply(interaction, f"Deleted messages are logged to <#{gs.log_channel}>.")


async def setup(bot):
    await bot.add_cog(LogCommands(bot))
