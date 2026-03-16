from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.install_extension import install_extension, render_config_snippet
from scripts.launch_discord_admin_mcp import parse_dotenv


class InstallExtensionTests(unittest.TestCase):
    def test_render_config_snippet_uses_launcher_path(self) -> None:
        repo_root = Path(r"C:\repo")
        snippet = render_config_snippet(repo_root, repo_root / ".state" / "discord-admin.db")
        self.assertIn(r'C:\repo\scripts\launch_discord_admin_mcp.py', snippet)
        self.assertNotIn("DISCORD_BOT_TOKEN", snippet)

    def test_install_extension_writes_skill_and_snippets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hermes_home = Path(temp_dir) / ".hermes"
            result = install_extension(hermes_home)

            self.assertTrue(result["skill_path"].exists())
            self.assertTrue((result["skill_path"] / "SKILL.md").exists())
            self.assertTrue(result["config_snippet_path"].exists())
            self.assertTrue(result["env_example_path"].exists())
            self.assertTrue(result["default_env_path"].exists())
            self.assertTrue(result["default_config_path"].exists())

    def test_parse_dotenv_supports_basic_key_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "# comment\nDISCORD_BOT_TOKEN=test-token\nDISCORD_ALLOWED_USERS=123,456\n",
                encoding="utf-8",
            )

            parsed = parse_dotenv(env_file)
            self.assertEqual(parsed["DISCORD_BOT_TOKEN"], "test-token")
            self.assertEqual(parsed["DISCORD_ALLOWED_USERS"], "123,456")


if __name__ == "__main__":
    unittest.main()

