"""
Slash commands that control WHEN the reset runs, for the server they're used in:
    /resetdays view | set | add | remove
    /resettime
    /resettimezone
    /resetnext
All of them need the Manage Server permission.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import timeutils
from cogs._common import DAYS_HELP, TIME_HELP, ZONE_HELP, reply, save, settings_for


async def _days_or_reply(interaction: discord.Interaction, text: str):
    """Parse a days argument; if it's bad, tell the user and return None."""
    try:
        days = timeutils.parse_days(text)
    except ValueError as e:
        await reply(interaction, f"I didn't understand `{e.args[0]}`. {DAYS_HELP}")
        return None
    if not days:
        await reply(interaction, f"Give me at least one day. {DAYS_HELP}")
        return None
    return days


class ScheduleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---- /resetdays ---------------------------------------------------------

    resetdays = app_commands.Group(
        name="resetdays",
        description="Choose which days the channel reset runs",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @resetdays.command(name="view", description="Show this server's reset days, time and timezone")
    async def days_view(self, interaction: discord.Interaction):
        await reply(interaction, timeutils.describe_schedule(settings_for(interaction)))

    @resetdays.command(name="set", description="Replace the reset days")
    @app_commands.describe(days=DAYS_HELP)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def days_set(self, interaction: discord.Interaction, days: str):
        new_days = await _days_or_reply(interaction, days)
        if new_days is None:
            return
        gs = settings_for(interaction)
        gs.days = new_days
        save(interaction, gs)
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    @resetdays.command(name="add", description="Add days to the reset schedule")
    @app_commands.describe(days=DAYS_HELP)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def days_add(self, interaction: discord.Interaction, days: str):
        to_add = await _days_or_reply(interaction, days)
        if to_add is None:
            return
        gs = settings_for(interaction)
        gs.days = gs.days | to_add
        save(interaction, gs)
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    @resetdays.command(name="remove", description="Remove days from the reset schedule")
    @app_commands.describe(days=DAYS_HELP)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def days_remove(self, interaction: discord.Interaction, days: str):
        to_remove = await _days_or_reply(interaction, days)
        if to_remove is None:
            return
        gs = settings_for(interaction)
        remaining = gs.days - to_remove
        if not remaining:
            return await reply(
                interaction,
                "That would remove every day. Keep at least one, or use `/resetdays set` instead.",
            )
        gs.days = remaining
        save(interaction, gs)
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    # ---- /resettime ---------------------------------------------------------

    @app_commands.command(name="resettime", description="Set the time of day the reset runs")
    @app_commands.describe(time=TIME_HELP)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def resettime(self, interaction: discord.Interaction, time: str):
        try:
            new_time = timeutils.parse_time(time)
        except ValueError:
            return await reply(interaction, f"I didn't understand the time `{time}`. {TIME_HELP}")
        gs = settings_for(interaction)
        gs.time = new_time
        save(interaction, gs)   # runs today at the new time if that hasn't passed yet
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    # ---- /resettimezone -----------------------------------------------------

    @app_commands.command(name="resettimezone", description="Set the timezone this server's reset schedule uses")
    @app_commands.describe(timezone=ZONE_HELP)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def resettimezone(self, interaction: discord.Interaction, timezone: str):
        try:
            name = timeutils.find_timezone(timezone)
        except ValueError:
            return await reply(
                interaction,
                f"I don't know the timezone `{timezone}`. Start typing and pick one from the "
                f"suggestions. {ZONE_HELP}",
            )
        gs = settings_for(interaction)
        gs.tz_name = name
        save(interaction, gs)   # re-checks today in the new zone
        await reply(interaction, "Updated. " + timeutils.describe_schedule(gs))

    @resettimezone.autocomplete("timezone")
    async def timezone_autocomplete(self, interaction: discord.Interaction, current: str):
        """Suggest zones as the user types (Discord allows at most 25 suggestions)."""
        q = current.strip().lower().replace(" ", "_")
        choices: dict[str, str] = {}   # value -> label, keeps friendly aliases first
        for alias, zone in timeutils.ZONE_ALIASES.items():
            if q in alias or q in zone.lower():
                choices.setdefault(zone, f"{alias.title()} ({zone})")
        for zone in timeutils.ZONE_NAMES:
            if len(choices) >= 25:
                break
            if q in zone.lower():
                choices.setdefault(zone, zone)
        return [
            app_commands.Choice(name=label[:100], value=zone)
            for zone, label in list(choices.items())[:25]
        ]

    # ---- /resetnext ---------------------------------------------------------

    @app_commands.command(name="resetnext", description="Show when the next resets are scheduled")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def resetnext(self, interaction: discord.Interaction):
        gs = settings_for(interaction)
        runs = gs.upcoming_runs(3)
        if not runs:
            return await reply(interaction, "No reset is scheduled. Add days with `/resetdays set`.")
        first = runs[0]
        lines = [
            f"**Next reset:** {timeutils.format_run(gs, first)}",
            f"In your local time: <t:{int(first.timestamp())}:F>",
        ]
        if len(runs) > 1:
            lines.append("\n**After that:**")
            lines += [f"• {timeutils.format_run(gs, r)}" for r in runs[1:]]
        found = sum(1 for cid in gs.channels if self.bot.get_channel(cid) is not None)
        if found:
            lines.append(f"\nClears {found} channel(s) in this server. See `/resetchannels list`.")
        else:
            lines.append("\nNo channels are set up in this server yet. Add one with `/resetchannels add`.")
        await reply(interaction, "\n".join(lines))


async def setup(bot):
    await bot.add_cog(ScheduleCommands(bot))
