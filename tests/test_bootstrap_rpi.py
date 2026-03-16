from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts.bootstrap_rpi import build_plan


class BootstrapRpiTests(unittest.TestCase):
    @mock.patch("scripts.bootstrap_rpi.hermes_installed", return_value=False)
    @mock.patch("scripts.bootstrap_rpi.platform.machine", return_value="aarch64")
    @mock.patch("scripts.bootstrap_rpi.platform.system", return_value="Linux")
    def test_build_plan_includes_hermes_install_when_missing(self, *_mocks) -> None:
        plan = build_plan(hermes_home=Path("/home/pi/.hermes"), skip_hermes_install=False)
        self.assertTrue(any("install.sh" in command for command in plan.commands))
        self.assertTrue(any("install_extension.py" in command for command in plan.commands))

    @mock.patch("scripts.bootstrap_rpi.hermes_installed", return_value=True)
    @mock.patch("scripts.bootstrap_rpi.platform.machine", return_value="aarch64")
    @mock.patch("scripts.bootstrap_rpi.platform.system", return_value="Linux")
    def test_build_plan_skips_install_when_hermes_exists(self, *_mocks) -> None:
        plan = build_plan(hermes_home=Path("/home/pi/.hermes"), skip_hermes_install=False)
        self.assertFalse(any("install.sh" in command for command in plan.commands))
        self.assertTrue(any("already installed" in note for note in plan.notes))

    @mock.patch("scripts.bootstrap_rpi.hermes_installed", return_value=False)
    @mock.patch("scripts.bootstrap_rpi.platform.machine", return_value="x86_64")
    @mock.patch("scripts.bootstrap_rpi.platform.system", return_value="Windows")
    def test_build_plan_warns_on_non_pi_runtime(self, *_mocks) -> None:
        plan = build_plan(hermes_home=Path("/tmp/.hermes"), skip_hermes_install=True)
        self.assertTrue(any("Linux hosts" in note for note in plan.notes))
        self.assertTrue(any("Pi ARM" in note for note in plan.notes))


if __name__ == "__main__":
    unittest.main()

