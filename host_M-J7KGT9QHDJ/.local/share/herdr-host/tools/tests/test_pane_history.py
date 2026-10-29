"""Tests for `herdr-tools focus record`, `back` and `forward`, against a fake herdr socket."""

import json
import subprocess
from pathlib import Path

from fake_socket import FakeSocket
from label_harness import run_label_command

from herdr_tools import pane_history


def test_selftest_passes() -> None:
    pane_history.selftest()


def _run(
    tmp_path: Path,
    fake: FakeSocket,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    # A subprocess: the state directory is read from the environment at import.
    return run_label_command(
        "herdr_tools.cli",
        tmp_path,
        tmp_path / "herdr-is-never-run",
        "focus",
        *args,
        env={
            "HERDR_SOCKET_PATH": str(fake.path),
            "HERDR_PLUGIN_STATE_DIR": str(tmp_path),
        },
    )


def test_record_puts_the_focused_pane_at_the_front_of_the_trail(tmp_path: Path) -> None:
    with FakeSocket() as fake:
        fake.reply("pane.current", {"pane": {"pane_id": "p1", "focused": True}})

        result = _run(tmp_path, fake, "record")

    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "trail.json").read_text())["order"] == ["p1"]


def test_back_survives_the_pane_closing_before_it_is_focused(tmp_path: Path) -> None:
    (tmp_path / "trail.json").write_text(json.dumps({"order": ["p1", "p2"], "at": 0}))
    with FakeSocket() as fake:
        fake.reply(
            "pane.list",
            {
                "panes": [
                    {"pane_id": "p1", "focused": True},
                    {"pane_id": "p2", "focused": False},
                ],
            },
        )
        fake.fail("pane.focus")

        result = _run(tmp_path, fake, "back")

        assert result.returncode == 0, result.stderr
        assert ("pane.focus", {"pane_id": "p2"}) in fake.requests


def test_forward_walks_towards_the_newer_pane(tmp_path: Path) -> None:
    (tmp_path / "trail.json").write_text(json.dumps({"order": ["p1", "p2"], "at": 1}))
    with FakeSocket() as fake:
        fake.reply(
            "pane.list",
            {
                "panes": [
                    {"pane_id": "p1", "focused": False},
                    {"pane_id": "p2", "focused": True},
                ],
            },
        )

        result: subprocess.CompletedProcess[str] = _run(tmp_path, fake, "forward")

        assert result.returncode == 0, result.stderr
        assert ("pane.focus", {"pane_id": "p1"}) in fake.requests
