"""Minimal stdio MCP server for Discord administration."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, TextIO

from .audit_store import AuditStore
from .config import DiscordAdminConfig
from .discord_api import DiscordRestClient
from .errors import ConfigError, ToolExecutionError, ValidationError
from .tool_registry import DiscordAdminService, build_tool_registry

SERVER_NAME = "discord-admin"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-03-26", "2025-06-18", "2025-11-25"}


class MinimalMCPServer:
    """Enough of the MCP stdio transport for Hermes to discover and call tools."""

    def __init__(self, registry) -> None:
        self._registry = registry
        self._initialized = False

    def serve(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        input_stream = stdin or sys.stdin
        output_stream = stdout or sys.stdout

        for raw_line in input_stream:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self._write(
                    output_stream,
                    self._error_response(None, -32700, f"Invalid JSON: {exc.msg}"),
                )
                continue

            response = self.handle_message(message)
            if response is not None:
                self._write(output_stream, response)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        if message.get("jsonrpc") != "2.0":
            return self._error_response(request_id, -32600, "Only JSON-RPC 2.0 messages are supported.")

        method = message.get("method")
        if not isinstance(method, str):
            return None if request_id is None else self._error_response(request_id, -32600, "Missing method.")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id, message.get("params") or {})
            if method in {"initialized", "notifications/initialized"} or method.startswith("notifications/"):
                self._initialized = True
                return None
            if method == "ping":
                return {"jsonrpc": "2.0", "id": request_id, "result": {}}
            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self._registry.list_tools()}}
            if method == "tools/call":
                return self._handle_tool_call(request_id, message.get("params") or {})

            return self._error_response(request_id, -32601, f"Unknown method: {method}")
        except ValidationError as exc:
            return self._tool_error_response(request_id, str(exc))
        except ToolExecutionError as exc:
            return self._tool_error_response(request_id, str(exc))
        except Exception as exc:  # pragma: no cover - defensive logging path
            print("Unhandled server error:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return self._error_response(request_id, -32000, str(exc))

    def _handle_initialize(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        requested_version = params.get("protocolVersion")
        if isinstance(requested_version, str) and requested_version in SUPPORTED_PROTOCOL_VERSIONS:
            protocol_version = requested_version
        else:
            protocol_version = DEFAULT_PROTOCOL_VERSION

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    def _handle_tool_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not name:
            return self._error_response(request_id, -32602, "tools/call requires a tool name.")
        if not self._registry.has(name):
            return self._error_response(request_id, -32602, f"Unknown tool: {name}")

        result = self._registry.call(name, arguments)
        text_block = json.dumps(result, ensure_ascii=True, sort_keys=True)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": text_block}],
                "structuredContent": result,
                "isError": False,
            },
        }

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    @staticmethod
    def _tool_error_response(request_id: Any, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": message}],
                "isError": True,
            },
        }

    @staticmethod
    def _write(stream: TextIO, message: dict[str, Any]) -> None:
        stream.write(json.dumps(message, ensure_ascii=True, separators=(",", ":")) + "\n")
        stream.flush()


def main() -> int:
    try:
        config = DiscordAdminConfig.from_env()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    audit_store = AuditStore(config.audit_db_path)
    api_client = DiscordRestClient(config)
    registry = build_tool_registry(DiscordAdminService(api_client, audit_store))
    MinimalMCPServer(registry).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

