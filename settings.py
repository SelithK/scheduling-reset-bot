"""
Per-server settings. Each server the bot is in gets its own small JSON file in
config.DATA_DIR (named after the server's ID), so one server's schedule never
affects another's, and code updates never touch the data.
"""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from timeutils import ZONE_LOOKUP


@dataclass
class GuildSettings:
    guild_id: int
    days: set = field(default_factory=lambda: set(config.DEFAULT_DAYS))
    time: datetime.time = config.DEFAULT_RESET_TIME
    tz_name: str = config.DEFAULT_TIMEZONE
    channels: list = field(default_factory=list)
    amount: int | None = None               # newest messages per channel per scheduled reset; None = all
    log_channel: int | None = None          # where deleted messages are logged; None = no logging
    last_run: datetime.date | None = None   # runtime only, not saved

    # ---- loading / saving -------------------------------------------------

    @classmethod
    def from_dict(cls, guild_id: int, data) -> "GuildSettings":
        """Build settings from saved data. Anything missing or invalid uses defaults."""
        gs = cls(guild_id)
        if not isinstance(data, dict):
            return gs
        try:
            days = {int(d) for d in data.get("days", []) if 0 <= int(d) <= 6}
            if days:
                gs.days = days
        except (TypeError, ValueError):
            pass
        zone = ZONE_LOOKUP.get(str(data.get("timezone", "")).lower())
        if zone:
            gs.tz_name = zone
        try:
            gs.time = datetime.datetime.strptime(data["time"], "%H:%M").time()
        except (KeyError, TypeError, ValueError):
            pass
        if "channels" in data:   # a saved list wins, even an empty one
            try:
                gs.channels = list(dict.fromkeys(int(c) for c in data["channels"]))
            except (TypeError, ValueError):
                pass
        amount = data.get("amount")
        if isinstance(amount, int) and not isinstance(amount, bool) and 1 <= amount <= config.MAX_CLEAR_AMOUNT:
            gs.amount = amount
        log_channel = data.get("log_channel")
        if isinstance(log_channel, int) and not isinstance(log_channel, bool) and log_channel > 0:
            gs.log_channel = log_channel
        return gs

    def to_dict(self) -> dict:
        return {
            "days": sorted(self.days),
            "time": self.time.strftime("%H:%M"),
            "timezone": self.tz_name,
            "channels": list(self.channels),
            "amount": self.amount,
            "log_channel": self.log_channel,
        }

    # ---- schedule logic ---------------------------------------------------

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)

    def now(self) -> datetime.datetime:
        """Now, in this server's timezone."""
        return datetime.datetime.now(self.tz)

    def resync_today(self) -> None:
        """
        Re-decide whether today's reset is still to come. If the reset time
        hasn't passed yet today (in this server's timezone), it will run at that
        time today. If it has passed, today counts as done, so loading or
        changing settings never fires a surprise catch-up reset.
        """
        now = self.now()
        self.last_run = now.date() if now.time() >= self.time else None

    def is_due(self, now: datetime.datetime | None = None) -> bool:
        now = now or self.now()
        return (
            now.weekday() in self.days
            and now.time() >= self.time
            and self.last_run != now.date()
        )

    def upcoming_runs(self, count: int = 1) -> list:
        """The next `count` times the reset will run, given the current settings."""
        now = self.now()
        runs = []
        for offset in range(15):
            day = now.date() + datetime.timedelta(days=offset)
            if day.weekday() not in self.days:
                continue
            if day == now.date() and self.last_run == day:
                continue   # already ran (or was counted as done) today
            runs.append(datetime.datetime.combine(day, self.time, tzinfo=self.tz))
            if len(runs) == count:
                break
        return runs


class SettingsStore:
    """Loads and saves GuildSettings, one file per server."""

    def __init__(self, directory: Path = config.DATA_DIR):
        self.directory = Path(directory)
        self._cache: dict[int, GuildSettings] = {}

    def _path(self, guild_id: int) -> Path:
        return self.directory / f"{guild_id}.json"

    def has_saved(self, guild_id: int) -> bool:
        return self._path(guild_id).exists()

    def get(self, guild_id: int) -> GuildSettings:
        """This server's settings (defaults if it has never saved any)."""
        gs = self._cache.get(guild_id)
        if gs is None:
            path = self._path(guild_id)
            try:
                data = json.loads(path.read_text())
            except FileNotFoundError:
                data = {}
            except ValueError:
                # Never silently overwrite a damaged file: keep a copy first.
                backup = path.with_suffix(".corrupt")
                print(f"[WARN] settings for server {guild_id} were unreadable; "
                      f"kept a copy as {backup.name} and using defaults")
                path.replace(backup)
                data = {}
            gs = GuildSettings.from_dict(guild_id, data)
            gs.resync_today()
            self._cache[guild_id] = gs
        return gs

    def commit(self, gs: GuildSettings) -> None:
        """Call after changing anything: re-checks today's run, then saves."""
        gs.resync_today()
        self._cache[gs.guild_id] = gs
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(gs.guild_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(gs.to_dict(), indent=2))
        tmp.replace(path)   # atomic swap, so a crash can't leave a half-written file


def migrate_legacy(bot, store: SettingsStore) -> None:
    """
    One-time import of the old single-server reset_settings.json into
    per-server files. A server gets the old settings if it owns at least one of
    the old channels (or if the old file had no channels and the bot is in only
    one server). The old file is then renamed so this never runs twice.
    """
    path = config.LEGACY_SETTINGS_FILE
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        old_channels = [int(c) for c in data.get("channels", [])]
    except (ValueError, TypeError, AttributeError, OSError):
        print(f"[WARN] {path.name} is unreadable, skipping the import")
        return

    migrated = []
    for guild in bot.guilds:
        if store.has_saved(guild.id):
            continue
        mine = []
        for cid in old_channels:
            owner = getattr(bot.get_channel(cid), "guild", None)
            if owner is not None and owner.id == guild.id:
                mine.append(cid)
        only_server = not old_channels and len(bot.guilds) == 1
        if not mine and not only_server:
            continue
        store.commit(GuildSettings.from_dict(guild.id, {**data, "channels": mine}))
        migrated.append(guild.name)

    try:
        path.rename(path.with_name(path.name + ".migrated"))
    except OSError:
        pass
    print(f"[OK]   imported old settings for: {', '.join(migrated) or 'no servers'}")
