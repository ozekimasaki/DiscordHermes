# Hermes Discord Admin Extension

This repository is a companion layer for a Hermes-based Discord admin bot.

It keeps Hermes upstream untouched and adds:

- a newline-delimited stdio MCP server for Discord admin actions
- Hermes skills that describe safe admin workflows
- example Hermes configuration
- a launcher that reads Hermes `.env` without duplicating the Discord token in `config.yaml`
- setup helpers

## Scope

The current admin surface is MCP-first and focuses on Discord management workflows that Hermes can invoke safely:

- guild, category, channel, role, and member inspection
- role lifecycle updates
- category and text channel creation
- channel rename/topic/lock/archive/move workflows
- member moderation helpers such as nickname updates, timeouts, and explicit kick/ban/unban actions
- one-shot export/report helpers such as member CSV export

`archive_channel` is intentionally defined as **move + lock + preserve**, not delete.

This extension does **not** introduce persistent jobs such as reminders or watch loops. It is intentionally focused on synchronous Discord administration.

## Current tool families

The current MCP surface is organized around a few operator-facing groups:

- inspection: guild, category, channel, role, and member lookups
- channel management: create category, create channel, rename, topic updates, move, lock, unlock, archive
- role management: create, update, assign, remove
- member administration: search, nickname update, timeout/clear timeout, kick, ban, unban
- reporting: member CSV export and announcement posting

Destructive actions are exposed as explicit tools rather than hidden behind broad generic commands, and successful or failed write actions are audit-logged.

## Layout

- `extensions/mcp/discord_admin_server/` - Discord REST wrapper, audit store, MCP server
- `extensions/skills/server-admin/` - Hermes skill and references
- `config/hermes/` - example `.env` and `config.yaml`
- `scripts/` - launcher and setup helpers
- `tests/` - stdlib `unittest` coverage for the pure-Python core

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

If you already have a Hermes setup, merge the generated snippet into your existing `config.yaml`.

## Running the MCP server directly

Set the bot token first:

```powershell
$env:DISCORD_BOT_TOKEN = "replace-me"
python scripts\launch_discord_admin_mcp.py
```

The server speaks newline-delimited JSON-RPC over stdio, which matches the MCP stdio transport.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Hermes configuration

See:

- `config\hermes\.env.example`
- `config\hermes\config.example.yaml`

The recommended path is to generate a repo-root-aware snippet with:

```bash
python scripts/install_extension.py --hermes-home ~/.hermes
```

That script renders the launcher path for the current checkout and avoids duplicating `DISCORD_BOT_TOKEN` inside `config.yaml`.

## Current validation status

Verified in this repository:

- stdlib unit tests pass
- the MCP server responds to `initialize`
- the MCP server responds to `tools/list`

Not verified in this environment:

- live `hermes gateway` startup
- real Discord guild E2E

Those require Hermes itself plus a test guild runtime, which is outside the current environment.
