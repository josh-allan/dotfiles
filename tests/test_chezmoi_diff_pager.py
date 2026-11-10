"""Run chezmoi's diff pager against fake rex and delta binaries.

Fake ``rex`` and ``delta`` come first on PATH and record what they get, so no block opens
and nothing pages. The fake ``rex`` reports chezmoi's terminal modes from files a test
writes. A stand-in for chezmoi runs the pager and then waits, as chezmoi does at a
prompt, until the test lets it exit.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGER = REPO / "home/dot_local/bin/chezmoi-diff-pager"
TIMEOUT = 5.0
BEFORE = "keep\nold\n"
AFTER = "keep\nnew\n"
PLAIN_DIFF = (
    "diff --git a/.config/demo b/.config/demo\n"
    "index 1111111..2222222 100644\n"
    "--- a/.config/demo\n"
    "+++ b/.config/demo\n"
    "@@ -1,2 +1,2 @@\n"
    " keep\n"
    "-old\n"
    "+new\n"
)
# chezmoi colours the diff whenever its stdout is a terminal.
COLOURED_DIFF = PLAIN_DIFF.replace("-old\n", "\x1b[31m-old\x1b[0m\n").replace(
    "+new\n", "\x1b[32m+new\x1b[0m\n"
)
NEW_DIRECTORY_DIFF = (
    "diff --git a/.config/new b/.config/new\n"
    "new file mode 0040000\n"
    "diff --git a/.config/new/file b/.config/new/file\n"
    "new file mode 100644\n"
    "index 0000000..3333333\n"
    "--- /dev/null\n"
    "+++ b/.config/new/file\n"
    "@@ -0,0 +1 @@\n"
    "+inside\n"
)
# Logs each call; answers `block call` from {state}/<method>, moving <method>.next in once
# read; holds `wait` until the block is closed.
FAKE_REX = """\
#!/bin/sh
printf '%s\\n' "$*" >>"{calls}"
case "$1" in
split) printf '%s\\n' "$@" >"{split_args}"; echo block:diff ;;
wait)
	i=0
	while [ ! -e "{state}/closed-$2" ] && [ $i -lt 200 ]; do sleep 0.05; i=$((i + 1)); done ;;
block)
	case "$2" in
	ls) cat "{state}/blocks.json" ;;
	close) : >"{state}/closed-$3" ;;
	call) cat "{state}/$5"; [ ! -e "{state}/$5.next" ] || mv "{state}/$5.next" "{state}/$5" ;;
	esac ;;
esac
"""
# What the pager writes to chezmoi's terminal to mark the prompt it waits on.
MARK = b"\x1b[?2004l"


def modes(*, cursor_visible: bool, bracketed_paste: bool) -> str:
    """``rex block call modes`` output for chezmoi's terminal, as rex prints it to a pipe."""
    entries = [
        {"name": "cursor_visible", "number": 25, "set": cursor_visible, "default": True},
        {"name": "bracketed_paste", "number": 2004, "set": bracketed_paste},
    ]
    return json.dumps({"screen": "primary", "modes": entries}, separators=(",", ":"))


ASKING = modes(cursor_visible=False, bracketed_paste=True)  # bubbletea prompt waiting
MARKED = modes(cursor_visible=False, bracketed_paste=False)  # same prompt, marked
AWAY = modes(cursor_visible=True, bracketed_paste=True)  # chezmoi working, or the shell


def until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + TIMEOUT
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"timed out waiting for {what}")
        time.sleep(0.02)


def show(repo: str, revision: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, "show", revision], capture_output=True, text=True, check=True
    ).stdout


