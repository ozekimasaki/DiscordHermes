"""Configuration loading."""

from __future__ import annotations

from dataclasses import dataclass
import os

from .errors import ConfigError


@dataclass(frozen=True)
class DiscordAdminConfig:
    """Runtime configuration for the MCP server."""

    bot_token: str
    api_base_url: str = "https://discord.com/api/v10"
    audit_db_path: str = ".state\\discord-admin.db"
    request_timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> "DiscordAdminConfig":
        bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if not bot_token:
            raise ConfigError(
                "DISCORD_BOT_TOKEN is required. Use the launcher script or pass the token explicitly to the MCP server."
            )

        api_base_url = os.getenv("DISCORD_API_BASE_URL", cls.api_base_url).strip() or cls.api_base_url
        audit_db_path = os.getenv("DISCORD_ADMIN_DB_PATH", cls.audit_db_path).strip() or cls.audit_db_path

        raw_timeout = os.getenv("DISCORD_REQUEST_TIMEOUT_SECONDS", str(cls.request_timeout_seconds)).strip()
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ConfigError("DISCORD_REQUEST_TIMEOUT_SECONDS must be numeric.") from exc

        return cls(
            bot_token=bot_token,
            api_base_url=api_base_url.rstrip("/"),
            audit_db_path=audit_db_path,
            request_timeout_seconds=timeout,
        )

