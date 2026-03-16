"""Launcher that resolves repo imports and loads Hermes .env before starting the MCP server."""

from __future__ import annotations

from pathlib import Path
import os
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a minimal .env file using only the standard library."""

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def load_hermes_env(hermes_home: Path) -> dict[str, str]:
    """Load Hermes .env values without overwriting explicit process env."""

    env_file = hermes_home / ".env"
    if not env_file.exists():
        return {}

    loaded = parse_dotenv(env_file)
    for key, value in loaded.items():
        os.environ.setdefault(key, value)
    return loaded


def default_hermes_home() -> Path:
    raw = os.getenv("HERMES_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def main() -> int:
    hermes_home = default_hermes_home()
    load_hermes_env(hermes_home)

    os.environ.setdefault("DISCORD_ADMIN_DB_PATH", str(REPO_ROOT / ".state" / "discord-admin.db"))

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from extensions.mcp.discord_admin_server.server import main as server_main

    return server_main()


if __name__ == "__main__":
    raise SystemExit(main())

