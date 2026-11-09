"""Run the fish prompt functions against a fake HOME and throwaway git repos."""

import os
import pty
import re
import select
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FISH = REPO / "home/dot_config/fish"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x1b]*\x1b\\|\x1b[()=>][0-9A-Za-z]?")
TIME = r"\d\d:\d\d:\d\d"

pytestmark = pytest.mark.skipif(shutil.which("fish") is None, reason="fish not installed")


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def repo(home: Path) -> Path:
    """Repo at ~/.dotfiles with one commit; x has two lines."""
    root = home / ".dotfiles"
    (root / "home/dot_config/fish").mkdir(parents=True)
    (root / "x").write_text("a\nb\n")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


def fish_raw(home: Path, script: str, cwd: Path | None = None) -> str:
    """Load the prompt files non-interactively, run script, return output with colours."""
    setup = f"set fish_function_path {FISH}/functions $fish_function_path; source {FISH}/conf.d/prompt.fish; true; "
    result = subprocess.run(
        ["fish", "--no-config", "-c", setup + script],
        cwd=cwd or home,
        env={**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "cfg")},
        capture_output=True,
        text=True,
    )
    assert result.stderr == ""
    return result.stdout


def fish(home: Path, script: str, cwd: Path | None = None) -> str:
    return ANSI.sub("", fish_raw(home, script, cwd))


def prompt(home: Path, cwd: Path, columns: int = 100, before: str = "") -> list[str]:
    return fish(home, f"set COLUMNS {columns}; {before} fish_prompt", cwd).split("\n")


@pytest.mark.parametrize(("ms", "text"), [(850, "850ms"), (4210, "4.2s"), (192000, "3m12s")])
def test_duration_format(home: Path, ms: int, text: str) -> None:
    assert fish(home, f"_prompt_duration {ms}") == f"{text}\n"


@pytest.mark.parametrize(
    ("rel", "full", "short"),
    [
        (".dotfiles/home/dot_config/fish", "~ / .dotfiles / home / dot_config / fish", "~/.d/h/d/fish"),
        ("", "~", "~"),
    ],
)
def test_breadcrumb_under_home(home: Path, repo: Path, rel: str, full: str, short: str) -> None:
    cwd = home / rel
    assert fish(home, "_prompt_breadcrumb full", cwd) == full
    assert fish(home, "_prompt_breadcrumb short", cwd) == short
    assert fish(home, "_prompt_breadcrumb leaf", cwd) == full.split(" / ")[-1]


def test_breadcrumb_outside_home(home: Path) -> None:
    assert fish(home, "_prompt_breadcrumb full", Path("/usr/bin")) == "/usr / bin"
    assert fish(home, "_prompt_breadcrumb short", Path("/usr/bin")) == "/u/bin"
    assert fish(home, "_prompt_breadcrumb full", Path("/")) == "/"


def run_worker(home: Path, repo: Path, seq: int = 1) -> list[str]:
    out = home / "diff"
    fish(home, f"function h --on-signal SIGUSR1; end; _prompt_diff_worker {seq} {repo} {out} $fish_pid", repo)
    return out.read_text().split()


@pytest.mark.parametrize(
    ("content", "counts"),
    [("a\nb\nc\n", ["1", "0"]), ("a\n", ["0", "1"]), ("c\nd\ne\n", ["3", "2"]), ("a\nb\n", ["0", "0"])],
)
def test_worker_counts(home: Path, repo: Path, content: str, counts: list[str]) -> None:
    (repo / "x").write_text(content)
    seq, root, *rest = run_worker(home, repo)
    assert (seq, Path(root).resolve(), rest) == ("1", repo.resolve(), counts)


def test_status_parts(home: Path, repo: Path) -> None:
    assert re.fullmatch(rf"⎇ main · {TIME}", fish(home, "_prompt_status 0 0 yes", repo))
    assert fish(home, "_prompt_status 1 4210 no", repo) == "exit 1 after 4.2s · ⎇ main"
    assert fish(home, "_prompt_status 0 0 no", home) == ""


def test_clean_repo(home: Path, repo: Path) -> None:
    line1, line2 = prompt(home, repo / "home/dot_config/fish")
    assert re.fullmatch(rf"~ / \.dotfiles / home / dot_config / fish +⎇ main · {TIME}", line1)
    assert len(line1) == 99
    assert line2 == "› "


def test_failure_shows_exit_and_duration(home: Path, repo: Path) -> None:
    line1, _ = prompt(home, repo, before="set CMD_DURATION 4210; false;")
    assert re.search(rf"exit 1 after 4\.2s · ⎇ main · {TIME}$", line1)


def test_detached_head_shows_short_sha(home: Path, repo: Path) -> None:
    git(repo, "checkout", "-q", "--detach")
    line1, _ = prompt(home, repo)
    assert re.search(rf"⎇ [0-9a-f]{{7,}} · {TIME}$", line1)


def test_outside_repo_has_no_git(home: Path) -> None:
    line1, _ = prompt(home, home)
    assert re.fullmatch(rf"~ +{TIME}", line1)


def test_blank_line_only_after_a_command(home: Path, repo: Path) -> None:
    assert prompt(home, repo)[0] != ""
    assert prompt(home, repo, before="set -g _prompt_blank_line;")[0] == ""


@pytest.mark.parametrize(
    ("columns", "pattern"),
    [
        (50, rf"~/\.d/h/d/fish +⎇ main · {TIME}"),
        (30, r"~/\.d/h/d/fish +⎇ main"),
        (16, r"fish +⎇ main"),
        (10, r"fish "),
    ],
)
def test_width_fallback(home: Path, repo: Path, columns: int, pattern: str) -> None:
    line1, _ = prompt(home, repo / "home/dot_config/fish", columns)
    assert re.fullmatch(pattern, line1)


