---
name: server-admin
description: Safely manage Discord roles and channels through the discord_admin MCP server.
version: 0.1.0
metadata:
  hermes:
    tags: [discord, admin, channels, roles]
    category: operations
---
# Server Admin

## When to Use

Use this skill when the user wants to manage a Discord server through Hermes.

This skill is specifically for:

- role management
- channel creation
- channel archiving
- channel moves between categories

## Procedure

1. Start with read tools to resolve IDs and confirm the current server state.
2. Explain the intended action briefly before taking write actions.
3. Use the smallest safe tool that can complete the request.
4. Treat `archive_channel` as move + lock + preserve, never as delete.
5. Summarize the result and mention that the action is audit-logged.

## Guardrails

- Never invent guild, role, channel, or category IDs.
- Prefer `list_roles`, `list_channels`, and `list_categories` before write operations.
- Do not use destructive actions that are not explicitly exposed by the MCP server.
- Prefer `move_channel_to_category` over delete-and-recreate workflows.
- If a request asks for broad or risky permissions changes, narrow the action or ask for a safer operation.

## Verification

- The target role or channel appears in follow-up read results.
- The final response reports what changed.
- The operation leaves an audit entry in the MCP audit database.

