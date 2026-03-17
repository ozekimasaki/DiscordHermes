from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.errors import ValidationError
from extensions.mcp.discord_admin_server.tool_registry import DiscordAdminService, build_tool_registry


class FakeAuditStore:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def log_action(self, **kwargs) -> None:
        self.records.append(kwargs)


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def update_role(self, guild_id: str, role_id: str, **kwargs):
        self.calls.append(("update_role", (guild_id, role_id), kwargs))
        return {"guild_id": guild_id, "role": {"id": role_id, **kwargs}}

    def timeout_member(self, guild_id: str, user_id: str, **kwargs):
        self.calls.append(("timeout_member", (guild_id, user_id), kwargs))
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "timed_out": True,
            "communication_disabled_until": "2099-01-01T00:00:00Z",
        }

    def lock_channel(self, channel_id: str, **kwargs):
        self.calls.append(("lock_channel", (channel_id,), kwargs))
        return {"guild_id": "12345", "channel": {"id": channel_id}}


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = FakeApi()
        self.audit_store = FakeAuditStore()
        self.registry = build_tool_registry(DiscordAdminService(self.api, self.audit_store))

    def test_registry_lists_new_admin_tools(self) -> None:
        tool_names = {tool["name"] for tool in self.registry.list_tools()}

        self.assertIn("create_category", tool_names)
        self.assertIn("lock_channel", tool_names)
        self.assertIn("timeout_member", tool_names)
        self.assertIn("export_members_csv", tool_names)

    def test_update_role_requires_mutation_fields(self) -> None:
        with self.assertRaises(ValidationError):
            self.registry.call("update_role", {"guild_id": "12345", "role_id": "67890"})

    def test_timeout_member_dispatches_to_api(self) -> None:
        result = self.registry.call(
            "timeout_member",
            {"guild_id": "12345", "user_id": "67890", "duration_minutes": 15},
        )

        self.assertTrue(result["timed_out"])
        self.assertEqual(self.api.calls[0][0], "timeout_member")
        self.assertEqual(self.api.calls[0][1], ("12345", "67890"))
        self.assertEqual(self.api.calls[0][2]["duration_minutes"], 15)

    def test_timeout_member_requires_duration(self) -> None:
        with self.assertRaises(ValidationError):
            self.registry.call("timeout_member", {"guild_id": "12345", "user_id": "67890"})

    def test_lock_channel_rejects_empty_role_ids(self) -> None:
        with self.assertRaises(ValidationError):
            self.registry.call("lock_channel", {"channel_id": "12345", "role_ids": []})


if __name__ == "__main__":
    unittest.main()
