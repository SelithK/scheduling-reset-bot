"""Small helpers shared by the command files. Files starting with _ are never
loaded as cogs."""
from __future__ import annotations

DAYS_HELP = "Examples: mon wed fri  |  weekdays  |  weekends  |  daily"
TIME_HELP = "Examples: 4:30 AM  |  4am  |  16:30  |  noon  |  midnight"
ZONE_HELP = "Examples: America/Chicago, Europe/London, or Eastern / Central / Pacific"


async def reply(interaction, message: str):
    """Answer privately, so only the person who ran the command sees it."""
    await interaction.response.send_message(message, ephemeral=True)


def settings_for(interaction):
    """The settings of the server the command was run in."""
    return interaction.client.store.get(interaction.guild_id)


def save(interaction, gs):
    """Save a server's settings (this also re-checks whether today's run is still to come)."""
    interaction.client.store.commit(gs)
