"""Report what a herdr space is working on as its sidebar tokens.

Three things the built-in tokens cannot say on their own:

* ``$repo`` — a worktree under ``~/wt/<repo>/`` is named after its branch
  (``EXC-1+add-thing``), so the cwd basename herdr labels a space with names
  the branch, not the repository. This resolves the remote instead, behind the
  boxed digit for where the space sits in the sidebar, which is the key that
  reaches it under the workspace picker. herdr numbers the spaces itself but
  publishes no token for the number. It rides on ``$repo`` rather than taking a
  token of its own because herdr puts a " · " between two tokens in a row and
  offers no way to suppress it.
* ``$branch`` / ``$focused_branch`` — the built-in ``branch`` token follows the
  pane's *shell* cwd, which an agent never moves: Claude Code relocates its own
  process into a worktree, and the shell it was launched from stays where it
  was. Both keys carry the same value; which one is set says whether the space
  is focused, and the two get different styling in config.toml. That is the only
  way to bold one space's branch and not another's, since herdr styles a row
  slot rather than a value.
* the pane-scoped ``$branch`` — the same branch reported against the pane, so
  the Agent panel names each agent's worktree separately when two of them are
  working in different ones at once.

Where the branch comes from depends on who is asking, because only the caller
knows whose directory is authoritative. The mode flags are mutually exclusive —
naming two sources is a caller bug, not a precedence question:

* a **sweep** (herdr plugin startup, ``workspace.focused``) reads herdr's own
  snapshot and prefers each pane's ``foreground_cwd`` — the cwd of the process
  controlling the pane, which is the agent when one is running. This is the
  self-healing path: it re-derives every space from scratch, so a session that
  was killed without running its exit hook is corrected on the next focus
  switch.
* ``workspace.created`` names one space and its directory.
* a **pane shell** (the fish hook on cd) is the directory, so its own cwd is it.
* ``--stdin-cwd`` reads a Claude Code hook payload and takes the session's cwd,
  which is already the new worktree by the time ``PostToolUse`` fires.
* ``--pane-cwd`` asks herdr for the pane's shell cwd, which is what SessionEnd
  wants: the agent process still exists at that point, so its own cwd is about
  to stop being true.
* ``--cwd PATH`` is told outright, for the OpenCode plugin — OpenCode never
  relocates its session, so nothing but the plugin knows where the run went.

``selftest`` checks that a repo and a branch still resolve out of a real
checkout; a pytest test runs it under the project's check.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Final

from cyclopts import Group, Parameter, validators
from pydantic import BaseModel, ValidationError

from herdr_tools.client import HerdrClient, best_effort
from herdr_tools.pane_label import ROBOT
from herdr_tools.replies import Reply, parse

SOURCE: Final = "user:space-label"
TIMEOUT: Final = 10
# Shown when a directory is not in a repository at all, so a space that has
# wandered out of a project says so rather than showing a bare directory name.
NO_REPO: Final = "(no repo)"
# nf-md-numeric_1_box through _9_box, then nf-md-numeric_0_box — the number row
# of a keyboard in the order the keys sit on it, so a space's glyph reads as the
# key that reaches it. The codepoints are not contiguous, so this is a literal
# rather than arithmetic. The same glyphs number a tab in the tab bar.
BOXES: Final = (
    "\U000f03a4\U000f03a7\U000f03aa"  # 1 2 3
    "\U000f03ad\U000f03b1\U000f03b3"  # 4 5 6
    "\U000f03b6\U000f03b9\U000f03bc"  # 7 8 9
    "\U000f03a1"  # 0, the tenth
)
# What the branch is indented with. herdr trims a token value before rendering
# it, so an indent of spaces disappears; U+2800 BRAILLE PATTERN BLANK is blank
# and one cell wide but is not whitespace, so it survives the trim.
BLANK: Final = "\u2800"

# A remote URL is <transport><host><separator><path>; the label is that path.
# Matching the host explicitly is what keeps a local path or a file:// URL from
# being read as though some directory above it were the org.
SCP: Final = re.compile(r"^[^/]*@([^/:]+):(.+)$")
URL: Final = re.compile(r"^[a-z][a-z0-9+.-]*://[^/]+/(.+)$", re.I)

# A GIT_DIR inherited from a caller outranks `git -C <dir>`, so every question
# below would be answered for the caller's repository instead of the directory
# being labelled. Anything spawned from a git hook exports one.
ENV: Final = {
    name: value for name, value in os.environ.items() if not name.startswith("GIT_")
}


# --------------------------------------------------------------------------- #
# Payloads — every one of these crosses a trust boundary (herdr's socket, a
# Claude Code hook, a plugin's environment), so each is validated rather than
# dug out of a raw dict. Only the fields this command labels from are modelled;
# the rest of herdr's schema is deliberately ignored so it can grow freely.
# --------------------------------------------------------------------------- #
class Pane(BaseModel):
    """A pane as ``herdr pane get`` and the snapshot report it."""

    pane_id: str
    workspace_id: str = ""
    cwd: str | None = None
    #: The cwd of the process controlling the pane — the agent's when one runs.
    foreground_cwd: str | None = None
    focused: bool = False
    #: The name ``pane rename`` gave the pane; herdr omits the key when none did.
    label: str = ""

    @property
    def dispatched(self) -> bool:
        """Whether a dispatcher named this pane: a sub-agent in its parent's space."""
        return self.label.startswith(ROBOT)


