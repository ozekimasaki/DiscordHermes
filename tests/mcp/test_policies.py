from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.policies import (
    SEND_MESSAGES_PERMISSION,
    build_archive_patch,
    build_channel_lock_patch,
    build_channel_unlock_patch,
    clear_send_messages,
    deny_send_messages,
    prefixed_channel_name,
)


class PolicyTests(unittest.TestCase):
    def test_prefixed_channel_name_is_stable(self) -> None:
        self.assertEqual(prefixed_channel_name("project-alpha", "archived"), "archived-project-alpha")
        self.assertEqual(prefixed_channel_name("archived-project-alpha", "archived"), "archived-project-alpha")

    def test_deny_send_messages_preserves_existing_overwrite(self) -> None:
        result = deny_send_messages(
            permission_overwrites=[{"id": "1", "type": 0, "allow": str(SEND_MESSAGES_PERMISSION), "deny": "0"}],
            role_ids=["1"],
        )
        self.assertEqual(result[0]["allow"], str(SEND_MESSAGES_PERMISSION))
        self.assertEqual(result[0]["deny"], str(SEND_MESSAGES_PERMISSION))

    def test_build_archive_patch_defaults_to_everyone_role(self) -> None:
        channel = {
            "id": "55",
            "guild_id": "999",
            "name": "project-room",
            "permission_overwrites": [],
        }

        patch = build_archive_patch(
            channel=channel,
            archive_category_id="123",
            rename_prefix="archived",
            lock_role_ids=None,
        )

        self.assertEqual(patch["parent_id"], "123")
        self.assertEqual(patch["name"], "archived-project-room")
        self.assertEqual(patch["permission_overwrites"][0]["id"], "999")
        self.assertEqual(patch["permission_overwrites"][0]["deny"], str(SEND_MESSAGES_PERMISSION))

    def test_clear_send_messages_removes_explicit_send_bits(self) -> None:
        result = clear_send_messages(
            permission_overwrites=[{"id": "1", "type": 0, "allow": str(SEND_MESSAGES_PERMISSION), "deny": str(SEND_MESSAGES_PERMISSION)}],
            role_ids=["1"],
        )

        self.assertEqual(result[0]["allow"], str(SEND_MESSAGES_PERMISSION))
        self.assertEqual(result[0]["deny"], "0")

    def test_clear_send_messages_removes_neutral_overwrites(self) -> None:
        result = clear_send_messages(
            permission_overwrites=[{"id": "1", "type": 0, "allow": "0", "deny": str(SEND_MESSAGES_PERMISSION)}],
            role_ids=["1"],
        )

        self.assertEqual(result, [])

    def test_build_channel_lock_patch_defaults_to_everyone_role(self) -> None:
        channel = {
            "id": "55",
            "guild_id": "999",
            "permission_overwrites": [],
        }

        patch = build_channel_lock_patch(channel=channel, lock_role_ids=None)

        self.assertEqual(patch["permission_overwrites"][0]["id"], "999")
        self.assertEqual(patch["permission_overwrites"][0]["deny"], str(SEND_MESSAGES_PERMISSION))

    def test_build_channel_unlock_patch_defaults_to_everyone_role(self) -> None:
        channel = {
            "id": "55",
            "guild_id": "999",
            "permission_overwrites": [{"id": "999", "type": 0, "allow": str(SEND_MESSAGES_PERMISSION), "deny": str(SEND_MESSAGES_PERMISSION)}],
        }

        patch = build_channel_unlock_patch(channel=channel, unlock_role_ids=None)

        self.assertEqual(patch["permission_overwrites"][0]["id"], "999")
        self.assertEqual(patch["permission_overwrites"][0]["allow"], str(SEND_MESSAGES_PERMISSION))
        self.assertEqual(patch["permission_overwrites"][0]["deny"], "0")


if __name__ == "__main__":
    unittest.main()

