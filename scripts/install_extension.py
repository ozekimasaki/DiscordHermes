"""Cross-platform installer for the Hermes Discord admin companion layer."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


REPO_ROOT = Path(__file__).resolve().parent.parent


def render_config_snippet(repo_root: Path, audit_db_path: Path) -> str:
    launcher = repo_root / "scripts" / "launch_discord_admin_mcp.py"
    return "\n".join(
        [
            "discord:",
            "  require_mention: true",
            "",
            "group_sessions_per_user: true",
            "",
            "mcp_servers:",
            "  discord_admin:",
            '    command: "python"',
            f'    args: ["{launcher}"]',
            "    env:",
            f'      DISCORD_ADMIN_DB_PATH: "{audit_db_path}"',
            '      DISCORD_REQUEST_TIMEOUT_SECONDS: "15"',
            "    tools:",
            "      include:",
            "        - get_guild_summary",
            "        - list_categories",
            "        - list_channels",
            "        - list_roles",
            "        - get_member",
            "        - list_members_by_role",
            "        - create_role",
            "        - assign_role",
            "        - remove_role",
            "        - create_text_channel",
            "        - archive_channel",
            "        - move_channel_to_category",
            "        - post_announcement",
            "      prompts: false",
            "      resources: false",
            "",
        ]
    )


def write_text(path: Path, content: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def copy_tree(source: Path, destination: Path, *, force: bool = False) -> bool:
    if destination.exists():
        if not force:
            return False
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return True


def install_extension(hermes_home: Path, *, force: bool = False) -> dict[str, Path]:
    hermes_home.mkdir(parents=True, exist_ok=True)

    source_skill = REPO_ROOT / "extensions" / "skills" / "server-admin"
    target_skill = hermes_home / "skills" / "server-admin"
    source_env_example = REPO_ROOT / "config" / "hermes" / ".env.example"
    target_env_example = hermes_home / "discord-admin.env.example"
    source_env_text = source_env_example.read_text(encoding="utf-8")
    snippet_path = hermes_home / "discord-admin.config.snippet.yaml"
    snippet_text = render_config_snippet(REPO_ROOT, REPO_ROOT / ".state" / "discord-admin.db")

    copy_tree(source_skill, target_skill, force=force)
    write_text(target_env_example, source_env_text, force=True)
    write_text(snippet_path, snippet_text, force=True)

    default_env_path = hermes_home / ".env"
    default_config_path = hermes_home / "config.yaml"

    if not default_env_path.exists():
        write_text(default_env_path, source_env_text, force=False)
    if not default_config_path.exists():
        write_text(default_config_path, snippet_text, force=False)

    return {
        "skill_path": target_skill,
        "env_example_path": target_env_example,
        "config_snippet_path": snippet_path,
        "default_env_path": default_env_path,
        "default_config_path": default_config_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the Hermes Discord admin extension into a Hermes home.")
    parser.add_argument(
        "--hermes-home",
        default=str(Path.home() / ".hermes"),
        help="Target Hermes home directory. Defaults to ~/.hermes",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite the target skill directory if it exists.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = install_extension(Path(args.hermes_home).expanduser(), force=args.force)

    print(f"Skill synced to: {result['skill_path']}")
    print(f"Config snippet written to: {result['config_snippet_path']}")
    print(f"Env example written to: {result['env_example_path']}")
    if result["default_env_path"].exists():
        print(f"Hermes env path: {result['default_env_path']}")
    if result["default_config_path"].exists():
        print(f"Hermes config path: {result['default_config_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

