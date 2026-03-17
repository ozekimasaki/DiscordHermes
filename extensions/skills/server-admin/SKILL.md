---
name: server-admin
description: Safely manage Discord roles, channels, members, and moderation actions through the discord_admin MCP server.
version: 0.1.0
metadata:
  hermes:
    tags: [discord, admin, channels, roles]
    category: operations
---
# Server Admin

## When to Use

Use this skill when the user wants Hermes to manage a Discord server through the Discord admin MCP server.

This skill is specifically for:

- guild, role, channel, category, and member inspection
- role management
- category and channel management
- channel lock and archive workflows
- member administration and moderation
- one-shot exports and reports

## Procedure

1. Start with read tools to resolve IDs and confirm the current server state.
2. Explain the intended action briefly before taking write actions.
3. Use the smallest safe tool that can complete the request.
4. Treat `archive_channel` as move + lock + preserve, never as delete.
5. Prefer reversible actions such as inspect, move, rename, timeout, or unlock before destructive actions such as kick or ban.
6. Summarize the result and mention that the action is audit-logged.

## Guardrails

- Never invent guild, role, channel, category, or user IDs.
- Prefer `list_roles`, `list_channels`, `list_categories`, `list_members`, and `search_members` before write operations.
- Do not use destructive actions that are not explicitly exposed by the MCP server.
- Prefer `move_channel_to_category` over delete-and-recreate workflows.
- `lock_channel` preserves prior explicit allows so `unlock_channel` can remove the deny without needing stored state.
- Prefer `timeout_member` over `kick_member` or `ban_member` when a reversible moderation action can solve the request.
- If a request asks for broad or risky permissions changes, narrow the action or ask for a safer operation.

## Verification

- The target role, member, or channel appears in follow-up read results.
- The final response reports what changed.
- The operation leaves an audit entry in the MCP audit database.

