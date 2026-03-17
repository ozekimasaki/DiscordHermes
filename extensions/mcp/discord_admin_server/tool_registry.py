"""Tool metadata and execution wrappers."""

from __future__ import annotations

import json
from typing import Any

from .audit_store import AuditStore
from .discord_api import DiscordRestClient
from .errors import ToolExecutionError, ValidationError
from .models import ToolDefinition
from .validation import (
    optional_boolean,
    optional_integer,
    optional_nonempty_snowflake_list,
    optional_permissions,
    optional_snowflake,
    optional_string,
    require_integer,
    require_mapping,
    require_snowflake,
    require_string,
)


def _summarize(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 500 else text[:497] + "..."


class ToolRegistry:
    """In-memory tool registry used by the stdio MCP server."""

    def __init__(self, definitions: list[ToolDefinition]) -> None:
        self._definitions = {definition.name: definition for definition in definitions}

    def list_tools(self) -> list[dict[str, Any]]:
        return [definition.as_mcp_tool() for definition in self._definitions.values()]

    def has(self, name: str) -> bool:
        return name in self._definitions

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._definitions:
            raise KeyError(name)
        return self._definitions[name].handler(arguments)


class DiscordAdminService:
    """High-level tool execution wrapper with audit logging."""

    def __init__(self, api: DiscordRestClient, audit_store: AuditStore) -> None:
        self.api = api
        self.audit_store = audit_store

    def _record(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        success: bool,
        result: Any,
        guild_id: str | None,
    ) -> None:
        self.audit_store.log_action(
            guild_id=guild_id,
            actor_user_id=optional_snowflake(arguments, "requested_by"),
            tool_name=tool_name,
            arguments=arguments,
            result_summary=_summarize(result),
            success=success,
        )

    def execute(self, tool_name: str, arguments: dict[str, Any], operation) -> Any:
        arguments = require_mapping(arguments)
        inferred_guild_id = optional_snowflake(arguments, "guild_id")
        try:
            result = operation(arguments)
        except ValidationError:
            raise
        except Exception as exc:
            self._record(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                result={"error": str(exc)},
                guild_id=inferred_guild_id,
            )
            raise ToolExecutionError(str(exc)) from exc
        else:
            guild_id = inferred_guild_id
            if isinstance(result, dict):
                possible_guild_id = result.get("guild_id")
                if isinstance(possible_guild_id, str) and possible_guild_id.isdigit():
                    guild_id = possible_guild_id
            self._record(
                tool_name=tool_name,
                arguments=arguments,
                success=True,
                result=result,
                guild_id=guild_id,
            )
            return result


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _role_update_fields(arguments: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "name" in arguments:
        updates["name"] = require_string(arguments, "name")
    if "permissions" in arguments:
        updates["permissions"] = optional_permissions(arguments, default=None)
    if "color" in arguments:
        updates["color"] = optional_integer(arguments, "color", minimum=0)
    if "hoist" in arguments:
        updates["hoist"] = optional_boolean(arguments, "hoist")
    if "mentionable" in arguments:
        updates["mentionable"] = optional_boolean(arguments, "mentionable")

    if not updates:
        raise ValidationError("update_role requires at least one role field to change.")

    return updates


def build_tool_registry(service: DiscordAdminService) -> ToolRegistry:
    """Create the Discord admin registry for Hermes."""

    definitions = [
        ToolDefinition(
            name="get_guild_summary",
            title="Get Guild Summary",
            description="Return high-level guild metadata for the target Discord server.",
            input_schema=_schema({"guild_id": {"type": "string"}}, ["guild_id"]),
            handler=lambda args: service.execute(
                "get_guild_summary",
                args,
                lambda payload: service.api.get_guild_summary(require_snowflake(payload, "guild_id")),
            ),
        ),
        ToolDefinition(
            name="list_categories",
            title="List Categories",
            description="List Discord category channels in the target guild.",
            input_schema=_schema({"guild_id": {"type": "string"}}, ["guild_id"]),
            handler=lambda args: service.execute(
                "list_categories",
                args,
                lambda payload: service.api.list_categories(require_snowflake(payload, "guild_id")),
            ),
        ),
        ToolDefinition(
            name="list_channels",
            title="List Channels",
            description="List Discord channels, optionally scoped to one category.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "category_id": {"type": "string"},
                },
                ["guild_id"],
            ),
            handler=lambda args: service.execute(
                "list_channels",
                args,
                lambda payload: service.api.list_channels(
                    require_snowflake(payload, "guild_id"),
                    optional_snowflake(payload, "category_id"),
                ),
            ),
        ),
        ToolDefinition(
            name="list_roles",
            title="List Roles",
            description="List Discord roles in the target guild.",
            input_schema=_schema({"guild_id": {"type": "string"}}, ["guild_id"]),
            handler=lambda args: service.execute(
                "list_roles",
                args,
                lambda payload: service.api.list_roles(require_snowflake(payload, "guild_id")),
            ),
        ),
        ToolDefinition(
            name="list_members",
            title="List Members",
            description="List guild members, optionally continuing after a specific member.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "after": {"type": "string"},
                },
                ["guild_id"],
            ),
            handler=lambda args: service.execute(
                "list_members",
                args,
                lambda payload: service.api.list_members(
                    require_snowflake(payload, "guild_id"),
                    limit=optional_integer(payload, "limit", default=100, minimum=1, maximum=1000) or 100,
                    after=optional_snowflake(payload, "after"),
                ),
            ),
        ),
        ToolDefinition(
            name="search_members",
            title="Search Members",
            description="Search guild members by username, nickname, or global name prefix.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                ["guild_id", "query"],
            ),
            handler=lambda args: service.execute(
                "search_members",
                args,
                lambda payload: service.api.search_members(
                    require_snowflake(payload, "guild_id"),
                    require_string(payload, "query"),
                    limit=optional_integer(payload, "limit", default=10, minimum=1, maximum=1000) or 10,
                ),
            ),
        ),
        ToolDefinition(
            name="get_member",
            title="Get Member",
            description="Return details for a guild member.",
            input_schema=_schema(
                {"guild_id": {"type": "string"}, "user_id": {"type": "string"}},
                ["guild_id", "user_id"],
            ),
            handler=lambda args: service.execute(
                "get_member",
                args,
                lambda payload: service.api.get_member(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                ),
            ),
        ),
        ToolDefinition(
            name="list_members_by_role",
            title="List Members By Role",
            description="List members in a guild who currently hold a given role.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                ["guild_id", "role_id"],
            ),
            handler=lambda args: service.execute(
                "list_members_by_role",
                args,
                lambda payload: service.api.list_members_by_role(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "role_id"),
                    optional_integer(payload, "limit", default=100, minimum=1, maximum=1000) or 100,
                ),
            ),
        ),
        ToolDefinition(
            name="create_role",
            title="Create Role",
            description="Create a new role in a Discord guild.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "name": {"type": "string"},
                    "permissions": {"type": ["string", "integer"]},
                    "color": {"type": "integer", "minimum": 0},
                    "hoist": {"type": "boolean"},
                    "mentionable": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "name"],
            ),
            handler=lambda args: service.execute(
                "create_role",
                args,
                lambda payload: service.api.create_role(
                    require_snowflake(payload, "guild_id"),
                    name=require_string(payload, "name"),
                    permissions=optional_permissions(payload) or "0",
                    color=optional_integer(payload, "color", default=0, minimum=0) or 0,
                    hoist=optional_boolean(payload, "hoist", default=False),
                    mentionable=optional_boolean(payload, "mentionable", default=False),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="update_role",
            title="Update Role",
            description="Update one or more mutable fields on an existing Discord role.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "name": {"type": "string"},
                    "permissions": {"type": ["string", "integer"]},
                    "color": {"type": "integer", "minimum": 0},
                    "hoist": {"type": "boolean"},
                    "mentionable": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "role_id"],
            ),
            handler=lambda args: service.execute(
                "update_role",
                args,
                lambda payload: service.api.update_role(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "role_id"),
                    reason=optional_string(payload, "reason"),
                    **_role_update_fields(payload),
                ),
            ),
        ),
        ToolDefinition(
            name="assign_role",
            title="Assign Role",
            description="Assign an existing role to a member.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id", "role_id"],
            ),
            handler=lambda args: service.execute(
                "assign_role",
                args,
                lambda payload: service.api.assign_role(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    require_snowflake(payload, "role_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="remove_role",
            title="Remove Role",
            description="Remove an existing role from a member.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id", "role_id"],
            ),
            handler=lambda args: service.execute(
                "remove_role",
                args,
                lambda payload: service.api.remove_role(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    require_snowflake(payload, "role_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="create_category",
            title="Create Category",
            description="Create a new category channel in a Discord guild.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "name": {"type": "string"},
                    "position": {"type": "integer", "minimum": 0},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "name"],
            ),
            handler=lambda args: service.execute(
                "create_category",
                args,
                lambda payload: service.api.create_category(
                    require_snowflake(payload, "guild_id"),
                    name=require_string(payload, "name"),
                    position=optional_integer(payload, "position", minimum=0),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="create_text_channel",
            title="Create Text Channel",
            description="Create a text channel, optionally inside a given category.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "name": {"type": "string"},
                    "parent_id": {"type": "string"},
                    "topic": {"type": "string"},
                    "nsfw": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "name"],
            ),
            handler=lambda args: service.execute(
                "create_text_channel",
                args,
                lambda payload: service.api.create_text_channel(
                    require_snowflake(payload, "guild_id"),
                    name=require_string(payload, "name"),
                    parent_id=optional_snowflake(payload, "parent_id"),
                    topic=optional_string(payload, "topic"),
                    nsfw=optional_boolean(payload, "nsfw", default=False),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="rename_channel",
            title="Rename Channel",
            description="Rename an existing Discord channel.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id", "name"],
            ),
            handler=lambda args: service.execute(
                "rename_channel",
                args,
                lambda payload: service.api.rename_channel(
                    require_snowflake(payload, "channel_id"),
                    require_string(payload, "name"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="set_channel_topic",
            title="Set Channel Topic",
            description="Update the topic on an existing Discord text channel.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "topic": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id", "topic"],
            ),
            handler=lambda args: service.execute(
                "set_channel_topic",
                args,
                lambda payload: service.api.set_channel_topic(
                    require_snowflake(payload, "channel_id"),
                    require_string(payload, "topic"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="lock_channel",
            title="Lock Channel",
            description="Deny send-message permissions for selected roles on a channel while preserving prior explicit allows for reversible unlocks.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "role_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id"],
            ),
            handler=lambda args: service.execute(
                "lock_channel",
                args,
                lambda payload: service.api.lock_channel(
                    require_snowflake(payload, "channel_id"),
                    role_ids=optional_nonempty_snowflake_list(payload, "role_ids"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="unlock_channel",
            title="Unlock Channel",
            description="Clear explicit send-message denies for selected roles on a channel and remove neutral overwrite entries.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "role_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id"],
            ),
            handler=lambda args: service.execute(
                "unlock_channel",
                args,
                lambda payload: service.api.unlock_channel(
                    require_snowflake(payload, "channel_id"),
                    role_ids=optional_nonempty_snowflake_list(payload, "role_ids"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="archive_channel",
            title="Archive Channel",
            description="Soft-archive a channel by moving it, locking it, and preserving it.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "archive_category_id": {"type": "string"},
                    "rename_prefix": {"type": "string"},
                    "lock_role_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id", "archive_category_id"],
            ),
            handler=lambda args: service.execute(
                "archive_channel",
                args,
                lambda payload: service.api.archive_channel(
                    require_snowflake(payload, "channel_id"),
                    archive_category_id=require_snowflake(payload, "archive_category_id"),
                    rename_prefix=optional_string(payload, "rename_prefix", default="archived") or "archived",
                    lock_role_ids=optional_nonempty_snowflake_list(payload, "lock_role_ids"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="move_channel_to_category",
            title="Move Channel To Category",
            description="Move an existing channel into another Discord category.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "target_category_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id", "target_category_id"],
            ),
            handler=lambda args: service.execute(
                "move_channel_to_category",
                args,
                lambda payload: service.api.move_channel_to_category(
                    require_snowflake(payload, "channel_id"),
                    require_snowflake(payload, "target_category_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="set_member_nickname",
            title="Set Member Nickname",
            description="Set a guild member nickname.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "nickname": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id", "nickname"],
            ),
            handler=lambda args: service.execute(
                "set_member_nickname",
                args,
                lambda payload: service.api.set_member_nickname(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    require_string(payload, "nickname"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="timeout_member",
            title="Timeout Member",
            description="Apply a communication timeout to a guild member.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 40320},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id", "duration_minutes"],
            ),
            handler=lambda args: service.execute(
                "timeout_member",
                args,
                lambda payload: service.api.timeout_member(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    duration_minutes=require_integer(
                        payload,
                        "duration_minutes",
                        minimum=1,
                        maximum=40320,
                    ),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="clear_member_timeout",
            title="Clear Member Timeout",
            description="Remove an active communication timeout from a guild member.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id"],
            ),
            handler=lambda args: service.execute(
                "clear_member_timeout",
                args,
                lambda payload: service.api.clear_member_timeout(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="kick_member",
            title="Kick Member",
            description="Kick a member from a Discord guild.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id"],
            ),
            handler=lambda args: service.execute(
                "kick_member",
                args,
                lambda payload: service.api.kick_member(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="ban_member",
            title="Ban Member",
            description="Ban a member from a Discord guild.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "delete_message_seconds": {"type": "integer", "minimum": 0, "maximum": 604800},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id"],
            ),
            handler=lambda args: service.execute(
                "ban_member",
                args,
                lambda payload: service.api.ban_member(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    delete_message_seconds=optional_integer(
                        payload,
                        "delete_message_seconds",
                        default=0,
                        minimum=0,
                        maximum=604800,
                    )
                    or 0,
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="unban_member",
            title="Unban Member",
            description="Remove an existing guild ban for a user.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["guild_id", "user_id"],
            ),
            handler=lambda args: service.execute(
                "unban_member",
                args,
                lambda payload: service.api.unban_member(
                    require_snowflake(payload, "guild_id"),
                    require_snowflake(payload, "user_id"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
        ToolDefinition(
            name="export_members_csv",
            title="Export Members CSV",
            description="Export a CSV snapshot of guild members, optionally filtered to one role.",
            input_schema=_schema(
                {
                    "guild_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                ["guild_id"],
            ),
            handler=lambda args: service.execute(
                "export_members_csv",
                args,
                lambda payload: service.api.export_members_csv(
                    require_snowflake(payload, "guild_id"),
                    limit=optional_integer(payload, "limit", default=100, minimum=1, maximum=1000) or 100,
                    role_id=optional_snowflake(payload, "role_id"),
                ),
            ),
        ),
        ToolDefinition(
            name="post_announcement",
            title="Post Announcement",
            description="Send a message into a Discord channel.",
            input_schema=_schema(
                {
                    "channel_id": {"type": "string"},
                    "content": {"type": "string"},
                    "reason": {"type": "string"},
                    "requested_by": {"type": "string"},
                },
                ["channel_id", "content"],
            ),
            handler=lambda args: service.execute(
                "post_announcement",
                args,
                lambda payload: service.api.post_announcement(
                    require_snowflake(payload, "channel_id"),
                    require_string(payload, "content"),
                    reason=optional_string(payload, "reason"),
                ),
            ),
        ),
    ]

    return ToolRegistry(definitions)
