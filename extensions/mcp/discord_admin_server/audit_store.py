"""SQLite-backed audit store."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any


class AuditStore:
    """Persist audit records outside Hermes chat history."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS guild_policies (
                    guild_id TEXT PRIMARY KEY,
                    allowed_roles TEXT,
                    allowed_channels TEXT,
                    destructive_actions_enabled INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS action_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    actor_user_id TEXT,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    result_summary TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS pending_confirmations (
                    confirmation_id TEXT PRIMARY KEY,
                    guild_id TEXT NOT NULL,
                    requested_by TEXT,
                    tool_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def log_action(
        self,
        *,
        guild_id: str | None,
        actor_user_id: str | None,
        tool_name: str,
        arguments: dict[str, Any],
        result_summary: str,
        success: bool,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO action_audit_log (
                    guild_id,
                    actor_user_id,
                    tool_name,
                    arguments_json,
                    result_summary,
                    success
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    actor_user_id,
                    tool_name,
                    json.dumps(arguments, ensure_ascii=True, sort_keys=True),
                    result_summary,
                    1 if success else 0,
                ),
            )
            connection.commit()

    def list_recent_actions(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT guild_id, actor_user_id, tool_name, arguments_json, result_summary, success, created_at
                FROM action_audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

