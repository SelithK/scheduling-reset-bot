"""
Pure helpers: understanding what people type (days, times, timezones) and
turning a server's settings into readable text. Nothing in here talks to
Discord, so it is safe to import from anywhere.
"""
from __future__ import annotations

import datetime
import re
from zoneinfo import available_timezones

# ------------------------------------------------------------------- DAYS ---

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

GROUP_ALIASES = {
    "daily": range(7),
    "everyday": range(7),
    "all": range(7),
    "weekdays": range(5),
    "weekends": (5, 6),
}


def parse_days(text: str) -> set[int]:
    """
    Turn 'mon, wed fri' / 'weekdays' / 'daily' into a set of weekday numbers.
    Raises ValueError(token) on anything it doesn't recognise.
    """
    days: set[int] = set()
    for token in re.split(r"[,\s]+", text.lower().strip()):
        if not token:
            continue
        if token in GROUP_ALIASES:
            days.update(GROUP_ALIASES[token])
            continue
        for i, name in enumerate(DAY_NAMES):
            if len(token) >= 3 and name.lower().startswith(token):
                days.add(i)
                break
        else:
            raise ValueError(token)
    return days


# ------------------------------------------------------------------- TIME ---


def parse_time(text: str) -> datetime.time:
    """
    Turn '4:30 AM' / '4am' / '16:30' / '0430' / 'noon' / 'midnight' into a time.
    Raises ValueError(text) if it can't be understood.
    """
    t = text.strip().lower().replace(".", "")
    if t == "noon":
        return datetime.time(12, 0)
    if t == "midnight":
        return datetime.time(0, 0)
    m = re.fullmatch(r"(\d{1,2})(?::?(\d{2}))?\s*(am|pm)?", t)
    if not m:
        raise ValueError(text)
    hour, minute, suffix = int(m[1]), int(m[2] or 0), m[3]
    if minute > 59:
        raise ValueError(text)
    if suffix:
        if not 1 <= hour <= 12:
            raise ValueError(text)
        hour = hour % 12 + (12 if suffix == "pm" else 0)
    elif hour > 23:
        raise ValueError(text)
    return datetime.time(hour, minute)


def format_time(t: datetime.time) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


# -------------------------------------------------------------- TIMEZONES ---

# Friendly names people are likely to type. Full IANA names always work too.
ZONE_ALIASES = {
    "eastern": "America/New_York",
    "central": "America/Chicago",
    "mountain": "America/Denver",
    "pacific": "America/Los_Angeles",
    "alaska": "America/Anchorage",
    "hawaii": "Pacific/Honolulu",
    "utc": "UTC",
    "gmt": "Etc/GMT",
    "uk": "Europe/London",
    "london": "Europe/London",
}

ZONE_NAMES = sorted(available_timezones())
ZONE_LOOKUP = {z.lower(): z for z in ZONE_NAMES}


def find_timezone(text: str) -> str:
    """Return the canonical zone name for user input, or raise ValueError."""
    key = text.strip().lower().replace(" ", "_")
    if key in ZONE_ALIASES:
        return ZONE_ALIASES[key]
    if key in ZONE_LOOKUP:
        return ZONE_LOOKUP[key]
    raise ValueError(text)


# ------------------------------------------------------------ DESCRIPTIONS ---
# These take a GuildSettings (see settings.py) as `gs`.


def format_run(gs, run: datetime.datetime, markup: bool = True) -> str:
    when = f"{run.strftime('%A, %b')} {run.day} at {format_time(run.time())} {run.strftime('%Z')}"
    if not markup:
        return when
    if run <= gs.now():
        return f"{when} (any moment now)"
    return f"{when} (<t:{int(run.timestamp())}:R>)"   # Discord shows this as "in 3 hours"


def describe_schedule(gs, markup: bool = True) -> str:
    abbr = gs.now().strftime("%Z")
    when = f"{format_time(gs.time)} {abbr} ({gs.tz_name})"
    if len(gs.days) == 7:
        text = f"Reset runs **every day** at {when}."
    else:
        names = ", ".join(DAY_NAMES[d][:3] for d in sorted(gs.days))
        text = f"Reset runs on **{names}** at {when}."
    if gs.amount is None:
        text += "\nEach run deletes all messages in every listed channel."
    else:
        text += f"\nEach run deletes only the {gs.amount} newest messages in every listed channel."
    if gs.log_channel:
        where = f"<#{gs.log_channel}>" if markup else f"channel {gs.log_channel}"
        text += f"\nDeleted messages are logged to {where}."
    else:
        text += "\nDeleted messages are not logged (no log channel set)."
    runs = gs.upcoming_runs(1)
    if runs:
        text += f"\nNext run: {format_run(gs, runs[0], markup)}"
    if not gs.channels:
        text += "\nNo channels are set up yet, so nothing will be cleared. Add one with /resetchannels add."
    return text