def test_diffstat_drawn_for_matching_repo_only(home: Path, repo: Path) -> None:
    root = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    line1, _ = prompt(home, repo, before=f"set _prompt_diff {root} 14 3;")
    assert re.search(rf"⎇ main \+14 −3 · {TIME}$", line1)
    line1, _ = prompt(home, repo, before="set _prompt_diff /elsewhere 14 3;")
    assert re.search(rf"⎇ main · {TIME}$", line1)


def test_final_rendering(home: Path, repo: Path) -> None:
    assert re.fullmatch(rf"{TIME} › ", fish(home, "fish_prompt --final-rendering", repo))


def test_async_diffstat_repaints_prompt(home: Path, repo: Path) -> None:
    (repo / "x").write_text("c\nd\ne\n")
    init = (
        f"set fish_function_path {FISH}/functions $fish_function_path; source {FISH}/conf.d/prompt.fish; "
        "set -g prompts 0; function _count --on-event fish_prompt; set -g prompts (math $prompts + 1); end"
    )
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "cfg"), "TERM": "xterm-256color"}
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(repo)
        os.execvpe("fish", ["fish", "--no-config", "-i", "-C", init], env)
    log = b""
    try:
        deadline = time.time() + 5
        while time.time() < deadline and "+3 −2".encode() not in log:
            if select.select([fd], [], [], 0.05)[0]:
                chunk = os.read(fd, 65536)
                log += chunk
                if b"\x1b[0c" in chunk:  # fish waits for the terminal's device-attributes reply
                    os.write(fd, b"\x1b[?62;22c")
        os.write(fd, b"echo PROMPTS=$prompts\r")
        deadline = time.time() + 3
        while time.time() < deadline and not re.search(rb"PROMPTS=\d", log):
            if select.select([fd], [], [], 0.05)[0]:
                log += os.read(fd, 65536)
    finally:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    out = ANSI.sub("", log.decode(errors="replace"))
    assert "⎇ main +3 −2" in out
    assert "PROMPTS=1" in out  # the repaint did not start another prompt cycle



# Vi mode caret


def rgb(hex_color: str) -> str:
    """Truecolor SGR parameters; fish may merge bold into the same escape."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"38;2;{r};{g};{b}"


def caret(home: Path, mode: str, bindings: str = "fish_hybrid_key_bindings", failed: bool = False) -> str:
    """Line 2 of the prompt, colours kept, for a bind mode."""
    fail = "false; " if failed else ""
    return fish_raw(home, f"set -g fish_key_bindings {bindings}; set -g fish_bind_mode {mode}; {fail}_prompt_caret $status")


@pytest.mark.parametrize(
    ("mode", "glyph", "color"),
    [
        ("insert", "›", "b4befe"),
        ("default", "‹", "a6e3a1"),
        ("visual", "‹", "cba6f7"),
        ("replace_one", "›", "fab387"),
        ("replace", "›", "fab387"),
    ],
)
def test_caret_per_vi_mode(home: Path, mode: str, glyph: str, color: str) -> None:
    out = caret(home, mode)
    assert ANSI.sub("", out) == f"{glyph} "
    assert rgb(color) in out


def test_caret_red_after_failure_keeps_mode_glyph(home: Path) -> None:
    out = caret(home, "default", failed=True)
    assert ANSI.sub("", out) == "‹ "
    assert rgb("f38ba8") in out


def test_caret_ignores_bind_mode_with_default_bindings(home: Path) -> None:
    out = caret(home, "default", bindings="fish_default_key_bindings")
    assert ANSI.sub("", out) == "› "
    assert rgb("b4befe") in out


def test_key_bindings_conf_sets_hybrid_and_cursors(home: Path) -> None:
    out = fish(home, f"source {FISH}/conf.d/key_bindings.fish; echo $fish_key_bindings $fish_cursor_insert $fish_cursor_default $fish_cursor_external")
    assert out == "fish_hybrid_key_bindings line block block\n"


def test_escape_switches_live_caret_to_normal_mode(home: Path) -> None:
    init = (
        f"set fish_function_path {FISH}/functions $fish_function_path; "
        f"source {FISH}/conf.d/prompt.fish; source {FISH}/conf.d/key_bindings.fish; "
        # --no-config skips fish's interactive setup, which is what loads $fish_key_bindings.
        "$fish_key_bindings"
    )
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "cfg"), "TERM": "xterm-256color"}
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(home)
        os.execvpe("fish", ["fish", "--no-config", "-i", "-C", init], env)
    log = b""

    def read_until(needle: bytes, seconds: float) -> bytes:
        """Output from now until needle appears or time runs out."""
        nonlocal log
        start = len(log)
        deadline = time.time() + seconds
        while time.time() < deadline and needle not in log[start:]:
            if select.select([fd], [], [], 0.05)[0]:
                chunk = os.read(fd, 65536)
                log += chunk
                if b"\x1b[0c" in chunk:  # fish waits for the terminal's device-attributes reply
                    os.write(fd, b"\x1b[?62;22c")
        return log[start:]

    try:
        read_until("› ".encode(), 5)
        os.write(fd, b"\x1b")
        normal = read_until("‹ ".encode(), 3)
        os.write(fd, b"i")
        insert = read_until("› ".encode(), 3)
    finally:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    assert "‹ ".encode() in normal
    assert b"\x1b[2 q" in normal  # block cursor
    assert "› ".encode() in insert
    assert b"\x1b[6 q" in insert  # line cursor
