"""
Deleting messages from a channel. Shared by the scheduled reset
(cogs/scheduler.py) and the manual /clearnow command (cogs/clear_commands.py),
so both behave the same way.
"""
from __future__ import annotations

import asyncio

import config

# One lock per channel, so a scheduled reset and a manual /clearnow can never
# run on the same channel at the same moment.
_locks: dict[int, asyncio.Lock] = {}


async def has_messages(channel) -> bool:
    async for _ in channel.history(limit=1):
        return True
    return False


async def _empty(channel) -> list:
    """
    Delete everything. Does nothing if the channel is already empty. Repeats
    until the channel is verifiably empty (or the pass cap is hit).
    """
    removed: list = []
    for _ in range(config.MAX_PURGE_PASSES):
        if not await has_messages(channel):
            break
        # limit=None = no cap. Messages under 14 days old are bulk deleted;
        # older ones are deleted one at a time (slower, but handled for you).
        removed.extend(await channel.purge(limit=None))
        await asyncio.sleep(1)   # let Discord catch up before re-checking
    return removed


async def _delete_newest(channel, amount: int) -> list:
    """Delete up to `amount` of the newest messages."""
    return list(await channel.purge(limit=amount))


async def clear_channel(channel, amount: int | None = None) -> list:
    """
    Delete messages from a channel and return the messages that were deleted
    (a list of discord.Message; use len() for the count).
    amount=None deletes everything; a number deletes up to that many of the
    newest messages (fewer if the channel doesn't have that many).
    """
    lock = _locks.setdefault(channel.id, asyncio.Lock())
    async with lock:
        if amount is None:
            return await _empty(channel)
        return await _delete_newest(channel, amount)