class Workspace(BaseModel):
    """A space as ``herdr workspace get`` and the snapshot report it."""

    workspace_id: str = ""
    focused: bool = False
    #: The space's 1-based position in the sidebar, herdr's own numbering.
    number: int = 0


class Snapshot(BaseModel):
    """The slice of ``herdr api snapshot`` a sweep re-derives every space from."""

    panes: list[Pane] = []
    workspaces: list[Workspace] = []


class HookPayload(BaseModel):
    """The slice of a Claude Code hook payload that names the session's cwd."""

    cwd: str | None = None


class PluginContext(BaseModel):
    """The slice of ``HERDR_PLUGIN_CONTEXT_JSON`` naming the space's directory.

    ``workspace_cwd`` is nullable in herdr's schema.
    """

    workspace_cwd: str | None = None


class _SnapshotGot(BaseModel):
    snapshot: Snapshot


class _WorkspaceGot(BaseModel):
    workspace: Workspace


class _PaneGot(BaseModel):
    pane: Pane


def _run(*args: str) -> str:
    """Return a command's stdout, or "" if it fails, times out, or is missing."""
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            env=ENV,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def slug(url: str) -> str | None:
    """Return a remote URL's host-relative path, or None if it names no host.

    Deliberately keeps every path segment, so a nested GitLab group stays
    "group/subgroup/proj" rather than being truncated to its last two parts.
    """
    url = re.sub(r"\.git$", "", url.strip().rstrip("/"))
    scp = SCP.match(url)
    if scp:
        return scp.group(2)
    hosted = URL.match(url)
    if hosted:
        return hosted.group(1)
    return None


def remote_url(cwd: str) -> str:
    """URL of origin, falling back to whichever remote is configured first."""
    url = _run("git", "-C", cwd, "remote", "get-url", "origin")
    if url:
        return url
    names = _run("git", "-C", cwd, "remote").split()
    return _run("git", "-C", cwd, "remote", "get-url", names[0]) if names else ""


def label_for(cwd: str) -> str:
    """Resolve cwd to "org/repo", else the repo's own name, else NO_REPO."""
    hosted = slug(remote_url(cwd))
    if hosted:
        return hosted
    # A repository with no usable remote still has a name worth showing.
    toplevel = _run("git", "-C", cwd, "rev-parse", "--show-toplevel")
    if toplevel:
        return os.path.basename(toplevel)
    return NO_REPO


