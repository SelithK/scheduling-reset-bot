"""
Settings that belong to the CODE. Edit these by hand.

Per-server settings that people change with slash commands (days, time,
timezone, channels) are NOT stored here. They live in DATA_DIR, one file per
server, so replacing or updating the bot's code never touches them.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Where per-server settings are saved: one JSON file per server.
# Set the BOT_DATA_DIR environment variable to keep this folder OUTSIDE the bot
# folder, so re-extracting or replacing the whole bot folder can never wipe it.
DATA_DIR = Path(os.environ.get("BOT_DATA_DIR", BASE_DIR / "data")) / "guilds"

# The single-server settings file from earlier versions of the bot. If it is
# found, it is imported once into the per-server files and then renamed.
LEGACY_SETTINGS_FILE = BASE_DIR / "reset_settings.json"

# Starting values for a server that hasn't changed anything yet.
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_RESET_TIME = datetime.time(hour=4, minute=0)
DEFAULT_DAYS = frozenset(range(7))   # 0 = Monday ... 6 = Sunday

MAX_PURGE_PASSES = 5   # safety cap on "purge, check, purge again" cycles
MAX_CLEAR_AMOUNT = 10000   # most messages /clearnow can delete per channel in one go

# Deletion log (only used when a server sets a log channel with /resetlog)
LOG_INLINE_LIMIT = 1800               # logs up to this many characters are posted as a message
MAX_LOG_FILE_BYTES = 8 * 1024 * 1024  # bigger transcripts are cut off at this size
CHECK_INTERVAL = 30    # seconds between "is it time yet?" checks
