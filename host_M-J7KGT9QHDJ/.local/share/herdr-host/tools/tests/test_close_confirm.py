"""Tests for `herdr-tools close`, against a fake herdr socket and binary."""

import contextlib
import json
import os
import pty
import subprocess
import sys
import termios
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from fake_herdr import FakeHerdr
from fake_socket import FakeSocket
from label_harness import run_label_command, writes

from herdr_tools import close_confirm


def test_selftest_passes() -> None:
    close_confirm.selftest()


_PLUGIN_CONTEXT: Final = {
    "HERDR_PLUGIN_CONTEXT_JSON": json.dumps({
        "workspace_id": "w1",
        "tab_id": "t1",
        "focused_pane_id": "p1",
    }),
}


def _close(
    tmp_path: Path,
    herdr: FakeHerdr,
    fake: FakeSocket,
    mode: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_label_command(
        "herdr_tools.cli",
        tmp_path,
        herdr.executable,
        "close",
        mode,
        env={"HERDR_SOCKET_PATH": str(fake.path), **(env or {})},
    )


def _press(
    tmp_path: Path,
    herdr: FakeHerdr,
    fake: FakeSocket,
    mode: str,
    process_info: Mapping[str, object],
) -> subprocess.CompletedProcess[str]:
    """Press `mode`'s close key on p1, one of two panes in t1, one of two tabs in w1."""
    fake.reply(
        "pane.list",
        {"panes": [{"pane_id": "p1", "tab_id": "t1"}, {"pane_id": "p2", "tab_id": "t1"}]},
    )
    fake.reply("tab.list", {"tabs": [{"tab_id": "t1"}, {"tab_id": "t2"}]})
    fake.reply(
        "workspace.list",
        {"workspaces": [{"workspace_id": "w1", "worktree": None}]},
    )
    fake.reply("pane.process_info", {"process_info": process_info})
    fake.reply(f"{mode}.close", {})
    return _close(tmp_path, herdr, fake, mode, _PLUGIN_CONTEXT)


_IDLE: Final = {"shell_pid": 10, "foreground_process_group_id": 10}


def test_an_idle_pane_among_others_closes_without_a_popup(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        result: subprocess.CompletedProcess[str] = _press(
            tmp_path,
            herdr,
            fake,
            "pane",
            _IDLE,
        )

        assert result.returncode == 0, result.stderr
        assert ("pane.close", {"pane_id": "p1"}) in fake.requests
    assert not writes(herdr, ["plugin", "pane"])


def test_a_busy_pane_asks_in_a_popup_before_closing(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    busy = {
        "shell_pid": 10,
        "foreground_process_group_id": 20,
        "foreground_processes": [{"pid": 20, "argv0": "claude", "name": "claude"}],
    }
    with FakeSocket() as fake:
        result: subprocess.CompletedProcess[str] = _press(
            tmp_path,
            herdr,
            fake,
            "pane",
            busy,
        )

        assert result.returncode == 0, result.stderr
        assert not [request for request in fake.requests if request[0] == "pane.close"]
    [popup] = writes(herdr, ["plugin", "pane"])
    assert popup[popup.index("--entrypoint") + 1] == "confirm"


def test_an_idle_tab_among_others_closes_without_a_popup(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        result: subprocess.CompletedProcess[str] = _press(
            tmp_path,
            herdr,
            fake,
            "tab",
            _IDLE,
        )

        assert result.returncode == 0, result.stderr
        assert ("tab.close", {"tab_id": "t1"}) in fake.requests
    assert not writes(herdr, ["plugin", "pane"])


def test_an_idle_workspace_closes_as_a_group_without_a_popup(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        result: subprocess.CompletedProcess[str] = _press(
            tmp_path,
            herdr,
            fake,
            "workspace",
            _IDLE,
        )

        assert result.returncode == 0, result.stderr
        assert (
            "workspace.close",
            {"workspace_id": "w1", "close_group": True},
        ) in fake.requests
    assert not writes(herdr, ["plugin", "pane"])


def test_a_press_without_a_plugin_context_exits_with_one_line(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        result: subprocess.CompletedProcess[str] = _close(
            tmp_path,
            herdr,
            fake,
            "pane",
            {"HERDR_PLUGIN_CONTEXT_JSON": "{}"},
        )

    assert result.returncode == 1
    assert result.stderr == "herdr-tools close: no focused pane in the plugin context\n"


def test_a_herdr_failure_exits_with_one_line(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        fake.fail("pane.list")
        result: subprocess.CompletedProcess[str] = _close(
            tmp_path,
            herdr,
            fake,
            "pane",
            _PLUGIN_CONTEXT,
        )

    assert result.returncode == 1
    assert result.stderr == "herdr-tools close: herdr pane.list: pane.list failed\n"


def _answer(tmp_path: Path, herdr: FakeHerdr, fake: FakeSocket, key: bytes) -> int:
    """Answer a tab-close popup with `key` on a real tty, returning the exit code."""
    prompt = close_confirm.Prompt(
        target="tab",
        pressed="tab",
        target_id="t1",
        location="w · t",
        running=["claude"],
    )
    environ: dict[str, str] = {
        **os.environ,
        "HOME": str(tmp_path),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "HERDR_BIN_PATH": str(herdr.executable),
        "HERDR_SOCKET_PATH": str(fake.path),
        "CLOSE_CONFIRM_JSON": prompt.to_json(),
    }
    for name in ("HERDR_ENV", "HERDR_PANE_ID", "HERDR_WORKSPACE_ID", "HERDR_PLUGIN_ID"):
        environ.pop(name, None)
    master, slave = pty.openpty()
    termios.tcsetwinsize(slave, (11, 62))
    process = subprocess.Popen(
        [sys.executable, "-m", "herdr_tools.cli", "close", "confirm"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=environ,
    )
    os.close(slave)
    os.read(master, 1024)  # The prompt has drawn; setraw discards input sent before it.
    os.write(master, key)
    with contextlib.suppress(OSError):
        while os.read(master, 1024):
            pass
    os.close(master)
    return process.wait(timeout=30)


def test_a_yes_in_the_popup_closes_its_target(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        fake.reply("tab.close", {})
        returncode: int = _answer(tmp_path, herdr, fake, b"y")

        assert returncode == 0
        assert ("tab.close", {"tab_id": "t1"}) in fake.requests


def test_a_no_in_the_popup_closes_nothing(tmp_path: Path) -> None:
    herdr = FakeHerdr(tmp_path)
    with FakeSocket() as fake:
        fake.reply("tab.close", {})
        returncode: int = _answer(tmp_path, herdr, fake, b"n")

        assert returncode == 0
        assert not fake.requests
