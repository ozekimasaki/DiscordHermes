from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.discord_api import DiscordRestClient


class FakeDiscordRestClient(DiscordRestClient):
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def _request(self, method: str, path: str, *, payload=None, query=None, reason=None):
        self.requests.append(
            {
                "method": method,
                "path": path,
                "payload": payload,
                "query": query,
                "reason": reason,
            }
        )
        return self._responses.pop(0)


class DiscordRestClientTests(unittest.TestCase):
    def test_list_members_by_role_collects_across_pages(self) -> None:
        first_page = [
            {"user": {"id": str(index), "username": f"user-{index}"}, "roles": []}
            for index in range(1, 1001)
        ]
        first_page[-1]["roles"] = ["9"]
        client = FakeDiscordRestClient(
            [
                first_page,
                [
                    {"user": {"id": "1001", "username": "one-thousand-one"}, "roles": ["9"]},
                    {"user": {"id": "1002", "username": "one-thousand-two"}, "roles": []},
                ],
            ]
        )

        result = client.list_members_by_role("12345", "9", limit=2)

        self.assertEqual(result["count"], 2)
        self.assertEqual([member["user_id"] for member in result["members"]], ["1000", "1001"])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(client.requests[1]["query"]["after"], "1000")

    def test_export_members_csv_filters_by_role(self) -> None:
        client = FakeDiscordRestClient(
            [
                [
                    {"user": {"id": "1", "username": "one"}, "roles": ["9"], "pending": False},
                    {"user": {"id": "2", "username": "two"}, "roles": [], "pending": False},
                ]
            ]
        )

        result = client.export_members_csv("12345", limit=10, role_id="9")

        self.assertEqual(result["count"], 1)
        self.assertIn("user_id,username,global_name,nick,joined_at,pending,communication_disabled_until,roles", result["csv"])
        self.assertIn("1,one", result["csv"])
        self.assertNotIn("2,two", result["csv"])


if __name__ == "__main__":
    unittest.main()
