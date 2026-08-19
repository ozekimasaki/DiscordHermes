# AGENTS.md

Guidance for coding agents working in this repository. It complements `README.md`;
read that first for the product-level overview.

## What this repository is

A companion layer for a [Hermes](https://github.com/NousResearch/hermes-agent)-based
Discord admin bot. It does not modify Hermes upstream. It provides:

- a stdio MCP server for Discord administration (`discord-admin`)
- a Hermes `server-admin` skill
- example Hermes configuration
- installers and platform setup helpers

The code is **pure Python and uses only the standard library** — there are no
third-party runtime dependencies. Preserve this constraint; do not add external
packages without an explicit request.

## Project structure and entry points

- `extensions/mcp/discord_admin_server/` — MCP server core
  - `server.py` — stdio JSON-RPC MCP server; `main()` is the process entry point
  - `tool_registry.py` — declares every MCP tool, its JSON schema, and its handler
  - `discord_api.py` — Discord REST client built on `urllib`
  - `policies.py` — pure helpers for lock/unlock/archive/move permission patches
  - `audit_store.py` — SQLite-backed audit log (`AuditStore`)
  - `config.py` — `DiscordAdminConfig.from_env()` reads environment variables
  - `validation.py` — argument validation helpers used by the tool handlers
  - `models.py`, `errors.py` — tool definition dataclass and error types
- `extensions/skills/server-admin/` — Hermes skill (`SKILL.md`) and reference notes
- `config/hermes/` — `.env.example` and `config.example.yaml`
- `scripts/`
  - `launch_discord_admin_mcp.py` — launcher that loads the Hermes `.env`, then starts the server
  - `install_extension.py` — installs the skill, env example, and config snippet into a Hermes home
  - `bootstrap_rpi.py` — Raspberry Pi bootstrap flow
  - `*.sh` / `*.ps1` — shell/PowerShell wrappers around the Python helpers
- `tests/` — `unittest` suite for the pure-Python core
- `pyproject.toml` — package metadata; declares the `discord-admin-mcp` console script

Console script entry point (`pyproject.toml`): `discord-admin-mcp = "extensions.mcp.discord_admin_server.server:main"`.

## Setup

- Requires Python **3.11+** (`requires-python = ">=3.11"`).
- No dependency install step is needed for running tests or the server — the standard library is sufficient.
- For an editable/packaged install: `pip install -e .` (uses `setuptools`).

## Build, test, lint, typecheck

- Run tests from the repository root:

  ```bash
  python -m unittest discover -s tests -v
  ```

- Build the package (optional): `python -m build` (requires the `build` package; not vendored here).
- There is **no** configured linter, formatter, or type checker in this repository
  (no `ruff`, `flake8`, `black`, `mypy`, or `pyright` config, and no pre-commit hooks).
  Do not assume one exists or invent commands for one. If you introduce such tooling,
  add its configuration and document it here and in `README.md`.

### Platform note for tests

Some helpers and tests assume a Windows/WSL layout. In particular,
`tests/test_install_extension.py::test_render_config_snippet_uses_launcher_path`
asserts a backslash (`C:\...`) Windows path and does not pass on non-Windows
platforms, where `pathlib` joins with forward slashes. This is a pre-existing
platform assumption, not a regression — do not "fix" it by rewriting the test
unless that is the explicit task, and never edit tests solely to make them pass.

## Coding conventions

- Match the existing style: `from __future__ import annotations`, standard-library
  imports only, type hints on public functions, module-level docstrings.
- Keep imports at the top of the file.
- Add a new MCP tool by appending a `ToolDefinition` in
  `extensions/mcp/discord_admin_server/tool_registry.py`: define its JSON schema
  with `_schema(...)`, validate arguments with the helpers in `validation.py`, and
  route execution through `service.execute(...)` so the action is audit-logged.
- Keep permission/patch logic pure in `policies.py` and covered by `tests/mcp/test_policies.py`.
- Preserve the safety model: destructive actions stay as explicit, separate tools;
  `archive_channel` means move + lock + preserve, never delete.
- Comments are sparse; prefer clear names over narration and match surrounding terseness.

## Configuration and secrets

- Runtime config comes from environment variables (see `config.py`): `DISCORD_BOT_TOKEN`
  (required), `DISCORD_API_BASE_URL`, `DISCORD_ADMIN_DB_PATH`, `DISCORD_REQUEST_TIMEOUT_SECONDS`.
- Never commit real tokens. Keep `DISCORD_BOT_TOKEN` in the Hermes `~/.hermes/.env`
  rather than in `config.yaml`; the launcher loads it via `os.environ.setdefault`.
- The audit database (default `.state/discord-admin.db`) is generated at runtime and
  should not be treated as source.

## Notes and gotchas

- The default branch is `main`; base pull requests on it.
- Discord REST access uses `urllib` — keep that dependency-free approach.
- When adding tools, update the tool tables in `README.md` and, where relevant, the
  `include` lists in `config/hermes/config.example.yaml` and `scripts/install_extension.py`.
- Japanese operator guides (`導入手順.md`, `Ubuntu更新手順.md`) exist; keep them consistent
  if you change the setup or update flows they describe.
