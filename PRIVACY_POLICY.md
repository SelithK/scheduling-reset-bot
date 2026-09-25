# Privacy Policy

*Last updated: 09-24-2026*

This Privacy Policy explains what data this Discord bot "scheduling-reset-bot" collects
and how it's used.

## Information the Bot stores

For each server it's added to, the Bot stores:
- The server's Discord ID
- The IDs of the channels chosen for scheduled clearing
- The reset schedule (days, time, timezone), the deletion amount setting, and
  the deletion log channel ID, if one is set

## Information the Bot processes but does not permanently store

- **Message content of deleted messages.** If a server sets a deletion log
  channel, the text and metadata (author, timestamp, attachment names) of
  messages the Bot deletes are posted to that channel at the time of
  deletion. The Bot does not keep a separate copy anywhere else; the record
  that exists afterward is the message the Bot posted in that channel, which
  is visible to anyone who can read it and is under that server's control.
- **Discord user IDs and display names** appear in deletion logs (as the
  author of a deleted message) and in command usage (as the person who ran a
  command), but are not stored outside of that.

## How this information is used

Solely to operate the Bot's features: running the scheduled clearing, the
`/clearnow` command, and the deletion log. It is not used for advertising,
profiling, or any purpose unrelated to the Bot's functionality.

## Data sharing

This data is not sold, rented, or shared with third parties, except where
required by law.

## Data retention and deletion

Per-server settings are kept for as long as the Bot remains in a server.
Removing the Bot from a server does not automatically delete its saved
settings; to request deletion, use the contact method listed under Contact below.

## Where data is stored

Server settings are stored on a private server rented from a third-party
hosting provider. They are not shared with any analytics service or data broker.

## Your rights

You can stop using the Bot at any time by removing it from your server. If
you administer a server the Bot is in, you can review and change its stored
settings using the Bot's own commands (`/resetdays view`, `/resetchannels
list`, `/resetlog view`), or ask the operator to delete them.

## Changes to this policy

This policy may be updated from time to time. Continued use of the Bot after
a change means you accept the updated policy.

## Contact

Questions about this policy: stephk @ discord
