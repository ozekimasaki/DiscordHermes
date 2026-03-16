from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from extensions.mcp.discord_admin_server.audit_store import AuditStore


class AuditStoreTests(unittest.TestCase):
    def test_log_action_persists_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "audit.db"
            store = AuditStore(str(db_path))
            store.log_action(
                guild_id="12345",
                actor_user_id="67890",
                tool_name="archive_channel",
                arguments={"channel_id": "42"},
                result_summary="ok",
                success=True,
            )

            rows = store.list_recent_actions()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["guild_id"], "12345")
            self.assertEqual(rows[0]["tool_name"], "archive_channel")
            self.assertEqual(rows[0]["success"], 1)


if __name__ == "__main__":
    unittest.main()

