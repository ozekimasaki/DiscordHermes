from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.policies import (
    SEND_MESSAGES_PERMISSION,
    build_archive_patch,
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
        self.assertEqual(result[0]["allow"], "0")
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


if __name__ == "__main__":
    unittest.main()

