# Hermes Discord Admin Extension

This repository is a companion layer for a [Hermes](https://github.com/NousResearch/hermes-agent)-based Discord admin bot.

It keeps Hermes upstream untouched and adds:

- a newline-delimited stdio MCP server for Discord admin actions
- a Hermes skill (`server-admin`) that describes safe admin workflows
- example Hermes configuration (`.env` and `config.yaml`)
- a launcher that reads the Hermes `.env` without duplicating the Discord token in `config.yaml`
- cross-platform setup helpers (Python installers plus PowerShell/shell wrappers)

The MCP server and its supporting core are written in **pure Python using only the standard library** (no third-party runtime dependencies).

## Scope

The current admin surface is MCP-first and focuses on Discord management workflows that Hermes can invoke safely:

- guild, category, channel, role, and member inspection
- role lifecycle updates
- category and text channel creation
- channel rename/topic/lock/unlock/archive/move workflows
- member moderation helpers such as nickname updates, timeouts, and explicit kick/ban/unban actions
- one-shot export/report helpers such as member CSV export and announcement posting

`archive_channel` is intentionally defined as **move + lock + preserve**, not delete.

This extension does **not** introduce persistent jobs such as reminders or watch loops. It is intentionally focused on synchronous Discord administration.

Destructive actions are exposed as explicit tools rather than hidden behind broad generic commands, and successful or failed write actions are audit-logged to a local SQLite database.

## Main features

The MCP server (`discord-admin`) exposes the following tools, grouped by operator-facing family:

### Inspection

| Tool | Purpose |
| --- | --- |
| `get_guild_summary` | Return high-level guild metadata. |
| `list_categories` | List category channels in a guild. |
| `list_channels` | List channels, optionally scoped to one category. |
| `list_roles` | List roles in a guild. |
| `list_members` | List guild members, optionally continuing after a member. |
| `search_members` | Search members by username, nickname, or global name prefix. |
| `get_member` | Return details for a single guild member. |
| `list_members_by_role` | List members who currently hold a given role. |

### Role management

| Tool | Purpose |
| --- | --- |
| `create_role` | Create a new role. |
| `update_role` | Update mutable fields on an existing role. |
| `assign_role` | Assign an existing role to a member. |
| `remove_role` | Remove a role from a member. |

### Channel and category management

| Tool | Purpose |
| --- | --- |
| `create_category` | Create a new category channel. |
| `create_text_channel` | Create a text channel, optionally inside a category. |
| `rename_channel` | Rename an existing channel. |
| `set_channel_topic` | Update a text channel topic. |
| `lock_channel` | Deny send-message permission for selected roles (reversible). |
| `unlock_channel` | Clear explicit send-message denies for selected roles. |
| `archive_channel` | Soft-archive a channel (move + lock + preserve). |
| `move_channel_to_category` | Move a channel into another category. |

### Member administration and moderation

| Tool | Purpose |
| --- | --- |
| `set_member_nickname` | Set a member nickname. |
| `timeout_member` | Apply a communication timeout (1–40320 minutes). |
| `clear_member_timeout` | Remove an active timeout. |
| `kick_member` | Kick a member. |
| `ban_member` | Ban a member (optionally deleting recent messages). |
| `unban_member` | Remove an existing guild ban. |

### Reporting

| Tool | Purpose |
| --- | --- |
| `export_members_csv` | Export a CSV snapshot of members, optionally filtered by role. |
| `post_announcement` | Send a message into a channel. |

## Requirements

- Python **3.11+** (see `pyproject.toml`; the standard library is the only runtime dependency)
- `curl` and `git` available for the Raspberry Pi bootstrap flow
- A Discord bot token with the permissions required for the actions you invoke
- Hermes itself, installed separately, to run the gateway that drives the MCP server

## Repository layout

- `extensions/mcp/discord_admin_server/` - Discord REST wrapper, audit store, and stdio MCP server
- `extensions/skills/server-admin/` - Hermes skill definition and reference notes
- `config/hermes/` - example `.env` and `config.yaml`
- `scripts/` - launcher, installers, and platform setup helpers
- `tests/` - stdlib `unittest` coverage for the pure-Python core
- `pyproject.toml` - package metadata and the `discord-admin-mcp` entry point
- `導入手順.md` / `Ubuntu更新手順.md` - Japanese setup and update guides

## Recommended runtime model

Run Hermes and this extension in the **same WSL2/Linux environment**.

The extension repo should be cloned or copied into that environment, then installed into the Hermes home directory with the helper below. This keeps Hermes upstream untouched and avoids hard-coding secrets into `config.yaml`.

## Raspberry Pi 400 target

The intended deployment target is a **Raspberry Pi 400** running a Linux distribution such as **Raspberry Pi OS Bookworm 64-bit**.

Recommended assumptions:

- Linux on ARM
- Python 3.11 available
- `curl` and `git` available
- Hermes installed with the official installer

For a Pi-oriented bootstrap flow, use:

```bash
python3 scripts/bootstrap_rpi.py --dry-run
python3 scripts/bootstrap_rpi.py
```

That script:

- installs Hermes with the official upstream installer if `hermes` is missing
- installs this extension into `~/.hermes`
- writes a repo-root-aware MCP config snippet
- keeps the Discord token in `~/.hermes/.env`

Use `--dry-run` to print the planned commands and notes without executing them, and `--skip-hermes-install` to avoid running the upstream installer even when `hermes` is missing.

After bootstrap, you still need to:

- set `DISCORD_BOT_TOKEN` and `DISCORD_ALLOWED_USERS` in `~/.hermes/.env`
- merge `~/.hermes/discord-admin.config.snippet.yaml` into `~/.hermes/config.yaml`
- run `hermes gateway setup` or configure Discord manually
- start the gateway with `hermes gateway`

For a persistent Pi deployment, Hermes already provides Linux service management:

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

## Install into an existing Hermes home

From the same environment where Hermes runs:

```bash
python scripts/install_extension.py --hermes-home ~/.hermes
```

This will:

- sync the `server-admin` skill into `~/.hermes/skills/server-admin`
- write `~/.hermes/discord-admin.env.example`
- write `~/.hermes/discord-admin.config.snippet.yaml`
- initialize `~/.hermes/.env` and `~/.hermes/config.yaml` only if they do not already exist

Pass `--force` to overwrite an existing skill directory. If you already have a Hermes setup, merge the generated snippet into your existing `config.yaml`.

## Running the MCP server directly

Set the bot token first, then start the launcher.

PowerShell:

```powershell
$env:DISCORD_BOT_TOKEN = "replace-me"
python scripts\launch_discord_admin_mcp.py
```

Bash:

```bash
export DISCORD_BOT_TOKEN="replace-me"
python scripts/launch_discord_admin_mcp.py
```

The launcher loads `~/.hermes/.env` (or `$HERMES_HOME/.env`) without overwriting variables already set in the process environment, then starts the server. The server speaks newline-delimited JSON-RPC over stdio, which matches the MCP stdio transport.

The package also installs a `discord-admin-mcp` console script (see `pyproject.toml`) that starts the server directly from `extensions.mcp.discord_admin_server.server:main`. Unlike the launcher, this entry point does not load a Hermes `.env`, so `DISCORD_BOT_TOKEN` must already be present in the environment.

## Configuration

Configuration is read from environment variables (see `extensions/mcp/discord_admin_server/config.py`):

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DISCORD_BOT_TOKEN` | yes | — | Discord bot token used for REST calls. |
| `DISCORD_API_BASE_URL` | no | `https://discord.com/api/v10` | Discord REST base URL. |
| `DISCORD_ADMIN_DB_PATH` | no | `.state\discord-admin.db` | SQLite audit database path. |
| `DISCORD_REQUEST_TIMEOUT_SECONDS` | no | `15` | Per-request timeout in seconds. |

Additional variables referenced by the example `.env` and helper scripts include `DISCORD_ALLOWED_USERS` and `DISCORD_HOME_CHANNEL`, which are consumed on the Hermes side.

See the example files:

- `config/hermes/.env.example`
- `config/hermes/config.example.yaml`

The recommended path is to generate a repo-root-aware snippet with:

```bash
python scripts/install_extension.py --hermes-home ~/.hermes
```

That script renders the launcher path for the current checkout and avoids duplicating `DISCORD_BOT_TOKEN` inside `config.yaml`.

## Development

Run the standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

There are no third-party runtime dependencies and no configured linter, type checker, or formatter in this repository. The audit store writes to the path in `DISCORD_ADMIN_DB_PATH` (default `.state/discord-admin.db`).

> Note: `tests/test_install_extension.py` and several PowerShell helper scripts assume a Windows/WSL layout, so a small number of path-oriented tests are Windows-specific and may not pass on other platforms.

## Additional documentation

Japanese guides are included for the primary deployment and maintenance flows:

- `導入手順.md` - Raspberry Pi 400 setup guide
- `Ubuntu更新手順.md` - updating the repository on Ubuntu

## License

MIT (see the `license` field in `pyproject.toml`).
