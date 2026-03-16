"""Discord REST API wrapper built on the Python standard library."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from .config import DiscordAdminConfig
from .errors import DiscordAPIError, ValidationError
from .policies import build_archive_patch, build_category_move_patch


TEXT_CHANNEL_TYPE = 0
CATEGORY_CHANNEL_TYPE = 4


class DiscordRestClient:
    """Small Discord REST client with only the endpoints required for the MVP."""

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
            }
            for role in roles
        ]
        payload.sort(key=lambda item: item["position"], reverse=True)
        return {"guild_id": guild_id, "roles": payload, "count": len(payload)}

    def get_member(self, guild_id: str, user_id: str) -> dict[str, Any]:
        member = self._request("GET", f"/guilds/{guild_id}/members/{user_id}")
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "nick": member.get("nick"),
            "roles": member.get("roles", []),
            "joined_at": member.get("joined_at"),
            "pending": member.get("pending", False),
            "user": member.get("user", {}),
        }

    def list_members_by_role(self, guild_id: str, role_id: str, limit: int = 100) -> dict[str, Any]:
        matched: list[dict[str, Any]] = []
        after: str | None = None
        page_size = 1000 if limit > 1000 else max(limit, 1)

        while len(matched) < limit:
            page = self._request("GET", f"/guilds/{guild_id}/members", query={"limit": page_size, "after": after})
            if not page:
                break

            for member in page:
                if role_id in member.get("roles", []):
                    matched.append(
                        {
                            "user_id": member["user"]["id"],
                            "username": member["user"].get("username"),
                            "global_name": member["user"].get("global_name"),
                            "nick": member.get("nick"),
                        }
                    )
                    if len(matched) >= limit:
                        break

            after = page[-1]["user"]["id"]
            if len(page) < page_size:
                break

        return {"guild_id": guild_id, "role_id": role_id, "members": matched, "count": len(matched)}

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

    def assign_role(self, guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "role_id": role_id, "assigned": True}

    def remove_role(self, guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict[str, Any]:
        self._request("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)
        return {"guild_id": guild_id, "user_id": user_id, "role_id": role_id, "removed": True}

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

    def post_announcement(self, channel_id: str, content: str, reason: str | None = None) -> dict[str, Any]:
        sent = self._request("POST", f"/channels/{channel_id}/messages", payload={"content": content}, reason=reason)
        return {
            "guild_id": str(sent.get("guild_id")),
            "channel_id": channel_id,
            "message_id": sent.get("id"),
            "content": sent.get("content"),
        }

