# Operating Rules

- Resolve IDs with read tools before calling write tools.
- Keep `discord.require_mention: true` unless the deployment intentionally uses a dedicated admin channel.
- Keep `group_sessions_per_user: true` to avoid shared-channel context collisions.
- Restrict use through `DISCORD_ALLOWED_USERS`.
- Keep destructive Discord actions out of the exposed MCP surface until approval flows exist.
- Use `archive_channel` for preservation, not deletion.

