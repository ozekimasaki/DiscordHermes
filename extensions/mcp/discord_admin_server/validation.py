"""Input validation helpers for tool handlers."""

from __future__ import annotations

import re
from typing import Any

from .errors import ValidationError

_SNOWFLAKE_RE = re.compile(r"^\d{5,25}$")


def require_mapping(arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ValidationError("Tool arguments must be a JSON object.")
    return arguments


def require_snowflake(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, (str, int)):
        raise ValidationError(f"{key} must be a Discord snowflake string.")
    text = str(value).strip()
    if not _SNOWFLAKE_RE.match(text):
        raise ValidationError(f"{key} must look like a Discord snowflake.")
    return text


def optional_snowflake(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    return require_snowflake(arguments, key)


def require_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string.")
    return value.strip()


def optional_string(arguments: dict[str, Any], key: str, default: str | None = None) -> str | None:
    value = arguments.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string.")
    return value.strip() or default


def optional_boolean(arguments: dict[str, Any], key: str, default: bool = False) -> bool:
    value = arguments.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError(f"{key} must be a boolean.")
    return value


def optional_integer(
    arguments: dict[str, Any], key: str, default: int | None = None, minimum: int | None = None
) -> int | None:
    value = arguments.get(key)
    if value is None:
        return default
    if not isinstance(value, int):
        raise ValidationError(f"{key} must be an integer.")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{key} must be >= {minimum}.")
    return value


def optional_permissions(arguments: dict[str, Any], key: str = "permissions", default: str = "0") -> str:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, int):
        if value < 0:
            raise ValidationError(f"{key} must be >= 0.")
        return str(value)
    if isinstance(value, str) and value.isdigit():
        return value
    raise ValidationError(f"{key} must be a non-negative integer or digit string.")


def optional_snowflake_list(arguments: dict[str, Any], key: str) -> list[str]:
    value = arguments.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{key} must be an array of Discord snowflakes.")

    validated: list[str] = []
    for item in value:
        if not isinstance(item, (str, int)):
            raise ValidationError(f"{key} must only contain Discord snowflakes.")
        text = str(item).strip()
        if not _SNOWFLAKE_RE.match(text):
            raise ValidationError(f"{key} must only contain valid Discord snowflakes.")
        validated.append(text)
    return validated

