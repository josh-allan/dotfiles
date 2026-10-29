"""Tests for `herdr-tools focus watch`, against a fake herdr socket."""

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from fake_socket import FakeSocket

from herdr_tools import focus_watch
from herdr_tools.client import HerdrClient


def test_selftest_passes() -> None:
    focus_watch.selftest()


def test_help_exits_cleanly() -> None:
    subprocess.run(
        [sys.executable, "-m", "herdr_tools.cli", "focus", "watch", "--help"],
        check=True,
        capture_output=True,
    )


def _detach_spawns() -> list[tuple[list[str], bool]]:
    spawned: list[tuple[list[str], bool]] = []

    def fake_popen(argv: list[str], *, start_new_session: bool, **_: object) -> None:
        spawned.append((argv, start_new_session))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(focus_watch.subprocess, "Popen", fake_popen)
        focus_watch.watch_command(detach=True)
    return spawned


def test_detach_spawns_focus_watch_in_its_own_session() -> None:
    spawned: list[tuple[list[str], bool]] = _detach_spawns()

    assert spawned == [
        ([sys.executable, "-P", "-m", "herdr_tools.cli", "focus", "watch"], True),
    ]


def test_the_detach_argv_runs_the_poller(tmp_path: Path) -> None:
    [(argv, _)] = _detach_spawns()
    environ_without_herdr = {
        name: value for name, value in os.environ.items() if not name.startswith("HERDR_")
    }

    result: subprocess.CompletedProcess[str] = subprocess.run(
        argv,
        env={
            **environ_without_herdr,
            "HERDR_PLUGIN_STATE_DIR": str(tmp_path),
            "HERDR_SOCKET_PATH": str(tmp_path / "missing.sock"),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "poller.lock").read_text().isdecimal()


def test_focused_returns_the_current_pane() -> None:
    with FakeSocket() as fake:
        fake.reply("pane.current", {"pane": {"pane_id": "p7"}})
        assert focus_watch.focused(HerdrClient(Path("herdr"), socket=fake.path)) == "p7"


def test_notify_reaches_every_consumer_despite_errors() -> None:
    with FakeSocket() as fake:
        fake.fail("plugin.action.invoke")
        focus_watch.notify(HerdrClient(Path("herdr"), socket=fake.path))
        methods = [method for method, _ in fake.requests]

    assert methods == ["plugin.action.invoke"] * 3


def test_poll_returns_when_the_socket_is_gone(tmp_path: Path) -> None:
    herdr = HerdrClient(Path("herdr"), socket=tmp_path / "missing.sock")
    thread = threading.Thread(target=focus_watch.poll, args=(herdr,), daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