def branch_for(cwd: str) -> str:
    """Return the branch checked out at cwd, "" outside a repository.

    A detached HEAD — mid-rebase, mid-bisect, or a checked-out tag — names no
    branch, and the literal "HEAD" git answers with is worth nothing in a
    sidebar, so it degrades to the short commit instead.
    """
    name = _run("git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if name and name != "HEAD":
        return name
    return _run("git", "-C", cwd, "rev-parse", "--short", "HEAD") if name else ""


def in_repo(cwd: str) -> bool:
    """Whether cwd is inside a work tree, guarding the foreground_cwd preference."""
    return _run("git", "-C", cwd, "rev-parse", "--is-inside-work-tree") == "true"


def position_glyph(number: int) -> str:
    """Return the boxed digit for a space's sidebar position, "" past the tenth.

    Positions run out at the end of the number row rather than degrading to a
    "more than this" glyph: the digit is only worth showing where it names a key
    that reaches the space. A zero is herdr declining to answer, since it numbers
    spaces from one.

    The tenth's ``0`` is the one glyph herdr itself does not answer — its indexed
    switching is 1..9 and the workspace picker ignores ``0`` — so config.toml
    binds ``prefix+0`` to focus it instead.
    """
    return BOXES[number - 1] if 1 <= number <= len(BOXES) else ""


def workspace_tokens(cwd: str, focused: bool, number: int) -> list[str]:
    """Token arguments describing cwd, keyed for a focused or unfocused space.

    Args:
        cwd: The directory the space is working in.
        focused: Whether herdr currently has this space focused.
        number: Where the space sits in the sidebar, prefixed to the repo as a
            glyph and matched by an equal indent on the branch.

    Returns:
        The ``--token`` / ``--clear-token`` arguments to hand
        ``workspace report-metadata``. The unused branch key is always cleared,
        because leaving both set would render the branch twice.
    """
    key, other = ("focused_branch", "branch") if focused else ("branch", "focused_branch")
    branch = branch_for(cwd)
    # herdr indents every row of a space entry to the same column, so a prefix
    # on the repo leaves the branch below it starting under the prefix rather
    # than under the repo name. Padding the branch by the prefix's own width is
    # the only lever for that: row layouts have no alignment setting, and the
    # indent herdr applies is not configurable.
    glyph = position_glyph(number)
    prefix = f"{glyph} " if glyph else ""
    return [
        "--token",
        f"repo={prefix}{label_for(cwd)}",
        "--clear-token",
        other,
        *(
            ["--token", f"{key}={BLANK * len(prefix)}{branch}"]
            if branch
            else ["--clear-token", key]
        ),
    ]


def _herdr(herdr: HerdrClient, *args: str) -> None:
    """Fire a herdr CLI call; a failure is one stderr line, never an exception.

    A label is display-only and every caller here is fire-and-forget — a hook or
    a fish ``cd``. Neither a missing binary nor a wedged socket may take one of
    those down or hold it open; the sidebar just keeps its last value.
    """
    with best_effort():
        herdr.run(*args, timeout=TIMEOUT)


def report_space(
    herdr: HerdrClient,
    workspace_id: str,
    cwd: str,
    focused: bool,
    number: int,
) -> None:
    """Label one space with its repo, the branch in play, and its sidebar slot."""
    _herdr(
        herdr,
        "workspace",
        "report-metadata",
        workspace_id,
        "--source",
        SOURCE,
        *workspace_tokens(cwd, focused, number),
    )


def report_pane(herdr: HerdrClient, pane_id: str, cwd: str) -> None:
    """Label one pane with its own branch, for the Agent panel's row."""
    branch = branch_for(cwd)
    _herdr(
        herdr,
        "pane",
        "report-metadata",
        pane_id,
        "--source",
        SOURCE,
        *(["--token", f"branch={branch}"] if branch else ["--clear-token", "branch"]),
    )


def calling_pane() -> str | None:
    """Return the pane this process runs in, or None when that is not knowable.

    A plugin's HERDR_PANE_ID is whichever pane was focused when the event fired,
    which is nobody's branch in particular — so a plugin invocation reports no
    pane token and lets the sweep label each pane from its own cwd instead.
    """
    if os.environ.get("HERDR_PLUGIN_ID"):
        return None
    return os.environ.get("HERDR_PANE_ID")


def snapshot(herdr: HerdrClient) -> Snapshot | None:
    """Return herdr's live snapshot, or None (its failure on stderr) when unusable.

    Every reader here degrades the same way on no server, a failed call, or a
    payload that does not fit, and every caller then leaves the sidebar as it was.
    """
    with best_effort():
        return parse(
            Reply[_SnapshotGot],
            herdr.run("api", "snapshot", timeout=TIMEOUT),
        ).result.snapshot
    return None


def space_info(herdr: HerdrClient, workspace_id: str) -> Workspace:
    """Return what herdr holds under this space id, blank when it cannot say.

    One call answers both things a report needs — which branch key to use, and
    which slot the space sits in — so labelling a space never asks about it
    twice.
    """
    with best_effort():
        return parse(
            Reply[_WorkspaceGot],
            herdr.run("workspace", "get", workspace_id, timeout=TIMEOUT),
        ).result.workspace
    return Workspace()


def get_pane(herdr: HerdrClient, pane_id: str) -> Pane | None:
    """Return what herdr holds under this pane id, or None when it cannot say."""
    with best_effort():
        return parse(
            Reply[_PaneGot],
            herdr.run("pane", "get", pane_id, timeout=TIMEOUT),
        ).result.pane
    return None


def shell_cwd(herdr: HerdrClient, pane_id: str) -> str | None:
    """Return a pane's shell cwd — the directory it keeps once its agent exits."""
    pane: Pane | None = get_pane(herdr, pane_id)
    return pane.cwd if pane else None


def pick_cwd(panes: list[Pane]) -> str | None:
    """Return the directory a space is working in, as its panes report it.

    ``foreground_cwd`` is the cwd of the process controlling the pane, so it is
    the agent's directory whenever one is running and the shell's otherwise. It
    is preferred only when it is in a repository, which keeps a pane that is
    momentarily running something in /tmp from renaming the space.

    The focused pane is asked first: a space split between a shell and an agent
    should follow whichever one the user is looking at. A dispatched pane is never
    asked: it works in a worktree of its own on its parent's behalf.
    """
    own = [pane for pane in panes if not pane.dispatched]
    ordered = sorted(own, key=lambda pane: not pane.focused)
    for pane in ordered:
        for cwd in (pane.foreground_cwd, pane.cwd):
            if cwd and in_repo(cwd):
                return cwd
    cwds = [pane.cwd for pane in ordered if pane.cwd]
    return cwds[0] if cwds else None


def sweep(herdr: HerdrClient) -> None:
    """Re-derive every open space and pane from herdr's snapshot.

    Does nothing beyond one stderr line when no server answers. Each pane is
    labelled from its own directory rather than the space's, so an Agent row
    keeps naming the worktree its agent is in even when the space has settled
    on another pane's.
    """
    live: Snapshot | None = snapshot(herdr)
    if live is None:
        return
    panes: dict[str, list[Pane]] = {}
    for pane in live.panes:
        panes.setdefault(pane.workspace_id, []).append(pane)
        cwd = pane.foreground_cwd or pane.cwd
        if cwd:
            report_pane(herdr, pane.pane_id, cwd)
    for workspace in live.workspaces:
        cwd = pick_cwd(panes.get(workspace.workspace_id, []))
        if cwd:
            report_space(
                herdr,
                workspace.workspace_id,
                cwd,
                workspace.focused,
                workspace.number,
            )


def stdin_payload_cwd() -> str | None:
    """Read the session cwd out of a Claude Code hook payload, or None."""
    try:
        return HookPayload.model_validate_json(sys.stdin.read()).cwd
    except ValidationError:
        return None


def plugin_context_cwd() -> str | None:
    """Read the workspace cwd a herdr plugin hook is handed, or None."""
    try:
        raw = os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}"
        return PluginContext.model_validate_json(raw).workspace_cwd
    except ValidationError:
        return None


