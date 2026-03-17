from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.errors import ValidationError
from extensions.mcp.discord_admin_server.validation import (
    optional_integer,
    optional_nonempty_snowflake_list,
    optional_permissions,
    require_integer,
)


class ValidationTests(unittest.TestCase):
    def test_optional_integer_rejects_values_over_maximum(self) -> None:
        with self.assertRaises(ValidationError):
            optional_integer({"limit": 1001}, "limit", minimum=1, maximum=1000)

    def test_optional_integer_rejects_boolean_values(self) -> None:
        with self.assertRaises(ValidationError):
            optional_integer({"limit": True}, "limit", minimum=1, maximum=1000)

    def test_optional_permissions_can_return_none_when_requested(self) -> None:
        self.assertIsNone(optional_permissions({}, default=None))

    def test_optional_permissions_rejects_boolean_values(self) -> None:
        with self.assertRaises(ValidationError):
            optional_permissions({"permissions": True})

    def test_require_integer_rejects_missing_values(self) -> None:
        with self.assertRaises(ValidationError):
            require_integer({}, "duration_minutes", minimum=1)

    def test_require_integer_rejects_boolean_values(self) -> None:
        with self.assertRaises(ValidationError):
            require_integer({"duration_minutes": False}, "duration_minutes", minimum=1)

    def test_optional_nonempty_snowflake_list_rejects_empty_arrays(self) -> None:
        with self.assertRaises(ValidationError):
            optional_nonempty_snowflake_list({"role_ids": []}, "role_ids")


if __name__ == "__main__":
    unittest.main()
