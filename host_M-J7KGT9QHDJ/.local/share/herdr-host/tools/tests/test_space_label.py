"""Tests for the `herdr-tools label space` command.

The command tests run the real module with Herdr faked by `FakeHerdr` under a throwaway
`HOME`, so no sweep ever reaches a live server.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fake_herdr import FakeHerdr
from label_harness import run_label_command, writes

from herdr_tools import space_label
from herdr_tools.client import HerdrClient

_CLI_MODULE = "herdr_tools.cli"
_PANE_WRITE = ["pane", "report-metadata"]
_SPACE_WRITE = ["workspace", "report-metadata"]
#: Bare, sweep, and the SessionEnd hook's pane-cwd outside a pane — each one sweeps.
_INVOCATIONS = ((), ("--sweep",), ("--pane-cwd",))


class SpaceLabelTests(unittest.TestCase):
    def test_selftest_passes(self) -> None:
        space_label.selftest()

    def test_help_exits_zero(self) -> None:
        subprocess.run(
            [sys.executable, "-m", _CLI_MODULE, "label", "space", "--help"],
            capture_output=True,
            check=True,
        )


class ReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeHerdr(Path(self.enterContext(tempfile.TemporaryDirectory())))
        self.herdr = HerdrClient(self.fake.executable)

    def test_get_pane_reads_the_pane_herdr_holds(self) -> None:
        self.fake.reply(
            "pane get",
            json.dumps({
                "id": "1",
                "result": {"pane": {"pane_id": "p1", "label": "🤖 impl"}},
            }),
        )
        pane: space_label.Pane | None = space_label.get_pane(self.herdr, "p1")
        self.assertIsNotNone(pane)
        assert pane is not None
        self.assertTrue(pane.dispatched)

    def test_space_info_reads_focus_and_slot(self) -> None:
        workspace = {"workspace_id": "w1", "focused": True, "number": 3}
        self.fake.reply(
            "workspace get",
            json.dumps({"id": "1", "result": {"workspace": workspace}}),
        )
        self.assertEqual(
            space_label.space_info(self.herdr, "w1"),
            space_label.Workspace(workspace_id="w1", focused=True, number=3),
        )


class SweepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.fake = FakeHerdr(self.home)

    def _run(
        self,
        herdr: Path,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return run_label_command(
            _CLI_MODULE,
            self.home,
            herdr,
            "label",
            "space",
            *args,
            env=env,
        )

    def _spaces(self) -> list[list[str]]:
        return writes(self.fake, _SPACE_WRITE)

    def test_outside_herdr_exits_zero_and_writes_nothing(self) -> None:
        self.fake.fail("api snapshot", "no server")
        for args in _INVOCATIONS:
            with self.subTest(args=args):
                self.assertEqual(self._run(self.fake.executable, *args).returncode, 0)
        self.assertEqual(writes(self.fake, _PANE_WRITE, _SPACE_WRITE), [])

    def test_without_a_herdr_binary_exits_zero(self) -> None:
        for args in _INVOCATIONS:
            with self.subTest(args=args):
                missing: Path = self.home / "missing" / "herdr"
                self.assertEqual(self._run(missing, *args).returncode, 0)

    def test_sweep_labels_a_space_through_the_configured_herdr(self) -> None:
        snapshot: dict[str, object] = {
            "panes": [{"pane_id": "p1", "workspace_id": "w1", "cwd": str(self.home)}],
            "workspaces": [{"workspace_id": "w1", "number": 1}],
        }
        self.fake.reply(
            "api snapshot",
            json.dumps({"id": "1", "result": {"snapshot": snapshot}}),
        )
        for args in _INVOCATIONS:
            with self.subTest(args=args):
                before: int = len(self._spaces())
                self.assertEqual(self._run(self.fake.executable, *args).returncode, 0)
                spaces: list[list[str]] = self._spaces()
                self.assertEqual(len(spaces), before + 1)
                self.assertEqual(spaces[-1][2:5], ["w1", "--source", "user:space-label"])

    def test_a_dispatched_pane_labels_itself_but_not_its_parents_space(self) -> None:
        pane = {"pane_id": "p1", "workspace_id": "w1", "label": "🤖 EXC-1 impl"}
        self.fake.reply("pane get", json.dumps({"id": "1", "result": {"pane": pane}}))
        env = {"HERDR_WORKSPACE_ID": "w1", "HERDR_PANE_ID": "p1"}
        result = self._run(self.fake.executable, "--cwd", str(self.home), env=env)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._spaces(), [])
        self.assertEqual([call[2] for call in writes(self.fake, _PANE_WRITE)], ["p1"])