def target_cwd(
    herdr: HerdrClient,
    cwd: str | None,
    from_stdin: bool,
    from_pane: bool,
) -> str | None:
    """Return the directory to label, or None when the caller identifies none.

    A plugin hook is told which directory the workspace is in. A pane shell is
    not, but it *is* that directory, so its own cwd is the answer — which is
    what lets the fish hook relabel on cd. The two are told apart by
    HERDR_PLUGIN_ID, since a plugin's cwd is its own root, not the workspace's.
    """
    if cwd:
        return cwd
    if from_stdin:
        return stdin_payload_cwd()
    if from_pane:
        pane_id = os.environ.get("HERDR_PANE_ID")
        return shell_cwd(herdr, pane_id) if pane_id else None
    if os.environ.get("HERDR_PLUGIN_ID"):
        return plugin_context_cwd()
    return os.getcwd()


def selftest() -> None:
    """Check the pure parses, then the git reads against a throwaway repo."""
    import tempfile

    cases = {
        "https://github.com/macintacos/dotfiles.git": "macintacos/dotfiles",
        "https://github.com/macintacos/caret": "macintacos/caret",
        "https://github.com/org/repo/": "org/repo",
        "git@github.com:macintacos/caret.git": "macintacos/caret",
        "ssh://git@github.com/org/sub.repo.git": "org/sub.repo",
        "https://user@bitbucket.org/team/repo.git": "team/repo",
        "git@ghe.corp.internal:team/service.git": "team/service",
        "https://gitlab.com/group/subgroup/proj.git": "group/subgroup/proj",
    }
    for url, want in cases.items():
        assert slug(url) == want, f"{url} -> {slug(url)!r}, want {want!r}"
    # No host to strip, so these fall back to the cwd basename instead.
    for url in ("", "/Users/me/src/bare-repo.git", "file:///srv/git/thing.git"):
        assert slug(url) is None, url
    assert position_glyph(0) == ""
    assert position_glyph(1) == BOXES[0]
    assert position_glyph(10) == BOXES[-1]
    assert position_glyph(11) == ""
    assert pick_cwd([]) is None
    assert pick_cwd([Pane(pane_id="p", cwd="/nowhere")]) == "/nowhere"
    # A dispatched sub-agent never names its parent's space, even while focused.
    sub_agent = Pane(pane_id="d", label="🤖 EXC-1 impl", cwd="/worktree", focused=True)
    assert sub_agent.dispatched
    assert not Pane(pane_id="p", label="renamed").dispatched
    assert pick_cwd([sub_agent, Pane(pane_id="p", cwd="/parent")]) == "/parent"
    assert pick_cwd([sub_agent]) is None
    assert label_for("/") == NO_REPO
    assert branch_for("/") == ""
    assert not in_repo("/")

    # A herdr that cannot run degrades to None, never raises.
    with contextlib.redirect_stderr(io.StringIO()):
        assert snapshot(HerdrClient(Path("/nonexistent/herdr"))) is None
    assert PluginContext.model_validate_json("{}").workspace_cwd is None

    with tempfile.TemporaryDirectory() as repo:
        _run("git", "-C", repo, "init", "-q", "-b", "trunk")
        open(os.path.join(repo, "f"), "w").close()
        _run("git", "-C", repo, "add", "-A")
        _run(
            "git",
            "-C",
            repo,
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "t",
        )
        assert branch_for(repo) == "trunk", branch_for(repo)
        assert in_repo(repo)
        head = _run("git", "-C", repo, "rev-parse", "--short", "HEAD")
        _run("git", "-C", repo, "checkout", "-q", "--detach")
        # Detached: the branch is gone, so the commit stands in for it.
        assert branch_for(repo) == head, branch_for(repo)

        # A focused space bolds its branch by reporting it under the other key,
        # and either way the branch is indented to clear the repo's digit.
        indent = BLANK * len(f"{BOXES[0]} ")
        assert workspace_tokens(repo, False, 1)[3:] == [
            "focused_branch",
            "--token",
            f"branch={indent}{head}",
        ]
        assert workspace_tokens(repo, True, 1)[3:] == [
            "branch",
            "--token",
            f"focused_branch={indent}{head}",
        ]
        # No glyph on the repo, so nothing for the branch to clear.
        assert workspace_tokens(repo, False, 0)[3:] == [
            "focused_branch",
            "--token",
            "branch=" + head,
        ]
    # Outside a repository there is no branch to show under either key.
    assert workspace_tokens("/", False, 1)[3:] == [
        "focused_branch",
        "--clear-token",
        "branch",
    ]
    # The digit leads the repo; past the number row, and for a position herdr
    # could not answer, the repo leads on its own.
    assert workspace_tokens("/", False, 3)[1] == f"repo={BOXES[2]} {NO_REPO}"
    assert workspace_tokens("/", False, 11)[1] == f"repo={NO_REPO}"
    assert workspace_tokens("/", False, 0)[1] == f"repo={NO_REPO}"
    print("ok")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