class Rig:
    """A fake HOME, scratch TMPDIR, fake binaries, and a stand-in chezmoi."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.home = tmp / "home"
        (self.home / ".config").mkdir(parents=True)
        (self.home / ".config/demo").write_text(BEFORE)
        self.scratch = tmp / "scratch"
        self.scratch.mkdir()
        self.state = tmp / "state"
        self.state.mkdir()
        (self.state / "blocks.json").write_text('{"blocks":[]}')
        self.calls_file = tmp / "rex-calls"
        self.split_args = tmp / "rex-split"
        self.paged = tmp / "paged"
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        rex = bin_dir / "rex"
        rex.write_text(
            FAKE_REX.format(calls=self.calls_file, split_args=self.split_args, state=self.state)
        )
        delta = bin_dir / "delta"
        delta.write_text(f'#!/bin/sh\ncat >"{self.paged}"\n')
        for script in (rex, delta):
            script.chmod(0o755)
        user_home = tmp / "user"
        user_home.mkdir()
        base = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "REX_"))}
        self.env = {
            **base,
            "HOME": str(user_home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "TMPDIR": str(self.scratch),
            "CHEZMOI_DEST_DIR": str(self.home),
            "REX_SESSION": "session:chezmoi",
            "REX_BLOCK": "block:chezmoi",
        }
        self.chezmoi: subprocess.Popen[bytes] | None = None
        self.terminal = -1

    def page(self, command: str, diff: str = COLOURED_DIFF, *, in_rex: bool = True) -> str:
        """Page ``diff`` under the stand-in chezmoi; return the pager's stderr."""
        env = {**self.env, "CHEZMOI_COMMAND": command}
        if not in_rex:
            del env["REX_BLOCK"]
        (self.tmp / "diff").write_text(diff)
        self.terminal, terminal = os.pipe()
        self.chezmoi = subprocess.Popen(
            ["sh", "-c", 'sh "$0" <"$1" 2>"$2"; echo; read -r _', PAGER, "diff", "stderr"],
            cwd=self.tmp,
            env=env,
            stdin=subprocess.PIPE,
            stdout=terminal,
        )
        os.close(terminal)
        assert self.read_terminal(1) == b"\n"
        return (self.tmp / "stderr").read_text()

    def quit(self) -> None:
        if self.chezmoi is not None and self.chezmoi.returncode is None:
            self.chezmoi.communicate(timeout=TIMEOUT)

    def finish(self) -> None:
        """Let chezmoi and the diff's block go, then wait for the pager to tidy up."""
        self.quit()
        (self.state / "closed-block:diff").touch()
        until(lambda: not any(self.scratch.iterdir()), "the scratch repo to go")
        if self.terminal >= 0:
            os.close(self.terminal)

    def read_terminal(self, size: int) -> bytes:
        data = b""
        deadline = time.monotonic() + TIMEOUT
        while len(data) < size:
            ready, _, _ = select.select([self.terminal], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                pytest.fail(f"chezmoi's terminal got {data!r}, not {size} bytes")
            data += os.read(self.terminal, size - len(data))
        return data

    def calls(self) -> list[str]:
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def split(self) -> tuple[list[str], str]:
        """The argv the pager split a block with, and the repo it opened."""
        argv = self.split_args.read_text().splitlines()
        return argv, argv[argv.index("--cwd") + 1]

    def answer(self, act: Callable[[], object]) -> None:
        """Show a diff at apply's prompt, ``act`` on it, and check the block goes."""
        (self.state / "modes").write_text(ASKING)
        (self.state / "modes.next").write_text(MARKED)
        self.page("apply")
        assert self.read_terminal(len(MARK)) == MARK
        act()
        until(lambda: "block close block:diff" in self.calls(), "the diff to close")
        until(lambda: not any(self.scratch.iterdir()), "the scratch repo to go")


@pytest.fixture
def rig(tmp_path: Path) -> Iterator[Rig]:
    r = Rig(tmp_path)
    yield r
    r.finish()


def test_outside_rex_pages_through_delta(rig: Rig) -> None:
    rig.page("apply", in_rex=False)
    assert rig.paged.read_text() == COLOURED_DIFF
    assert not rig.split_args.exists()


def test_prompt_diff_opens_as_a_branch_off_the_files_as_they_are(rig: Rig) -> None:
    rig.page("apply")
    argv, repo = rig.split()
    assert argv[:6] == ["split", "-b", "block:chezmoi", "--focus=false", "--label", "chezmoi diff"]
    assert argv[-1] == ".config/demo"
    assert show(repo, "main:.config/demo") == BEFORE
    assert show(repo, "HEAD:.config/demo") == AFTER
    assert not rig.paged.exists()


def test_chezmoi_diff_opens_focused(rig: Rig) -> None:
    rig.page("diff")
    argv, _ = rig.split()
    assert argv[:4] == ["split", "-b", "block:chezmoi", "--focus=true"]


def test_earlier_diff_in_the_same_window_is_replaced(rig: Rig) -> None:
    blocks = [
        {"block_id": "block:chezmoi", "window_id": "window:here", "label": "fish"},
        {"block_id": "block:earlier", "window_id": "window:here", "label": "chezmoi diff"},
        {"block_id": "block:lazygit", "window_id": "window:here", "label": "lazygit"},
        {"block_id": "block:other", "window_id": "window:there", "label": "chezmoi diff"},
    ]
    (rig.state / "blocks.json").write_text(json.dumps({"blocks": blocks}))
    rig.page("apply")
    calls = rig.calls()
    closes = [i for i, c in enumerate(calls) if c.startswith("block close")]
    assert [calls[i] for i in closes] == ["block close block:earlier"]
    assert closes[0] < next(i for i, c in enumerate(calls) if c.startswith("split"))


def test_closes_once_chezmoi_moves_past_the_prompt(rig: Rig) -> None:
    rig.answer(lambda: (rig.state / "modes").write_text(AWAY))


def test_closes_once_a_later_prompt_starts(rig: Rig) -> None:
    rig.answer(lambda: (rig.state / "modes").write_text(ASKING))


def test_closes_once_chezmoi_exits(rig: Rig) -> None:
    rig.answer(rig.quit)


def test_diff_no_prompt_follows_stays_open(rig: Rig) -> None:
    (rig.state / "modes").write_text(AWAY)
    rig.page("apply")
    rig.quit()
    until(lambda: "wait block:diff" in rig.calls(), "the pager to stop watching")
    assert "block close block:diff" not in rig.calls()


def test_directory_entry_is_left_out_and_the_rest_opens(rig: Rig) -> None:
    stderr = rig.page("diff", NEW_DIRECTORY_DIFF + COLOURED_DIFF)
    _, repo = rig.split()
    assert show(repo, "HEAD:.config/new/file") == "inside\n"
    assert show(repo, "HEAD:.config/demo") == AFTER
    assert "Not in the review: .config/new\n" in stderr


def test_diff_that_does_not_apply_pages_through_delta_and_leaves_nothing(rig: Rig) -> None:
    (rig.home / ".config/demo").write_text("drifted\n")
    stderr = rig.page("apply")
    assert "Not in the review: .config/demo\n" in stderr
    assert rig.paged.read_text() == PLAIN_DIFF
    assert not rig.split_args.exists()
    assert list(rig.scratch.iterdir()) == []
