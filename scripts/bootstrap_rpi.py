"""Bootstrap Hermes plus this extension on a Raspberry Pi 400 or similar Linux ARM host."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent


HERMES_INSTALL_COMMAND = "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"


@dataclass(frozen=True)
class BootstrapPlan:
    """A rendered bootstrap plan for the target system."""

    runtime_summary: str
    commands: list[str]
    notes: list[str]


def detect_runtime_summary() -> str:
    system = platform.system()
    machine = platform.machine()
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    return f"{system} {machine} / Python {python_version}"


def hermes_installed() -> bool:
    return shutil.which("hermes") is not None


def build_plan(*, hermes_home: Path, skip_hermes_install: bool) -> BootstrapPlan:
    commands: list[str] = []
    notes: list[str] = []

    system = platform.system().lower()
    machine = platform.machine().lower()
    if system != "linux":
        notes.append("Warning: the Raspberry Pi bootstrap is designed for Linux hosts.")
    if machine not in {"aarch64", "arm64", "armv7l", "armv8l"}:
        notes.append("Warning: this does not look like a Raspberry Pi ARM runtime.")

    if not hermes_installed() and not skip_hermes_install:
        commands.append(HERMES_INSTALL_COMMAND)
    elif skip_hermes_install:
        notes.append("Skipping Hermes install because --skip-hermes-install was provided.")
    else:
        notes.append("Hermes is already installed; skipping upstream install.")

    commands.append(
        f"{shlex.quote(sys.executable)} {shlex.quote(str(REPO_ROOT / 'scripts' / 'install_extension.py'))} "
        f"--hermes-home {shlex.quote(str(hermes_home))}"
    )

    notes.extend(
        [
            f"Edit {hermes_home / '.env'} and set DISCORD_BOT_TOKEN plus DISCORD_ALLOWED_USERS.",
            f"Merge {hermes_home / 'discord-admin.config.snippet.yaml'} into {hermes_home / 'config.yaml'}.",
            "If Hermes was just installed, reload the shell before running Hermes commands.",
            "Run `hermes gateway setup` or configure Discord manually, then start the gateway.",
            "For persistent service management on the Pi, use `hermes gateway install` and `hermes gateway start`.",
        ]
    )

    return BootstrapPlan(runtime_summary=detect_runtime_summary(), commands=commands, notes=notes)


def run_plan(plan: BootstrapPlan, *, hermes_home: Path) -> None:
    for command in plan.commands:
        subprocess.run(command, shell=True, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Hermes and this extension on a Raspberry Pi class host.")
    parser.add_argument(
        "--hermes-home",
        default=str(Path.home() / ".hermes"),
        help="Target Hermes home directory. Defaults to ~/.hermes",
    )
    parser.add_argument(
        "--skip-hermes-install",
        action="store_true",
        help="Do not run the official Hermes installer even if `hermes` is missing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned commands and notes without executing them.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    hermes_home = Path(args.hermes_home).expanduser()
    plan = build_plan(hermes_home=hermes_home, skip_hermes_install=args.skip_hermes_install)

    print(f"Runtime: {plan.runtime_summary}")
    print("Commands:")
    for command in plan.commands:
        print(f"  - {command}")
    print("Notes:")
    for note in plan.notes:
        print(f"  - {note}")

    if args.dry_run:
        return 0

    run_plan(plan, hermes_home=hermes_home)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

