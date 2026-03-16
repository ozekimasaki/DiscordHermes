from __future__ import annotations

import unittest

from extensions.mcp.discord_admin_server.models import ToolDefinition
from extensions.mcp.discord_admin_server.server import MinimalMCPServer
from extensions.mcp.discord_admin_server.tool_registry import ToolRegistry


class MinimalMCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = ToolRegistry(
            [
                ToolDefinition(
                    name="sample_tool",
                    title="Sample Tool",
                    description="Returns a tiny payload.",
                    input_schema={"type": "object", "additionalProperties": False},
                    handler=lambda args: {"ok": True, "echo": args},
                )
            ]
        )
        self.server = MinimalMCPServer(registry)

    def test_initialize_returns_tools_capability(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            }
        )

        self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_returns_registry_contents(self) -> None:
        response = self.server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(response["result"]["tools"][0]["name"], "sample_tool")

    def test_tools_call_returns_structured_content(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "sample_tool", "arguments": {"hello": "world"}},
            }
        )

        self.assertFalse(response["result"]["isError"])
        self.assertEqual(response["result"]["structuredContent"]["echo"]["hello"], "world")

    def test_unknown_tool_returns_protocol_error(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "missing_tool", "arguments": {}},
            }
        )

        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()

