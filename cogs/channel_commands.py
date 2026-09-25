"""
Slash commands that control WHICH channels get cleared, for the server they're
used in:
    /resetchannels list | add | remove | cleanup
All of them need the Manage Server permission.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import timeutils
from cogs._common import reply, save, settings_for


class ChannelCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    resetchannels = app_commands.Group(
        name="resetchannels",
        description="Choose which channels get cleared",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @resetchannels.command(name="list", description="Show the channels cleared in this server")
    async def channels_list(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        found = [ch for cid in gs.channels if (ch := self.bot.get_channel(cid)) is not None]
        if found:
            lines = "\n".join(f"• {ch.mention}" for ch in found)
            msg = f"**Channels cleared in this server ({len(found)}):**\n{lines}"
        else:
            msg = "No channels are set up for this server yet. Add one with `/resetchannels add`."
        missing = len(gs.channels) - len(found)
        if missing:
            msg += (
                f"\n\n{missing} saved channel(s) can't be found (deleted, or I can't see them). "
                "Run `/resetchannels cleanup` to drop them."
            )
        await reply(interaction, msg + "\n\n" + timeutils.describe_schedule(gs))

    @resetchannels.command(name="add", description="Add a channel to be cleared")
    @app_commands.describe(channel="The text channel to clear on the schedule")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channels_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        gs = settings_for(interaction)
        if channel.id == gs.log_channel:
            return await reply(
                interaction,
                f"{channel.mention} is this server's deletion log channel, so it can't also be cleared. "
                "Change the log channel with `/resetlog set` or turn it off with `/resetlog off` first.",
            )
        if channel.id in gs.channels:
            return await reply(interaction, f"{channel.mention} is already on the list.")
        gs.channels.append(channel.id)
        save(interaction, gs)
        perms = channel.permissions_for(channel.guild.me)
        missing = [
            name for name, ok in (
                ("View Channel", perms.view_channel),
                ("Read Message History", perms.read_message_history),
                ("Manage Messages", perms.manage_messages),
            ) if not ok
        ]
        msg = f"Added {channel.mention}. It will be cleared on the schedule."
        if missing:
            msg += (
                f"\nHeads up: I'm missing **{', '.join(missing)}** in that channel, so the "
                "reset will fail there until that's fixed."
            )
        await reply(interaction, msg)

    @resetchannels.command(name="remove", description="Stop clearing a channel")
    @app_commands.describe(channel="The channel to stop clearing")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channels_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        gs = settings_for(interaction)
        if channel.id not in gs.channels:
            return await reply(interaction, f"{channel.mention} isn't on the list.")
        gs.channels.remove(channel.id)
        save(interaction, gs)
        await reply(interaction, f"Removed {channel.mention}. It will no longer be cleared.")

    @resetchannels.command(name="cleanup", description="Drop saved channels that no longer exist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channels_cleanup(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        gone = [cid for cid in gs.channels if self.bot.get_channel(cid) is None]
        if not gone:
            return await reply(interaction, "Nothing to clean up. Every saved channel is still there.")
        gs.channels = [cid for cid in gs.channels if cid not in gone]
        save(interaction, gs)
        ids = ", ".join(f"`{cid}`" for cid in gone)
        await reply(interaction, f"Removed {len(gone)} channel(s) I can't find: {ids}")


async def setup(bot):
    await bot.add_cog(ChannelCommands(bot))
