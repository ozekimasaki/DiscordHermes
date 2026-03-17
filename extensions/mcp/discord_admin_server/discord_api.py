"""Discord REST API wrapper built on the Python standard library."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any
from urllib import error, parse, request

from .config import DiscordAdminConfig
from .errors import DiscordAPIError, ValidationError
from .policies import (
    build_archive_patch,
    build_category_move_patch,
    build_channel_lock_patch,
    build_channel_unlock_patch,
)

TEXT_CHANNEL_TYPE = 0
CATEGORY_CHANNEL_TYPE = 4
MAX_GUILD_MEMBER_PAGE_SIZE = 1000


class DiscordRestClient:
    """Small Discord REST client for Hermes-managed Discord administration."""

    def __init__(self, config: DiscordAdminConfig) -> None:
        self._base_url = config.api_base_url.rstrip("/")
        self._bot_token = config.bot_token
        self._timeout = config.request_timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        if query:
            encoded = parse.urlencode({key: value for key, value in query.items() if value is not None})
            url = f"{url}?{encoded}"

        body = None if payload is None else json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        headers = {
            "Authorization": f"Bot {self._bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "hermes-discord-admin-extension/0.1.0",
        }
        if reason:
            headers["X-Audit-Log-Reason"] = parse.quote(reason, safe="")

        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            details: Any = raw
            if raw.startswith("{"):
                try:
                    details = json.loads(raw)
                except json.JSONDecodeError:
                    details = raw
            if isinstance(details, dict):
                message = details.get("message") or json.dumps(details, ensure_ascii=True)
            else:
                message = details or str(exc.reason)
            raise DiscordAPIError(exc.code, message, details) from exc
        except error.URLError as exc:
            raise DiscordAPIError(0, f"Failed to reach Discord: {exc.reason}") from exc

    @staticmethod
    def _serialize_member(member: dict[str, Any]) -> dict[str, Any]:
        user = member.get("user", {})
        return {
            "user_id": user.get("id"),
            "username": user.get("username"),
            "global_name": user.get("global_name"),
            "nick": member.get("nick"),
            "joined_at": member.get("joined_at"),
            "pending": member.get("pending", False),
            "roles": member.get("roles", []),
            "communication_disabled_until": member.get("communication_disabled_until"),
        }

    def _collect_members(self, guild_id: str, *, limit: int, role_id: str | None = None) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        after: str | None = None
        page_size = MAX_GUILD_MEMBER_PAGE_SIZE if role_id else min(MAX_GUILD_MEMBER_PAGE_SIZE, max(limit, 1))

        while len(matched) < limit:
            page = self._request("GET", f"/guilds/{guild_id}/members", query={"limit": page_size, "after": after})
            if not page:
                break

            for member in page:
                if role_id is not None and role_id not in member.get("roles", []):
                    continue
                matched.append(member)
                if len(matched) >= limit:
                    return matched

            last_user = page[-1].get("user", {})
            last_user_id = last_user.get("id")
            if not isinstance(last_user_id, str) or not last_user_id:
                break
            after = last_user_id
            if len(page) < page_size:
                break

        return matched

    def get_guild_summary(self, guild_id: str) -> dict[str, Any]:
        guild = self._request("GET", f"/guilds/{guild_id}")
        channels = self._request("GET", f"/guilds/{guild_id}/channels")
        roles = self._request("GET", f"/guilds/{guild_id}/roles")
        categories = [channel for channel in channels if int(channel.get("type", -1)) == CATEGORY_CHANNEL_TYPE]

        return {
            "guild_id": guild_id,
            "name": guild.get("name"),
            "description": guild.get("description"),
            "member_count": guild.get("approximate_member_count"),
            "channel_count": len(channels),
            "category_count": len(categories),
            "role_count": len(roles),
        }

    def list_categories(self, guild_id: str) -> dict[str, Any]:
        channels = self._request("GET", f"/guilds/{guild_id}/channels")
        categories = [
            {
                "id": channel["id"],
                "name": channel["name"],
                "position": channel.get("position", 0),
            }
            for channel in channels
            if int(channel.get("type", -1)) == CATEGORY_CHANNEL_TYPE
        ]
        categories.sort(key=lambda item: item["position"])
        return {"guild_id": guild_id, "categories": categories, "count": len(categories)}

    def list_channels(self, guild_id: str, category_id: str | None = None) -> dict[str, Any]:
        channels = self._request("GET", f"/guilds/{guild_id}/channels")
        filtered = [
            {
                "id": channel["id"],
                "name": channel["name"],
                "type": channel.get("type"),
                "parent_id": channel.get("parent_id"),
                "position": channel.get("position", 0),
                "topic": channel.get("topic"),
                "nsfw": channel.get("nsfw", False),
            }
            for channel in channels
            if category_id is None or str(channel.get("parent_id")) == category_id
        ]
        filtered.sort(key=lambda item: (item["parent_id"] or "", item["position"], item["name"]))
        return {"guild_id": guild_id, "channels": filtered, "count": len(filtered)}

    def list_roles(self, guild_id: str) -> dict[str, Any]:
        roles = self._request("GET", f"/guilds/{guild_id}/roles")
        payload = [
            {
                "id": role["id"],
                "name": role["name"],
                "position": role.get("position", 0),
                "mentionable": role.get("mentionable", False),
                "managed": role.get("managed", False),
                "permissions": role.get("permissions", "0"),
                "color": role.get("color", 0),
            }
            for role in roles
        ]
        payload.sort(key=lambda item: item["position"], reverse=True)
        return {"guild_id": guild_id, "roles": payload, "count": len(payload)}

    def list_members(self, guild_id: str, limit: int = 100, after: str | None = None) -> dict[str, Any]:
        page_size = min(MAX_GUILD_MEMBER_PAGE_SIZE, max(limit, 1))
        members = self._request("GET", f"/guilds/{guild_id}/members", query={"limit": page_size, "after": after})
        payload = [self._serialize_member(member) for member in members]
        next_after = payload[-1]["user_id"] if payload else None
        return {"guild_id": guild_id, "members": payload, "count": len(payload), "next_after": next_after}

    def search_members(self, guild_id: str, query_text: str, limit: int = 10) -> dict[str, Any]:
        members = self._request(
            "GET",
            f"/guilds/{guild_id}/members/search",
            query={"query": query_text, "limit": limit},
        )
        payload = [self._serialize_member(member) for member in members]
        return {"guild_id": guild_id, "query": query_text, "members": payload, "count": len(payload)}

    def get_member(self, guild_id: str, user_id: str) -> dict[str, Any]:
        member = self._request("GET", f"/guilds/{guild_id}/members/{user_id}")
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            **self._serialize_member(member),
            "user": member.get("user", {}),
        }

    def list_members_by_role(self, guild_id: str, role_id: str, limit: int = 100) -> dict[str, Any]:
        members = [self._serialize_member(member) for member in self._collect_members(guild_id, limit=limit, role_id=role_id)]
        return {"guild_id": guild_id, "role_id": role_id, "members": members, "count": len(members)}

    def create_role(
        self,
        guild_id: str,
        *,
        name: str,
        permissions: str = "0",
        color: int = 0,
        hoist: bool = False,
        mentionable: bool = False,
        reason: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "permissions": permissions,
            "color": color,
            "hoist": hoist,
            "mentionable": mentionable,
        }
        created = self._request("POST", f"/guilds/{guild_id}/roles", payload=payload, reason=reason)
        return {"guild_id": guild_id, "role": created}

    def update_role(
        self,
        guild_id: str,
        role_id: str,
        *,
        name: str | None = None,
        permissions: str | None = None,
        color: int | None = None,
        hoist: bool | None = None,
        mentionable: bool | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if permissions is not None:
            payload["permissions"] = permissions
        if color is not None:
            payload["color"] = color
        if hoist is not None:
            payload["hoist"] = hoist
        if mentionable is not None:
            payload["mentionable"] = mentionable
        if not payload:
            raise ValidationError("update_role requires at least one field to change.")

        updated = self._request("PATCH", f"/guilds/{guild_id}/roles/{role_id}", payload=payload, reason=reason)
        return {"guild_id": guild_id, "role": updated}

    def assign_role(self, guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "role_id": role_id, "assigned": True}

    def remove_role(self, guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "role_id": role_id, "removed": True}

    def create_category(self, guild_id: str, *, name: str, position: int | None = None, reason: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "type": CATEGORY_CHANNEL_TYPE}
        if position is not None:
            payload["position"] = position
        created = self._request("POST", f"/guilds/{guild_id}/channels", payload=payload, reason=reason)
        return {"guild_id": guild_id, "channel": created}

    def create_text_channel(
        self,
        guild_id: str,
        *,
        name: str,
        parent_id: str | None = None,
        topic: str | None = None,
        nsfw: bool = False,
        reason: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "type": TEXT_CHANNEL_TYPE,
            "nsfw": nsfw,
        }
        if parent_id:
            payload["parent_id"] = parent_id
        if topic:
            payload["topic"] = topic
        created = self._request("POST", f"/guilds/{guild_id}/channels", payload=payload, reason=reason)
        return {"guild_id": guild_id, "channel": created}

    def rename_channel(self, channel_id: str, name: str, reason: str | None = None) -> dict[str, Any]:
        renamed = self._request("PATCH", f"/channels/{channel_id}", payload={"name": name}, reason=reason)
        return {"guild_id": str(renamed.get("guild_id")), "channel": renamed}

    def set_channel_topic(self, channel_id: str, topic: str, reason: str | None = None) -> dict[str, Any]:
        updated = self._request("PATCH", f"/channels/{channel_id}", payload={"topic": topic}, reason=reason)
        return {"guild_id": str(updated.get("guild_id")), "channel": updated}

    def lock_channel(self, channel_id: str, role_ids: list[str] | None = None, reason: str | None = None) -> dict[str, Any]:
        channel = self._request("GET", f"/channels/{channel_id}")
        channel_type = int(channel.get("type", -1))
        if channel_type == CATEGORY_CHANNEL_TYPE:
            raise ValidationError("lock_channel expects a concrete channel, not a category.")

        locked_role_ids = role_ids or [str(channel["guild_id"])]
        locked = self._request(
            "PATCH",
            f"/channels/{channel_id}",
            payload=build_channel_lock_patch(channel, locked_role_ids),
            reason=reason,
        )
        return {"guild_id": str(locked.get("guild_id")), "channel": locked, "locked_role_ids": locked_role_ids}

    def unlock_channel(self, channel_id: str, role_ids: list[str] | None = None, reason: str | None = None) -> dict[str, Any]:
        channel = self._request("GET", f"/channels/{channel_id}")
        channel_type = int(channel.get("type", -1))
        if channel_type == CATEGORY_CHANNEL_TYPE:
            raise ValidationError("unlock_channel expects a concrete channel, not a category.")

        unlocked_role_ids = role_ids or [str(channel["guild_id"])]
        unlocked = self._request(
            "PATCH",
            f"/channels/{channel_id}",
            payload=build_channel_unlock_patch(channel, unlocked_role_ids),
            reason=reason,
        )
        return {"guild_id": str(unlocked.get("guild_id")), "channel": unlocked, "unlocked_role_ids": unlocked_role_ids}

    def move_channel_to_category(
        self, channel_id: str, target_category_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        moved = self._request(
            "PATCH",
            f"/channels/{channel_id}",
            payload=build_category_move_patch(target_category_id),
            reason=reason,
        )
        return {
            "guild_id": str(moved.get("guild_id")),
            "channel": moved,
            "target_category_id": target_category_id,
        }

    def archive_channel(
        self,
        channel_id: str,
        *,
        archive_category_id: str,
        rename_prefix: str = "archived",
        lock_role_ids: list[str] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        channel = self._request("GET", f"/channels/{channel_id}")
        channel_type = int(channel.get("type", -1))
        if channel_type == CATEGORY_CHANNEL_TYPE:
            raise ValidationError("archive_channel expects a concrete channel, not a category.")

        payload = build_archive_patch(
            channel=channel,
            archive_category_id=archive_category_id,
            rename_prefix=rename_prefix,
            lock_role_ids=lock_role_ids,
        )
        archived = self._request("PATCH", f"/channels/{channel_id}", payload=payload, reason=reason)
        return {
            "guild_id": str(archived.get("guild_id")),
            "channel": archived,
            "archive_category_id": archive_category_id,
            "locked_role_ids": lock_role_ids or [str(channel["guild_id"])],
        }

    def set_member_nickname(self, guild_id: str, user_id: str, nickname: str, reason: str | None = None) -> dict[str, Any]:
        updated = self._request(
            "PATCH",
            f"/guilds/{guild_id}/members/{user_id}",
            payload={"nick": nickname},
            reason=reason,
        )
        return {"guild_id": guild_id, "user_id": user_id, "nick": updated.get("nick")}

    def timeout_member(
        self,
        guild_id: str,
        user_id: str,
        *,
        duration_minutes: int,
        reason: str | None = None,
    ) -> dict[str, Any]:
        communication_disabled_until = (
            datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        updated = self._request(
            "PATCH",
            f"/guilds/{guild_id}/members/{user_id}",
            payload={"communication_disabled_until": communication_disabled_until},
            reason=reason,
        )
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "communication_disabled_until": updated.get("communication_disabled_until", communication_disabled_until),
            "timed_out": True,
        }

    def clear_member_timeout(self, guild_id: str, user_id: str, reason: str | None = None) -> dict[str, Any]:
        updated = self._request(
            "PATCH",
            f"/guilds/{guild_id}/members/{user_id}",
            payload={"communication_disabled_until": None},
            reason=reason,
        )
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "communication_disabled_until": updated.get("communication_disabled_until"),
            "timed_out": False,
        }

    def kick_member(self, guild_id: str, user_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("DELETE", f"/guilds/{guild_id}/members/{user_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "kicked": True}

    def ban_member(
        self,
        guild_id: str,
        user_id: str,
        *,
        delete_message_seconds: int = 0,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._request(
            "PUT",
            f"/guilds/{guild_id}/bans/{user_id}",
            payload={"delete_message_seconds": delete_message_seconds},
            reason=reason,
        )
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "banned": True,
            "delete_message_seconds": delete_message_seconds,
        }

    def unban_member(self, guild_id: str, user_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("DELETE", f"/guilds/{guild_id}/bans/{user_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "unbanned": True}

    def export_members_csv(self, guild_id: str, *, limit: int = 100, role_id: str | None = None) -> dict[str, Any]:
        members = self._collect_members(guild_id, limit=limit, role_id=role_id)
        buffer = StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            [
                "user_id",
                "username",
                "global_name",
                "nick",
                "joined_at",
                "pending",
                "communication_disabled_until",
                "roles",
            ]
        )

        for member in members:
            serialized = self._serialize_member(member)
            writer.writerow(
                [
                    serialized.get("user_id", ""),
                    serialized.get("username", ""),
                    serialized.get("global_name", ""),
                    serialized.get("nick", ""),
                    serialized.get("joined_at", ""),
                    "true" if serialized.get("pending") else "false",
                    serialized.get("communication_disabled_until", ""),
                    ";".join(serialized.get("roles", [])),
                ]
            )

        return {
            "guild_id": guild_id,
            "role_id": role_id,
            "count": len(members),
            "csv": buffer.getvalue(),
        }

    def post_announcement(self, channel_id: str, content: str, reason: str | None = None) -> dict[str, Any]:
        sent = self._request("POST", f"/channels/{channel_id}/messages", payload={"content": content}, reason=reason)
        return {
            "guild_id": str(sent.get("guild_id")),
            "channel_id": channel_id,
            "message_id": sent.get("id"),
            "content": sent.get("content"),
        }
