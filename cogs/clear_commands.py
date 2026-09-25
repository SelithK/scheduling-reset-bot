"""
Manual clearing, for the server the command is used in:
    /clearnow                       delete EVERYTHING in every listed channel
    /clearnow amount:50             delete up to the 50 newest messages in each listed channel
    /clearnow channel:#raid-a       only that channel (it must be on the list)
    /clearnow amount:50 channel:#raid-a
Always asks for confirmation first.

And how many messages the SCHEDULED reset deletes (default: everything):
    /resetamount set amount:50      scheduled resets delete only the 50 newest per channel
    /resetamount all                back to deleting everything
All of them need the Manage Server permission.
"""
from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import clearing
import config
import deletion_log
import timeutils
from cogs._common import reply, save, settings_for


async def clear_targets(bot, targets, amount, source: str) -> list:
    """Clear each channel, log what was deleted (if the server has a log channel),
    and return one result line per channel."""
    lines = []
    for ch in targets:
        try:
            messages = await clearing.clear_channel(ch, amount)
            n = len(messages)
            await deletion_log.send_deletion_log(bot, ch, messages, source)
            lines.append(f"• {ch.mention}: deleted {n} message(s)" if n else f"• {ch.mention}: nothing to delete")
        except discord.Forbidden:
            lines.append(f"• {ch.mention}: I'm missing permissions there (Manage Messages, Read Message History)")
        except discord.HTTPException as e:
            lines.append(f"• {ch.mention}: failed (Discord error {e.status})")
    return lines


class ConfirmClear(discord.ui.View):
    """The Delete / Cancel buttons shown before anything is removed."""

    def __init__(self, origin: discord.Interaction, targets: list, amount: Optional[int]):
        super().__init__(timeout=60)
        self.origin = origin          # the original /clearnow interaction
        self.targets = targets
        self.amount = amount

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.origin.user.id   # only whoever ran the command

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Deleting messages...", view=None)
        lines = await clear_targets(interaction.client, self.targets, self.amount, f"/clearnow by {interaction.user}")
        what = "all messages" if self.amount is None else f"up to {self.amount} newest messages"
        print(f"[OK]   /clearnow by {interaction.user} ({interaction.user.id}) in server "
              f"{interaction.guild_id}: {what}, {len(self.targets)} channel(s)")
        try:
            await interaction.edit_original_response(content="**Done.**\n" + "\n".join(lines))
        except discord.HTTPException:
            pass   # the interaction expired during a very long clear; the deletion still finished

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelled. Nothing was deleted.", view=None)

    async def on_timeout(self):
        try:
            await self.origin.edit_original_response(content="Timed out. Nothing was deleted.", view=None)
        except discord.HTTPException:
            pass


class ClearCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---- /resetamount: how much the SCHEDULED reset deletes -------------------

    resetamount = app_commands.Group(
        name="resetamount",
        description="Choose how many messages each scheduled reset deletes",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @resetamount.command(name="set", description="Scheduled resets delete only the newest N messages per channel")
    @app_commands.describe(amount="How many of the newest messages to delete in each channel per scheduled reset")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def amount_set(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, config.MAX_CLEAR_AMOUNT],
    ):
        gs = settings_for(interaction)
        gs.amount = amount
        save(interaction, gs)
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    @resetamount.command(name="all", description="Scheduled resets delete every message (the default)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def amount_all(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        gs.amount = None
        save(interaction, gs)
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    # ---- /clearnow: delete right now ------------------------------------------

    @app_commands.command(name="clearnow", description="Delete messages in this server's listed channels right now")
    @app_commands.describe(
        amount="How many of the newest messages to delete in each channel. Leave empty to delete everything",
        channel="Only this channel (it must be on the list). Leave empty for every listed channel",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clearnow(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, config.MAX_CLEAR_AMOUNT]] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        gs = settings_for(interaction)
        if not gs.channels:
            return await reply(interaction, "No channels are set up for this server yet. Add one with `/resetchannels add`.")

        if channel is not None:
            if channel.id not in gs.channels:
                return await reply(interaction, f"{channel.mention} isn't on the list. Add it with `/resetchannels add` first.")
            targets = [channel]
        else:
            targets = [ch for cid in gs.channels if (ch := self.bot.get_channel(cid)) is not None]
            if not targets:
                return await reply(interaction, "I can't find any of the saved channels. Check `/resetchannels list`.")

        what = "**all messages**" if amount is None else f"up to the **{amount} newest messages**"
        shown = ", ".join(ch.mention for ch in targets[:10])
        if len(targets) > 10:
            shown += f" and {len(targets) - 10} more"
        view = ConfirmClear(interaction, targets, amount)
        await interaction.response.send_message(
            f"This will delete {what} in {shown}.\nThis can't be undone.",
            view=view,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ClearCommands(bot))
