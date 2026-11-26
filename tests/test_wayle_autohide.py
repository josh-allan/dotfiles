"""Run wayle-autohide against fake hyprctl, nc (Hyprland event socket) and wayle."""

import os
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "home/dot_local/bin/wayle-autohide"
PEEK_MS = 400


@dataclass
class Rig:
    proc: subprocess.Popen[str]
    events: object
    cursor: Path
    log: Path
    wayle_failures: Path

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def move(self, x: int, y: int) -> None:
        self.cursor.write_text(f"{x}, {y}\n")

    def send(self, event: str) -> None:
        self.events.write(event + "\n")
        self.events.flush()


def write_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def wait_for(check: Callable[[], bool], timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.05)
    raise AssertionError("condition not met in time")


@pytest.fixture
def rig(tmp_path: Path) -> Iterator[Rig]:
    home, fakes = tmp_path / "home", tmp_path / "bin"
    fifo, cursor, log = tmp_path / "events", tmp_path / "cursor", tmp_path / "wayle.log"
    failures = tmp_path / "wayle-failures"
    os.mkfifo(fifo)
    cursor.write_text("500, 500\n")
    write_exe(fakes / "nc", f'exec cat "{fifo}"\n')
    write_exe(fakes / "hyprctl", f'[ "$1" = cursorpos ] && cat "{cursor}"\n')
    write_exe(
        home / ".cargo/bin/wayle",
        f'n=$(cat "{failures}" 2>/dev/null || echo 0)\n'
        f'if [ "$n" -gt 0 ]; then echo $((n - 1)) > "{failures}"; exit 1; fi\n'
        f'echo "$*" >> "{log}"\n',
    )
    env = {
        "HOME": str(home),
        "PATH": f"{fakes}:/usr/bin:/bin",
        "XDG_RUNTIME_DIR": str(tmp_path),
        "HYPRLAND_INSTANCE_SIGNATURE": "test",
        "WAYLE_AUTOHIDE_PEEK_MS": str(PEEK_MS),
    }
    proc = subprocess.Popen(["bash", str(SCRIPT)], env=env, text=True)
    events = os.fdopen(os.open(fifo, os.O_RDWR), "w")  # O_RDWR: never blocks on a missing reader
    r = Rig(proc, events, cursor, log, failures)
    yield r
    if not events.closed:
        events.close()
    proc.kill()
    proc.wait()


def test_hides_bar_on_start(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])


def test_shows_at_top_edge_until_cursor_leaves_bar(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])
    rig.move(500, 0)
    wait_for(lambda: rig.calls()[-1:] == ["panel show"])
    rig.move(500, 20)  # still over the bar: stays shown
    time.sleep(0.4)
    assert rig.calls()[-1] == "panel show"
    rig.move(500, 300)
    wait_for(lambda: rig.calls() == ["panel hide", "panel show", "panel hide"])


def test_cursor_below_edge_does_not_reveal(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])
    rig.move(500, 20)
    time.sleep(0.4)
    assert rig.calls() == ["panel hide"]


def test_workspace_switch_peeks_then_hides(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])
    rig.send("workspacev2>>2,2")
    wait_for(lambda: rig.calls()[-1:] == ["panel show"], timeout=PEEK_MS / 2000)
    wait_for(lambda: rig.calls() == ["panel hide", "panel show", "panel hide"])


def test_other_events_do_not_peek(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])
    rig.send("activewindowv2>>55fa217abbb0")
    time.sleep(0.4)
    assert rig.calls() == ["panel hide"]


def test_retries_until_panel_is_up(rig: Rig) -> None:
    rig.wayle_failures.write_text("3\n")
    wait_for(lambda: rig.calls() == ["panel hide"])


def test_exits_when_event_stream_closes(rig: Rig) -> None:
    wait_for(lambda: rig.calls() == ["panel hide"])
    rig.events.close()
    assert rig.proc.wait(timeout=3) == 0
