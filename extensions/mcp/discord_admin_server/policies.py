"""Pure helpers for channel archive, lock, and move policies."""

from __future__ import annotations

from typing import Any, Iterable

SEND_MESSAGES_PERMISSION = 1 << 11  # 2048
ROLE_OVERWRITE_TYPE = 0


def prefixed_channel_name(current_name: str, prefix: str | None) -> str:
    if not prefix:
        return current_name
    trimmed = prefix.strip(" -_")
    if not trimmed:
        return current_name
    rendered = f"{trimmed}-{current_name}"
    if current_name.startswith(f"{trimmed}-"):
        return current_name
    return rendered


def deny_send_messages(permission_overwrites: Iterable[dict[str, Any]], role_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Return permission overwrites with SEND_MESSAGES denied for selected roles."""

    target_ids = {str(role_id) for role_id in role_ids}
    updated: list[dict[str, Any]] = []
    seen: set[str] = set()

    for overwrite in permission_overwrites:
        copied = dict(overwrite)
        overwrite_id = str(copied.get("id", ""))
        overwrite_type = int(copied.get("type", ROLE_OVERWRITE_TYPE))

        if overwrite_id in target_ids and overwrite_type == ROLE_OVERWRITE_TYPE:
            allow_bits = int(str(copied.get("allow", "0")))
            deny_bits = int(str(copied.get("deny", "0")))
            deny_bits |= SEND_MESSAGES_PERMISSION
            copied["allow"] = str(allow_bits)
            copied["deny"] = str(deny_bits)
            seen.add(overwrite_id)

        updated.append(copied)

    for role_id in sorted(target_ids - seen):
        updated.append(
            {
                "id": role_id,
                "type": ROLE_OVERWRITE_TYPE,
                "allow": "0",
                "deny": str(SEND_MESSAGES_PERMISSION),
            }
        )

    return updated


def clear_send_messages(permission_overwrites: Iterable[dict[str, Any]], role_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Clear explicit SEND_MESSAGES deny bits for selected roles."""

    target_ids = {str(role_id) for role_id in role_ids}
    updated: list[dict[str, Any]] = []

    for overwrite in permission_overwrites:
        copied = dict(overwrite)
        overwrite_id = str(copied.get("id", ""))
        overwrite_type = int(copied.get("type", ROLE_OVERWRITE_TYPE))

        if overwrite_id in target_ids and overwrite_type == ROLE_OVERWRITE_TYPE:
            allow_bits = int(str(copied.get("allow", "0")))
            deny_bits = int(str(copied.get("deny", "0")))
            copied["allow"] = str(allow_bits)
            copied["deny"] = str(deny_bits & ~SEND_MESSAGES_PERMISSION)
            if copied["allow"] == "0" and copied["deny"] == "0":
                continue

        updated.append(copied)

    return updated


def build_channel_lock_patch(channel: dict[str, Any], lock_role_ids: list[str] | None = None) -> dict[str, Any]:
    """Build the PATCH payload for a channel lock operation."""

    guild_id = str(channel["guild_id"])
    effective_role_ids = lock_role_ids or [guild_id]
    return {
        "permission_overwrites": deny_send_messages(channel.get("permission_overwrites", []), effective_role_ids),
    }


def build_channel_unlock_patch(channel: dict[str, Any], unlock_role_ids: list[str] | None = None) -> dict[str, Any]:
    """Build the PATCH payload for a channel unlock operation."""

    guild_id = str(channel["guild_id"])
    effective_role_ids = unlock_role_ids or [guild_id]
    return {
        "permission_overwrites": clear_send_messages(channel.get("permission_overwrites", []), effective_role_ids),
    }


def build_archive_patch(
    channel: dict[str, Any],
    archive_category_id: str,
    rename_prefix: str,
    lock_role_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build the PATCH payload for a soft archive operation."""

    patch = build_channel_lock_patch(channel, lock_role_ids)
    patch.update(
        {
        "parent_id": archive_category_id,
        }
    )

    current_name = str(channel.get("name", "channel"))
    new_name = prefixed_channel_name(current_name, rename_prefix)
    if new_name != current_name:
        patch["name"] = new_name

    return patch


def build_category_move_patch(target_category_id: str) -> dict[str, Any]:
    """Build the PATCH payload for a category move."""

    return {"parent_id": target_category_id}