#: Naming two directory sources at once is a caller bug — five other files in
#: this repo hard-code these flags, so a wrong pairing should say so rather than
#: silently pick one. `--sweep` belongs here too: it means "take no directory,
#: re-derive them all", which is the same question answered differently.
MODE: Final = Group("directory source", validator=validators.LimitedChoice())


def label(
    *,
    cwd: Annotated[str | None, Parameter(group=MODE)] = None,
    from_stdin: Annotated[
        bool,
        Parameter(name="--stdin-cwd", negative=(), group=MODE),
    ] = False,
    from_pane: Annotated[
        bool,
        Parameter(name="--pane-cwd", negative=(), group=MODE),
    ] = False,
    sweep_all: Annotated[
        bool,
        Parameter(name="--sweep", negative=(), group=MODE),
    ] = False,
) -> None:
    """Report a herdr space's org/repo and branch as sidebar tokens.

    Labels whichever space the caller identifies, else sweeps them all.

    Args:
        cwd: Label the space working in this directory (OpenCode plugin).
        from_stdin: Take the directory from a Claude Code hook payload on stdin.
        from_pane: Take the directory from this pane's shell cwd, via herdr.
        sweep_all: Re-derive every open space and pane from herdr's snapshot.
    """
    herdr = HerdrClient(Path(os.environ.get("HERDR_BIN_PATH", "herdr")))
    workspace_id = os.environ.get("HERDR_WORKSPACE_ID")
    target = None if sweep_all else target_cwd(herdr, cwd, from_stdin, from_pane)
    if not (workspace_id and target):
        sweep(herdr)
        return
    pane_id = calling_pane()
    pane: Pane | None = get_pane(herdr, pane_id) if pane_id else None
    if not (pane and pane.dispatched):
        space: Workspace = space_info(herdr, workspace_id)
        report_space(herdr, workspace_id, target, space.focused, space.number)
    if pane_id:
        report_pane(herdr, pane_id, target)
