"""Tests for the `herdr-tools label pane` command.

The command tests run the real module with Herdr faked by `FakeHerdr` under a throwaway
`HOME`, so no sweep ever reaches a live server.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fake_herdr import FakeHerdr
from label_harness import run_label_command, writes

from herdr_tools import pane_label
from herdr_tools.client import HerdrClient


class PaneLabelTests(unittest.TestCase):
    def test_selftest_passes(self) -> None:
        pane_label.selftest()

    def test_unnumbered_inverts_numbered_at_every_position(self) -> None:
        for position in range(len(pane_label.BOXES) + 1):
            self.assertEqual(
                pane_label.unnumbered(pane_label.numbered("EXC-1 Diff", position)),
                "EXC-1 Diff",
            )


class ReaderTests(unittest.TestCase):
    def test_foreground_names_the_program_leading_the_group(self) -> None:
        fake = FakeHerdr(Path(self.enterContext(tempfile.TemporaryDirectory())))
        info = {
            "foreground_process_group_id": 7,
            "foreground_processes": [{"pid": 7, "argv0": "/opt/homebrew/bin/fish"}],
        }
        fake.reply(
            "pane process-info",
            json.dumps({"id": "1", "result": {"process_info": info}}),
        )
        self.assertEqual(
            pane_label.foreground(HerdrClient(fake.executable), "p1"),
            "fish",
        )


class SweepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.fake = FakeHerdr(self.home)

    def _writes(self) -> list[list[str]]:
        return writes(self.fake, ["pane", "report-metadata"], ["tab", "rename"])

    def _run(self, herdr: Path) -> subprocess.CompletedProcess[str]:
        return run_label_command("herdr_tools.cli", self.home, herdr, "label", "pane")

    def test_outside_herdr_exits_zero_and_writes_nothing(self) -> None:
        self.fake.fail("api snapshot", "no server")
        self.assertEqual(self._run(self.fake.executable).returncode, 0)
        self.assertEqual(self._writes(), [])

    def test_without_a_herdr_binary_exits_zero(self) -> None:
        self.assertEqual(self._run(self.home / "missing" / "herdr").returncode, 0)

    def test_labels_an_agent_pane_and_its_tab_through_the_configured_herdr(self) -> None:
        snapshot: dict[str, object] = {
            "panes": [
                {
                    "pane_id": "p1",
                    "tab_id": "t1",
                    "agent": "claude",
                    "terminal_title": "✳ Refactor",
                },
            ],
            "tabs": [{"tab_id": "t1", "workspace_id": "w1"}],
        }
        self.fake.reply("api snapshot", json.dumps({"result": {"snapshot": snapshot}}))
        self.assertEqual(self._run(self.fake.executable).returncode, 0)
        self.assertEqual(
            self._writes(),
            [
                [
                    "pane",
                    "report-metadata",
                    "p1",
                    "--source",
                    "user:pane-label",
                    "--title",
                    "Refactor",
                ],
                ["tab", "rename", "t1", pane_label.numbered("Refactor", 0)],
            ],
        )

    def test_a_prompt_unchecks_only_its_own_dispatched_tab(self) -> None:
        snapshot: dict[str, object] = {
            "panes": [
                {"pane_id": "p1", "tab_id": "t1", "agent": "claude", "label": "🤖 impl"},
                {
                    "pane_id": "p2",
                    "tab_id": "t2",
                    "agent": "claude",
                    "label": "🤖 review",
                },
            ],
            "tabs": [
                {
                    "tab_id": "t1",
                    "workspace_id": "w1",
                    "label": pane_label.numbered("🤖 ✅ impl", 0),
                },
                {
                    "tab_id": "t2",
                    "workspace_id": "w1",
                    "label": pane_label.numbered("🤖 ✅ review", 1),
                },
            ],
        }
        self.fake.reply("api snapshot", json.dumps({"result": {"snapshot": snapshot}}))

        run_label_command(
            "herdr_tools.cli",
            self.home,
            self.fake.executable,
            *("label", "pane", "--prompt-title", "Read and follow brief-2.md"),
            env={"HERDR_PANE_ID": "p1"},
        )

        self.assertEqual(
            writes(self.fake, ["tab", "rename"]),
            [["tab", "rename", "t1", pane_label.numbered("🤖 impl", 0)]],
        )
