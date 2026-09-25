"""
The deletion log. If a server has set a log channel (/resetlog set), every time
the bot deletes messages it posts a record there: which channel they came from,
who or what triggered it, and the deleted messages themselves. If the server has
no log channel, nothing is posted at all.

Short logs are posted as a message; long ones are attached as a .txt file.
Writing the log can never break a deletion: any problem is printed and skipped.
"""
from __future__ import annotations

import datetime
import io
import re

import discord

import config


def format_message(m, tz, content_visible: bool = True) -> str:
    """One deleted message as readable text (author, time, text, attachments)."""
    when = m.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    author = getattr(m.author, "display_name", None) or str(m.author)
    head = f"[{when}] {author} ({m.author.id}):"

    body = []
    if content_visible and m.content:
        body = m.content.splitlines() or [""]
    extras = []
    if m.attachments:
        extras.append("[attachments] " + ", ".join(a.filename for a in m.attachments))
    if m.embeds:
        extras.append(f"[embeds] {len(m.embeds)}")
    if getattr(m, "stickers", None):
        extras.append("[stickers] " + ", ".join(s.name for s in m.stickers))

    if not content_visible and not extras:
        body = ["(text unavailable)"]
    elif not body and not extras:
        body = ["(no text)"]

    lines = [f"{head} {body[0]}" if body else head]
    lines += [f"    {line}" for line in body[1:]]
    lines += [f"    {line}" for line in extras]
    return "\n".join(lines)


def build_transcript(messages, tz, content_visible: bool = True, max_bytes: int = config.MAX_LOG_FILE_BYTES) -> str:
    """All the messages, oldest first, cut off with a note if it would be too big."""
    blocks, size = [], 0
    for i, m in enumerate(messages):
        block = format_message(m, tz, content_visible)
        block_bytes = len(block.encode("utf-8")) + 1
        if size + block_bytes > max_bytes:
            blocks.append(f"... {len(messages) - i} more message(s) not shown (log size limit)")
            break
        blocks.append(block)
        size += block_bytes
    return "\n".join(blocks)


async def send_deletion_log(bot, channel, messages, source: str) -> None:
    """
    Post a record of `messages`, just deleted from `channel`, to the server's log
    channel. Does nothing if the server has no log channel or nothing was deleted.
    `source` says what caused it, e.g. "scheduled reset" or "/clearnow by Alex".
    """
    try:
        guild = channel.guild
        gs = bot.store.get(guild.id)
        if gs.log_channel is None or not messages:
            return

        log_channel = bot.get_channel(gs.log_channel)
        owner = getattr(log_channel, "guild", None)
        if owner is None or owner.id != guild.id:
            print(f"[WARN] {guild.name}: log channel {gs.log_channel} not found in this server, log skipped")
            return
        if log_channel.id == channel.id:
            return   # never log a channel into itself

        visible = getattr(bot, "message_content_enabled", True)
        limit = min(config.MAX_LOG_FILE_BYTES, getattr(guild, "filesize_limit", config.MAX_LOG_FILE_BYTES))
        ordered = sorted(messages, key=lambda m: m.created_at)
        transcript = build_transcript(ordered, gs.tz, visible, limit)

        now = datetime.datetime.now(gs.tz)
        header = (
            f"**Deleted {len(messages)} message(s)** from #{channel.name} ({channel.mention})\n"
            f"Source: {source} | {now:%Y-%m-%d %H:%M:%S %Z}"
        )
        if not visible:
            header += "\nMessage text isn't included because the bot's Message Content intent is off."

        no_pings = discord.AllowedMentions.none()   # a logged @everyone must never ping again
        if len(header) + len(transcript) <= config.LOG_INLINE_LIMIT:
            safe = transcript.replace("```", "`\u200b``")   # so the text can't break out of the code block
            await log_channel.send(f"{header}\n```\n{safe}\n```", allowed_mentions=no_pings)
        else:
            name = re.sub(r"[^\w-]", "_", channel.name)
            filename = f"deleted-{name}-{now:%Y%m%d-%H%M%S}.txt"
            file = discord.File(io.BytesIO(transcript.encode("utf-8")), filename=filename)
            await log_channel.send(header, file=file, allowed_mentions=no_pings)
    except Exception as e:
        print(f"[WARN] couldn't write the deletion log: {type(e).__name__}: {e}")
