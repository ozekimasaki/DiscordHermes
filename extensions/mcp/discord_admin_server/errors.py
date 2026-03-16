"""Custom exceptions for the Discord admin MCP server."""


class DiscordAdminError(Exception):
    """Base exception for the project."""


class ConfigError(DiscordAdminError):
    """Raised when required configuration is missing or invalid."""


class ValidationError(DiscordAdminError):
    """Raised when tool input is invalid."""


class ToolExecutionError(DiscordAdminError):
    """Raised when a tool cannot complete its work."""


class DiscordAPIError(DiscordAdminError):
    """Raised when Discord rejects an API request."""

    def __init__(self, status_code: int, message: str, details=None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details

    def __str__(self) -> str:
        return f"Discord API error ({self.status_code}): {self.message}"

