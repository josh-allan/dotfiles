"""Name herdr panes and tabs after the agent session title in play.

The sibling of ``space_label``, which answers "what is this space working *on*";
this one answers "what is this pane *doing*". Both sweep the same snapshot, and
they are separate plugins because they subscribe to disjoint events and neither
has anything to say about the other's tokens.

Mostly this moves a string herdr already holds. Claude Code writes its
model-generated session title into the terminal title and herdr captures it per
pane as ``terminal_title``; the job is putting it on three surfaces herdr will
not put it on by itself:

* **the pane**, via ``pane report-metadata --title``. That is the field herdr
  paints on a split pane's border, zoomed or not; ``--display-agent`` is a
  different slot and does not appear there. Reported metadata is display-only
  and carries a ``--source``, but it outranks a manual ``pane rename`` on that
  border — so a name a dispatcher wrote there is buried unless a sweep puts it
  back, which is why it is the first name looked for below. A zoomed pane's
  title is prefixed with ``(zoomed)``, because herdr marks zoom nowhere in its
  chrome and a pane filling its tab otherwise looks like a tab that only has
  one.
* **the tab**, via ``tab rename`` — the only lever tabs have. There is no
  ``tab report-metadata``, so this is a real, persistent rename with no source
  and no way to clear it. It is written unconditionally, which is only
  reasonable because ``prompt_new_tab_name = false`` in config.toml stops herdr
  asking for a name nobody wants to type. A tab a dispatcher named — a leading
  ``🤖`` — keeps that name; only its boxed digit is re-applied, and the ``✅``
  ``dispatch complete`` puts on it comes off once its pane is prompted. A tab's
  name is prefixed with the boxed digit that switches to it, so ``switch_tab``'s
  ``prefix+1..9`` can be read off the tab bar instead of counted.
* **the outer terminal's window title**, via the ``client.window_title.set``
  socket call: the focused pane's name, then its cwd in parentheses. herdr
  renders a title of its own from ``ui.window_title``, but only from the tokens
  it defines and none of them is a cwd — so that key is set to ``""`` in
  config.toml and this owns the title instead. It is the one surface here that
  is not per-pane: a single title, repainted from whichever pane has focus.
  A pane with no agent is named by the program in its foreground rather than by
  its ``terminal_title``, which for an idle shell *is* the cwd and would print
  the directory twice.

Five things can name a pane, in that order of precedence: the ``pane rename``
label a dispatcher gave it, marked ``[DONE]`` once that pane's agent has
finished; the issue heading ``track_issue`` pushed with ``--issue-title``; a
title an agent pushed with ``--pane-title``; the pane's ``terminal_title``; and
the opening of the prompt, recorded by ``--prompt-title`` or the ``prompt``
command.
An agent that has not named its session yet leaves its own product name in the
terminal title — ``Claude Code``, ``OpenCode`` — which is why those two strings
count as no title rather than as a name. Claude Code names a session about a
second into a turn, but only a turn that began with prose: one driven entirely
by slash commands is never named at all, unless a hook names it, as
``track_issue`` does a tracked ``/linear-*`` or ``/jira-*`` command. The prompt sits *below*
``terminal_title`` so a real session title displaces it the moment one lands,
leaving nothing to clear.

A tab no dispatcher named shows the title of its **last-focused agent pane**, so
a tab holding two agents names the one you were last looking at rather than
whichever is noisiest.
herdr exposes no per-pane activity timestamp — ``revision`` is a state counter,
not comparable between panes — so focus order is recorded here, in a state file,
and that is the only reason this command keeps state at all. Panes that have
never been focused fall back to whichever is ``working``. A tab with no agent in
it is named from its panes' ``terminal_title`` all the same, which for a shell
is the abbreviated cwd and becomes the program's own title the moment one runs.

Every invocation is a full sweep. herdr emits **no terminal-title event** —
``pane.updated`` is not subscribable and nothing else reports a title change —
so freshness comes from sweeping on events that correlate with one:

* the plugin manifest's ``pane.focused`` (which is also what records recency),
  ``pane.agent_status_changed``, ``pane.created``, ``pane.closed``, and
  ``pane.agent_detected``, plus a startup sweep after a session is restored;
* Claude Code's ``SessionStart`` / ``Stop`` hooks, which are authoritative where
  herdr's agent-state detection reads the screen, and its ``UserPromptSubmit``
  hook, which runs ``prompt``: at prompt time the session title is still the old
  one, so it names the pane from the prompt and then watches for a new one;
* config.toml's ``prefix+z`` binding, which zooms *and* sweeps. Zoom reaches a
  plugin through no event at all: it changes only the tab layout, and
  ``layout.updated`` is not a plugin event — herdr answers a manifest asking for
  one with ``unknown event 'layout.updated'``. Doing the zoom is the only way to
  hear about it;
* ``--pane-title``, for an agent that knows its own name and hands it over
  rather than hoping the TUI put it in the terminal title, as OpenCode's plugin
  does. A pushed title is taken verbatim — the agent chose every character of
  it, glyph included — and outranks ``terminal_title`` for that pane until the
  pane dies; its ``--prompt-title`` sibling carries what the user typed, for the
  window before a summarizer has named anything.
* ``--issue-title``, the ``track_issue`` heading — ``<glyph> <ID> [<notices>]
  <title>`` — the only name a turn driven purely by a slash command ever gets.
  It is stored and cleared like ``--pane-title`` but outranks it, so a
  summarizer's title cannot displace the issue a session is pinned to.

``selftest`` checks the pure ranking and stripping logic; a pytest test runs it
under the project's check.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Final

from cyclopts import App
from pydantic import BaseModel, ValidationError

from herdr_tools.client import HerdrClient, best_effort
from herdr_tools.replies import Reply, parse

SOURCE: Final = "user:pane-label"
#: The socket API method that titles the terminal herdr itself runs in. Alone
#: among the calls here it has no CLI wrapper, so it is spoken to directly.
WINDOW_TITLE: Final = "client.window_title.set"
#: Prefix marking the pane that is currently filling its tab.
ZOOMED: Final = "(zoomed)"
#: Prefix a dispatcher puts on the panes it fans sub-agents out into. It is the
#: only thing telling a name this plugin must not overwrite from one it derived.
ROBOT: Final = "🤖"
#: Marks a dispatched pane whose agent has finished. Derived from the pane's
#: live status on every sweep and never stored, so a pane that goes back to work
#: loses the mark with no bookkeeping left to go stale.
DONE: Final = "[DONE]"
#: Put after a dispatched tab's ``ROBOT`` by ``dispatch complete``. Taken off
#: again when that tab's agent is prompted, since a prompt hands it more work.
COMPLETE: Final = "✅"
#: nf-md-numeric_1_box through _9_box, in order. Their codepoints are not
#: contiguous, so this is a literal rather than arithmetic. It stops at 9
#: because `switch_tab = "prefix+1..9"` is the only reason to number a tab.
BOXES: Final = (
    "\U000f03a4\U000f03a7\U000f03aa"  # 1 2 3
    "\U000f03ad\U000f03b1\U000f03b3"  # 4 5 6
    "\U000f03b6\U000f03b9\U000f03bc"  # 7 8 9
)
#: The terminal titles agents leave up before they have named a session: their
#: own product names, which describe no work and so count as no title at all.
GENERIC: Final = frozenset({"claude code", "opencode"})
#: Prompt openings the harness writes rather than the user. A backgrounded task
#: re-invokes its parent with one of these, and a turn that opens on one is never
#: given a session title — so naming the pane after it would replace a long run's
#: name with zero signal and nothing would ever displace it.
SYNTHETIC: Final = ("<task-notification",)
#: Longest prompt stopgap kept. A tab bar truncates well before this.
PROMPT_CHARS: Final = 40
#: Longest name any surface here shows. A session title is written by an agent
#: that knows nothing of the border it lands on, and one long enough to crowd
#: out the panes beside it says no more than its opening does.
TITLE_CHARS: Final = 50
TIMEOUT: Final = 10

#: herdr's API socket. Present in a pane's environment and, for a plugin
#: command that inherits less, at the path herdr puts it at beside its config.
SOCKET: Final = Path(
    os.environ.get("HERDR_SOCKET_PATH")
    or Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    / "herdr"
    / "herdr.sock",
)

#: Focus order and pushed titles have to outlive the process, because herdr
#: spawns a fresh one per event and exposes no recency of its own.
STATE: Final = (
    Path(os.environ.get("PANE_LABEL_STATE") or "")
    if os.environ.get("PANE_LABEL_STATE")
    else Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    / "herdr"
    / "pane-label.json"
)


class Pane(BaseModel):
    """The slice of a snapshot pane this labels from."""

    pane_id: str
    tab_id: str = ""
    #: The name `pane rename` gave the pane. herdr omits the key entirely when
    #: nothing has renamed it, so the default is what an unnamed pane carries.
    label: str = ""
    #: None for a pane running no agent — a plain shell, or lazygit.
    agent: str | None = None
    agent_status: str = "unknown"
    focused: bool = False
    terminal_title: str | None = None
    #: The pane shell's directory. `foreground_cwd` follows the running program
    #: instead, which for an agent is wherever it happens to have chdir'd to.
    cwd: str = ""


class Process(BaseModel):
    """The slice of a pane's foreground process this names the pane from."""

    pid: int = 0
    #: What the program was invoked as. ``name`` is the process's own title,
    #: which an agent rewrites — Claude Code reports its version there.
    argv0: str = ""


class ProcessInfo(BaseModel):
    """A pane's foreground processes, and which of them leads the group."""

    foreground_process_group_id: int = 0
    foreground_processes: list[Process] = []


class HookPayload(BaseModel):
    """The slice of Claude Code's ``UserPromptSubmit`` payload naming the turn."""

    prompt: str = ""


class Tab(BaseModel):
    """A tab and the label it currently carries, so unchanged ones are skipped."""

    tab_id: str
    workspace_id: str = ""
    label: str = ""


class Layout(BaseModel):
    """A tab's pane arrangement, for the one thing here that reads from it: zoom."""

    focused_pane_id: str = ""
    zoomed: bool = False


class Snapshot(BaseModel):
    """The slice of ``herdr api snapshot`` a sweep re-derives everything from."""

    panes: list[Pane] = []
    tabs: list[Tab] = []
    layouts: list[Layout] = []


class State(BaseModel):
    """What a sweep cannot re-derive from herdr and has to remember itself."""

    #: Pane ids in focus order, most recently focused first.
    mru: list[str] = []
    #: Titles handed over by an agent that does not publish one to its terminal.
    pushed: dict[str, str] = {}
    #: Issue headings, which outrank ``pushed``.
    issued: dict[str, str] = {}
    #: Prompt openings, for a pane whose agent has not named its session.
    prompted: dict[str, str] = {}


def strip_glyph(title: str) -> str:
    """Drop the animated state glyph agents prefix their terminal title with.

    Claude cycles ``✳``/``◐``/``◑`` there as a spinner, so leaving it in would
    repaint the border on every animation frame — and herdr's own
    ``terminal_title_stripped`` only removes the static ``✳``, leaving the
    spinner frames on precisely the panes that are busy.

    Only *non-ASCII* leading symbols are stripped, which is what keeps a shell's
    ``~/.l/s/c/trunk`` intact: ``~`` is a symbol too, but an ASCII one.
    """
    index = 0
    while index < len(title) and (
        title[index].isspace() or (ord(title[index]) > 127 and not title[index].isalnum())
    ):
        index += 1
    return title[index:].strip()


def zoomed_ids(layouts: list[Layout]) -> set[str]:
    """Return the panes currently zoomed to fill their tab.

    A zoomed tab's ``focused_pane_id`` *is* its zoomed pane: herdr focuses what
    it zooms and holds focus there until the zoom is released. The layout is the
    only place zoom is reported at all — a pane carries no flag of its own.
    """
    return {layout.focused_pane_id for layout in layouts if layout.zoomed}


def _herdr(herdr: HerdrClient, *args: str) -> None:
    """Fire a herdr CLI call; a failure is one stderr line, never an exception.

    A label is display-only and every caller is fire-and-forget — a plugin event
    or an agent hook. Neither a missing binary nor a wedged socket may take one
    of those down; the UI just keeps its last value.
    """
    with best_effort():
        herdr.run(*args, timeout=TIMEOUT)


def _api(method: str, params: dict[str, object]) -> None:
    """Fire one socket API request, ignoring whether it lands.

    The reply is read only so the server is not writing into a hung-up socket;
    nothing here has any use for it. Fire-and-forget for the same reason
    ``_herdr`` is — a title is display-only and may take no caller down.
    """
    request = json.dumps({"id": SOURCE, "method": method, "params": params}) + "\n"
    with contextlib.suppress(OSError), socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(TIMEOUT)
        sock.connect(str(SOCKET))
        sock.sendall(request.encode())
        sock.recv(1)


class _SnapshotGot(BaseModel):
    snapshot: Snapshot


class _ProcessInfoGot(BaseModel):
    process_info: ProcessInfo


def snapshot(herdr: HerdrClient) -> Snapshot | None:
    """Return herdr's live snapshot, or None (its failure on stderr) when unusable."""
    with best_effort():
        return parse(
            Reply[_SnapshotGot],
            herdr.run("api", "snapshot", timeout=TIMEOUT),
        ).result.snapshot
    return None


def process_name(info: ProcessInfo) -> str:
    """Return the program running in a pane's foreground, or "" if none is.

    The pane's own shell leads the group when it is sitting at a prompt, which
    is what makes an idle pane read ``fish`` rather than read as empty.
    """
    leader = next(
        (
            p
            for p in info.foreground_processes
            if p.pid == info.foreground_process_group_id
        ),
        None,
    )
    return Path(leader.argv0).name if leader else ""


def foreground(herdr: HerdrClient, pane_id: str) -> str:
    """Return one pane's foreground program, or "" when it cannot be read."""
    with best_effort():
        return process_name(
            parse(
                Reply[_ProcessInfoGot],
                herdr.run("pane", "process-info", "--pane", pane_id, timeout=TIMEOUT),
            ).result.process_info,
        )
    return ""


def load_state() -> State:
    """Read the recency file, degrading to an empty state on anything unreadable."""
    try:
        return State.model_validate_json(STATE.read_text())
    except (OSError, ValidationError):
        return State()


def save_state(state: State) -> None:
    """Write the recency file atomically, so a concurrent sweep never reads a partial one.

    ponytail: last writer wins on the read-modify-write itself — two events
    firing at once can drop one focus bump, which the next focus change
    corrects. Lock it only if labels are ever seen sticking to the wrong pane.
    """
    with contextlib.suppress(OSError):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=STATE.parent, delete=False) as handle:
            handle.write(state.model_dump_json())
            temp = Path(handle.name)
        temp.replace(STATE)


def from_prompt(prompt: str) -> str:
    """Return a tab-sized name for a prompt: its opening, on one line.

    A synthetic prompt names nothing, so it returns "" and the pane keeps
    whatever it was already called.
    """
    text = " ".join(prompt.split())
    if text.startswith(SYNTHETIC):
        return ""
    if len(text) <= PROMPT_CHARS:
        return text
    return text[:PROMPT_CHARS].rsplit(" ", 1)[0] + "…"


def elide(title: str) -> str:
    """Return ``title`` capped at ``TITLE_CHARS``, ellipsis included in the count."""
    return title if len(title) <= TITLE_CHARS else title[: TITLE_CHARS - 1].rstrip() + "…"


def dispatched_name(label: str, agent_status: str) -> str:
    """Return the name a dispatcher gave a pane, marked if its agent has finished.

    A fan-out names each sub-agent's pane with ``pane rename``, and that label is
    the only thing telling three otherwise identical panes apart — so it has to
    last the pane's whole life rather than until the agent publishes a title.

    Args:
        label: The pane's ``pane rename`` label. Anything not prefixed with
            ``ROBOT`` was named by something that is not a dispatcher, and is
            left to whatever the sweep derives.
        agent_status: The pane's live status.

    Returns:
        The label, ``DONE`` inserted after the glyph when the agent is finished,
        or "" when no dispatcher named this pane.
    """
    if not label.startswith(ROBOT):
        return ""
    if agent_status != "done":
        return label
    return f"{ROBOT} {DONE} {label.removeprefix(ROBOT).strip()}"


def dispatched_tab_name(label: str) -> str:
    """Return a tab's dispatcher-given name without its boxed digit, else "".

    The strip is the exact inverse of ``numbered``'s ``"{digit} {label}"``, the
    only thing that ever writes a digit; carrying the old one through would give
    a re-numbered tab two.

    A name carrying ``DONE`` is disowned. ``tab rename`` is persistent, so a
    marked name that reached a tab would otherwise be read back here as the
    dispatcher's own and pinned there, outliving both the status that earned it
    and the pane it described.
    """
    name = unnumbered(label)
    return name if name.startswith(ROBOT) and DONE not in name else ""


def derived_title(pane: Pane, state: State) -> str:
    """Return what a sweep works out itself: a push, the terminal title, else the prompt.

    Whichever wins is elided, including a pushed one: an agent chose every
    character of that, but not how many of them fit on a border.
    """
    pushed = state.issued.get(pane.pane_id) or state.pushed.get(pane.pane_id)
    if pushed:
        return elide(pushed)
    title = strip_glyph(pane.terminal_title or "")
    if title and title.casefold() not in GENERIC:
        return elide(title)
    return elide(state.prompted.get(pane.pane_id) or title)


def title_of(pane: Pane, state: State) -> str:
    """Return a pane's name: a dispatcher's label first, else what a sweep derives."""
    dispatched = dispatched_name(pane.label, pane.agent_status)
    return elide(dispatched) if dispatched else derived_title(pane, state)


def tab_name(tab: Tab, pane: Pane, state: State) -> str:
    """Return what a tab should be called, before its boxed digit goes on.

    A tab is dispatcher-named only by ``tab create --label``. It takes the
    *derived* name of the pane it shows, never that pane's own dispatcher label:
    ``tab rename`` is persistent, so an inherited label would come straight back
    through ``dispatched_tab_name`` on the next sweep and pin the tab to a name
    borrowed from a pane that may since have gone.

    A derived name opening on ``ROBOT`` is refused for that same reason — a
    pushed or prompted title is taken verbatim, glyph and all, so an ordinary
    pane can hold one. Refusing leaves the tab its current name rather than
    rewriting it, which is what lets the tab follow that pane again as soon as
    its title no longer opens on the marker.
    """
    own = dispatched_tab_name(tab.label)
    if own:
        return own
    derived = derived_title(pane, state)
    return "" if derived.startswith(ROBOT) else derived


def label_for(pane: Pane, state: State, zoomed: set[str]) -> str:
    """Return what a pane's border should read: its name, its zoom marker, or both.

    Only agent panes get a *name*: a shell's title is its cwd, which would turn
    every ``cd`` into a repaint of a border nobody asked to name. The zoom marker
    is not a name and stands on its own, so a zoomed shell or lazygit pane still
    gets one.
    """
    title = title_of(pane, state) if pane.agent else ""
    return f"{ZOOMED} {title}".strip() if pane.pane_id in zoomed else title


def window_title(pane: Pane, state: State, home: str, program: str) -> str:
    """Return what the outer terminal should be titled for the focused pane.

    Unlike a border label this names shells too: the window title is the only
    place a pane running no agent is described at all, and its cwd is the whole
    reason to look there.

    Args:
        pane: The focused pane.
        state: Pushed and prompt titles, as everywhere else here.
        home: The home directory, collapsed to ``~`` the way a shell writes it.
        program: The pane's foreground program, which names it when no agent
            does. Ignored for an agent pane, whose session title is the better
            name and whose foreground program is only ever the agent.
    """
    cwd = pane.cwd
    if cwd == home or cwd.startswith(f"{home}/"):
        cwd = f"~{cwd[len(home) :]}"
    title = title_of(pane, state) if pane.agent else program
    return f"{title} ({cwd})" if title and cwd else title or cwd


def numbered(label: str, position: int) -> str:
    """Prefix a tab's name with the boxed digit that switches to it.

    ``position`` is the tab's place in its own workspace, counted from zero —
    the snapshot's ``number`` is a monotonic id that passes 9 within a session
    and never matches the key you press. Tabs past the ninth keep a bare name,
    because there is no tenth key to advertise.
    """
    return f"{BOXES[position]} {label}" if position < len(BOXES) else label


def unnumbered(label: str) -> str:
    """Strip the boxed digit ``numbered`` puts on a tab's name, if it has one."""
    return label[2:] if label.startswith(tuple(BOXES)) else label


def rank(pane: Pane, state: State) -> tuple[int, bool, str]:
    """Sort key putting the last-focused pane first.

    Focus is the whole ordering; ``working`` only breaks ties among panes that
    have never been focused, which is what stops an agent started in a
    background tab from claiming that tab's name. The pane id is a final
    tiebreak so a sweep is deterministic.
    """
    seen = state.mru.index(pane.pane_id) if pane.pane_id in state.mru else len(state.mru)
    return (seen, pane.agent_status != "working", pane.pane_id)


def pick(panes: list[Pane], state: State) -> Pane | None:
    """Return the pane a tab is named from: its last-focused agent, else any pane."""
    agents = [pane for pane in panes if pane.agent]
    pool = agents or panes
    return min(pool, key=lambda pane: rank(pane, state)) if pool else None


def sweep(
    herdr: HerdrClient,
    push: tuple[str, str] | None = None,
    prompted: tuple[str, str] | None = None,
    issued: tuple[str, str] | None = None,
) -> None:
    """Re-derive every pane title and tab name from herdr's snapshot.

    Does nothing beyond one stderr line when no server answers.

    Args:
        herdr: The herdr CLI the snapshot, process-info and metadata calls go through.
        push: A ``(pane_id, title)`` an agent handed over directly, recorded
            before the pass so it wins for that pane.
        prompted: A ``(pane_id, title)`` taken from the prompt, recorded the
            same way but outranked by any title the agent publishes itself.
        issued: A ``(pane_id, heading)`` from ``track_issue``, recorded the
            same way and outranking ``push``.
    """
    live = snapshot(herdr)
    if live is None:
        return

    state = load_state()
    if push is not None:
        state.pushed[push[0]] = push[1]
    if prompted is not None:
        state.prompted[prompted[0]] = prompted[1]
    if issued is not None:
        state.issued[issued[0]] = issued[1]
    for pane in live.panes:
        if pane.focused and state.mru[:1] != [pane.pane_id]:
            state.mru = [pane.pane_id, *(p for p in state.mru if p != pane.pane_id)]
    # Panes die; their recency and their titles must not outlive them, or the
    # state file grows forever and a recycled id inherits a stranger's name.
    ids = {pane.pane_id for pane in live.panes}
    state.mru = [pane_id for pane_id in state.mru if pane_id in ids]
    state.pushed = {pane_id: t for pane_id, t in state.pushed.items() if pane_id in ids}
    state.issued = {pane_id: t for pane_id, t in state.issued.items() if pane_id in ids}
    state.prompted = {
        pane_id: t for pane_id, t in state.prompted.items() if pane_id in ids
    }
    save_state(state)

    # ponytail: nothing reports a cwd change, so a shell that `cd`s keeps the
    # old window title until whatever event triggers the next sweep. Watch the
    # way the `watch` command does if that lag ever shows.
    focused = next((pane for pane in live.panes if pane.focused), None)
    if focused is not None:
        program = "" if focused.agent else foreground(herdr, focused.pane_id)
        _api(
            WINDOW_TITLE,
            {"title": window_title(focused, state, str(Path.home()), program)},
        )

    zoomed = zoomed_ids(live.layouts)
    for pane in live.panes:
        title = label_for(pane, state, zoomed)
        _herdr(
            herdr,
            "pane",
            "report-metadata",
            pane.pane_id,
            "--source",
            SOURCE,
            *(["--title", title] if title else ["--clear-title"]),
        )

    prompted_tab = (
        {p.pane_id: p.tab_id for p in live.panes}.get(prompted[0]) if prompted else None
    )
    # Tabs arrive grouped in their workspace's bar order, which is the order
    # `prefix+1..9` counts in. Closing a tab renumbers every tab after it, and
    # that is only correct here because closing one also fires `pane.closed`.
    positions: dict[str, int] = {}
    for tab in live.tabs:
        position = positions.get(tab.workspace_id, 0)
        positions[tab.workspace_id] = position + 1
        pane = pick([p for p in live.panes if p.tab_id == tab.tab_id], state)
        if pane is None:
            continue
        name = tab_name(tab, pane, state)
        if tab.tab_id == prompted_tab:
            name = name.replace(f"{ROBOT} {COMPLETE}", ROBOT, 1)
        label = numbered(name, position)
        # `tab rename` is persistent and unsourced, so it is worth writing only
        # when the name actually moved.
        if label and label != tab.label:
            _herdr(herdr, "tab", "rename", tab.tab_id, label)


def terminal_title(herdr: HerdrClient, pane_id: str) -> str:
    """Return one pane's terminal title, stripped, or "" if it cannot be read."""
    live = snapshot(herdr)
    pane = next((p for p in live.panes if p.pane_id == pane_id), None) if live else None
    return strip_glyph(pane.terminal_title or "") if pane else ""


def selftest() -> None:
    """Check the stripping and the ranking — the only logic here that can be wrong."""
    assert (
        strip_glyph("✳ space-label.py uv script refactor")
        == "space-label.py uv script refactor"
    )
    assert (
        strip_glyph("◐ Herdr plugin for pane renaming")
        == "Herdr plugin for pane renaming"
    )
    assert strip_glyph("◑  spaced  ") == "spaced"
    # ASCII symbols survive: a shell's title starts with one and is not a glyph.
    assert strip_glyph("~/.l/s/c/trunk") == "~/.l/s/c/trunk"
    assert strip_glyph("[wip] thing") == "[wip] thing"
    # A non-ASCII *letter* is a title, not a glyph.
    assert strip_glyph("Éclair refactor") == "Éclair refactor"
    assert strip_glyph("✳") == ""
    assert strip_glyph("") == ""

    idle = Pane(pane_id="p1", tab_id="t1", agent="claude", agent_status="idle")
    busy = Pane(pane_id="p2", tab_id="t1", agent="claude", agent_status="working")
    shell = Pane(pane_id="p3", tab_id="t1", terminal_title="~/src")

    # Never focused: working wins the tiebreak.
    assert pick([idle, busy], State()) is busy
    # Focused: attention beats busyness, which is the whole point of Q6.1.
    assert pick([idle, busy], State(mru=["p1"])) is idle
    # An agent always outranks a shell sharing its tab...
    assert pick([shell, idle], State(mru=["p3"])) is idle
    # ...but a tab with no agent still names itself from the pane it has.
    assert pick([shell], State()) is shell
    assert pick([], State()) is None

    # A pushed title outranks the terminal title; stripping applies to neither
    # again, since the pusher strips before handing it over.
    assert title_of(shell, State()) == "~/src"
    assert (
        title_of(shell, State(pushed={"p3": "Refactor the labeller"}))
        == "Refactor the labeller"
    )
    assert title_of(Pane(pane_id="p4", terminal_title="◐ x"), State()) == "x"

    # An agent that has not named its session leaves its own product name up:
    # the prompt displaces that, and a real session title displaces the prompt.
    unnamed = Pane(pane_id="p5", agent="claude", terminal_title="✳ Claude Code")
    named = Pane(pane_id="p5", agent="claude", terminal_title="✳ Refactor the labeller")
    prompted = State(prompted={"p5": "/linear-exec EXC-1132"})
    assert title_of(unnamed, State()) == "Claude Code"
    assert title_of(unnamed, prompted) == "/linear-exec EXC-1132"
    assert title_of(named, prompted) == "Refactor the labeller"
    assert (
        title_of(unnamed, State(pushed={"p5": "Pushed"}, prompted={"p5": "Typed"}))
        == "Pushed"
    )
    # Both agents leave a product name up, and neither of them is a name.
    opencode = Pane(pane_id="p5", agent="opencode", terminal_title="OpenCode")
    assert title_of(opencode, prompted) == "/linear-exec EXC-1132"

    assert from_prompt("/linear-exec EXC-1132") == "/linear-exec EXC-1132"
    assert from_prompt("  fix\n the   thing  ") == "fix the thing"
    assert from_prompt("") == ""
    # A backgrounded task's wake-up names nothing; the pane keeps its run's name.
    assert (
        from_prompt("<task-notification>Agent finder-api completed</task-notification>")
        == ""
    )
    # Too long: cut at a word boundary, or mid-word when there is none.
    wordy = "double check that the tab title is not updated when there is one pane"
    assert from_prompt(wordy) == "double check that the tab title is not…"
    assert from_prompt("x" * 60) == "x" * 40 + "…"

    # A name too long for a border is cut to fifty cells, ellipsis included.
    assert elide("x" * 50) == "x" * 50
    assert elide("x" * 51) == "x" * 49 + "…"
    assert elide("") == ""
    # The cut lands where it lands, but never leaves a space before the mark.
    assert elide("x" * 49 + " word") == "x" * 49 + "…"
    long_push = State(pushed={"p1": "y" * 80})
    assert title_of(idle, long_push) == "y" * 49 + "…"
    assert label_for(idle, long_push, {"p1"}) == "(zoomed) " + "y" * 49 + "…"
    assert (
        title_of(Pane(pane_id="pB", terminal_title="✳ " + "z" * 80), State())
        == "z" * 49 + "…"
    )

    # A dispatcher's `pane rename` label outranks everything a sweep derives:
    # the fan-out named that pane, and the name has to last the pane's whole life.
    dispatched = Pane(pane_id="pC", agent="claude", label="🤖 EXC-1154 critique-test")
    assert title_of(dispatched, State()) == "🤖 EXC-1154 critique-test"
    named_too = dispatched.model_copy(update={"terminal_title": "✳ Refactor"})
    assert title_of(named_too, State()) == "🤖 EXC-1154 critique-test"
    assert (
        title_of(dispatched, State(pushed={"pC": "Pushed"}))
        == "🤖 EXC-1154 critique-test"
    )
    # An issue heading outranks a pushed summarizer title, but not a dispatcher.
    both = State(pushed={"p3": "Summarized"}, issued={"p3": "🧭 EXC-42 [🌱 #43] Title"})
    assert title_of(shell, both) == "🧭 EXC-42 [🌱 #43] Title"
    assert (
        title_of(shell, State(pushed={"p3": "Summarized"}, issued={"p3": ""}))
        == "Summarized"
    )
    assert (
        title_of(dispatched, State(issued={"pC": "🧭 EXC-42"}))
        == "🤖 EXC-1154 critique-test"
    )

    # The marker is re-derived every sweep, so a pane that goes back to work
    # loses it.
    for status in ("working", "idle", "blocked", "unknown"):
        assert (
            dispatched_name("🤖 EXC-1154 critique-test", status)
            == "🤖 EXC-1154 critique-test"
        )
    assert (
        dispatched_name("🤖 EXC-1154 critique-test", "done")
        == "🤖 [DONE] EXC-1154 critique-test"
    )
    # A pane the dispatcher never named is not one of ours, and is never marked.
    assert dispatched_name("scratch", "done") == ""
    assert dispatched_name("", "done") == ""

    # The format fits a border by construction: the marker, an issue id, and the
    # longest task slug the format allows land on TITLE_CHARS codepoints, uncut.
    # `🤖` is double-width, so that is one terminal cell more — the one name here
    # that keeps a wide glyph rather than having it stripped.
    assert elide("🤖 [DONE] EXC-1154 critique-test") == "🤖 [DONE] EXC-1154 critique-test"
    longest = "🤖 [DONE] EXC-1154 " + "a" * 32
    assert len(longest) == TITLE_CHARS
    assert elide(longest) == longest

    # A tab the dispatcher named keeps that name; only its digit is re-applied.
    assert dispatched_tab_name("🤖 exec/EXC-1154") == "🤖 exec/EXC-1154"
    assert dispatched_tab_name("\U000f03a4 🤖 exec/EXC-1154") == "🤖 exec/EXC-1154"
    assert dispatched_tab_name("\U000f03a4 Refactor the labeller") == ""
    assert dispatched_tab_name("") == ""
    # A marked name is one this plugin wrote to a tab itself, never a dispatcher's:
    # taken back as a given name it would freeze there, outliving both the status
    # that earned it and the pane it came from.
    assert dispatched_tab_name("🤖 [DONE] EXC-1154 critique-test") == ""
    assert dispatched_tab_name("\U000f03a4 🤖 [DONE] EXC-1154 critique-test") == ""

    # Only `tab create --label` names a tab. A tab must never inherit the label of
    # a pane inside it: `dispatched_tab_name` would read that straight back off the
    # tab next sweep and pin it there, outliving the pane it was borrowed from.
    own = Tab(tab_id="t1", label="🤖 exec/EXC-1154")
    plain = Tab(tab_id="t1", label="\U000f03a4 Refactor the labeller")
    assert tab_name(own, dispatched, State()) == "🤖 exec/EXC-1154"
    assert tab_name(plain, dispatched, State()) == ""
    assert tab_name(plain, named_too, State()) == "Refactor"

    # A pushed or prompted title is taken verbatim, glyph and all, so an ordinary
    # pane can carry one opening on the marker. It names no tab either: written
    # there it would read back as a dispatcher's and pin the tab for good, and
    # `strip_glyph` guards only the terminal-title rank below it.
    plain_pane = Pane(pane_id="p1", agent="claude")
    assert tab_name(plain, plain_pane, State(pushed={"p1": "🤖 not dispatched"})) == ""
    assert tab_name(plain, plain_pane, State(prompted={"p1": "🤖 do the thing"})) == ""
    # Declining rather than rewriting is what lets the tab follow that pane again
    # the moment its title no longer opens on the marker.
    assert tab_name(plain, plain_pane, State(pushed={"p1": "Refactor"})) == "Refactor"

    # A zoomed pane says so; an unnamed one says only that.
    assert (
        label_for(idle, State(pushed={"p1": "Refactor"}), {"p1"}) == "(zoomed) Refactor"
    )
    assert label_for(idle, State(pushed={"p1": "Refactor"}), set()) == "Refactor"
    assert label_for(shell, State(), {"p3"}) == "(zoomed)"
    assert label_for(shell, State(), set()) == ""

    # The window title names shells as well as agents, and always ends in a cwd.
    home = "/Users/x"
    working = Pane(
        pane_id="p6",
        agent="claude",
        terminal_title="✳ Refactor",
        cwd="/Users/x/src",
    )
    assert window_title(working, State(), home, "") == "Refactor (~/src)"
    # A shell is named by what it is running, not by its terminal title — which
    # at a prompt is the cwd, and would print the directory twice.
    shell_pane = Pane(pane_id="p7", terminal_title="~/.l/s/c/trunk", cwd="/Users/x/src")
    assert window_title(shell_pane, State(), home, "fish") == "fish (~/src)"
    assert window_title(shell_pane, State(), home, "nvim") == "nvim (~/src)"
    # Unreadable process info leaves the cwd standing on its own.
    assert window_title(shell_pane, State(), home, "") == "~/src"
    assert window_title(Pane(pane_id="p8", cwd=home), State(), home, "fish") == "fish (~)"
    # A path merely starting with the home directory's characters is not under it.
    assert (
        window_title(Pane(pane_id="p9", cwd="/Users/xyz"), State(), home, "")
        == "/Users/xyz"
    )
    # A pane with neither is nothing to title with, not "()".
    assert window_title(Pane(pane_id="pA"), State(), home, "") == ""

    # The group leader is the program in the foreground; a shell at a prompt
    # leads its own group, which is what makes an idle pane read "fish".
    idle = ProcessInfo(
        foreground_process_group_id=1,
        foreground_processes=[Process(pid=1, argv0="fish")],
    )
    running = ProcessInfo(
        foreground_process_group_id=2,
        foreground_processes=[
            Process(pid=1, argv0="fish"),
            Process(pid=2, argv0="/bin/nvim"),
        ],
    )
    assert process_name(idle) == "fish"
    assert process_name(running) == "nvim"
    assert process_name(ProcessInfo()) == ""

    assert numbered("Refactor", 0) == "\U000f03a4 Refactor"
    assert numbered("Refactor", 8) == "\U000f03bc Refactor"
    # A tenth tab has no key to advertise, so it is left alone.
    assert numbered("Refactor", 9) == "Refactor"

    assert zoomed_ids([Layout(focused_pane_id="p1", zoomed=True), Layout()]) == {"p1"}
    assert zoomed_ids([Layout(focused_pane_id="p1")]) == set()
    assert zoomed_ids([]) == set()

    # A payload that is not the shape we asked for degrades to an empty state.
    assert State.model_validate_json("{}").mru == []
    print("ok")


def _client() -> HerdrClient:
    return HerdrClient(Path(os.environ.get("HERDR_BIN_PATH", "herdr")))


# name must match cli.py's registration under `label`.
app = App(name="pane", version_flags=[])


@app.default
def label(
    *,
    pane_title: str | None = None,
    prompt_title: str | None = None,
    issue_title: str | None = None,
) -> None:
    """Sweep every pane and tab.

    Args:
        pane_title: Title for *this* pane, verbatim, for an agent that
            publishes one directly instead of through its terminal title.
        prompt_title: What the user just asked for, kept until that agent
            has a session title of its own.
        issue_title: The issue heading for *this* pane, verbatim; outranks
            ``pane_title``.
    """
    push = prompted = issued = None
    pane_id = os.environ.get("HERDR_PANE_ID")
    if pane_title is not None and pane_id:
        push = (pane_id, pane_title.strip())
    if prompt_title is not None and pane_id:
        prompted = (pane_id, from_prompt(prompt_title))
    if issue_title is not None and pane_id:
        issued = (pane_id, issue_title.strip())
    sweep(_client(), push, prompted, issued)


@app.command
def watch(*, seconds: float = 20.0, interval: float = 1.0) -> None:
    """Sweep as soon as this pane's terminal title changes.

    Claude Code names a session about a second into a turn, but the earliest
    sweep anything can trigger after that is its ``Stop`` hook at the *end*
    of the turn — so a pane spends the whole turn showing the name it had
    before the prompt. Watching from the prompt closes that window without
    putting a sweep on every tool call.

    Args:
        seconds: How long to watch before giving up. ``Stop`` still sweeps.
        interval: Seconds between snapshots.
    """
    pane_id = os.environ.get("HERDR_PANE_ID")
    if not pane_id:
        return
    herdr: HerdrClient = _client()
    before = terminal_title(herdr, pane_id)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(interval)
        if terminal_title(herdr, pane_id) != before:
            sweep(herdr)
            return


@app.command
def prompt(*, seconds: float = 20.0, interval: float = 1.0) -> None:
    """Name this pane from the prompt on stdin, then watch for a real title.

    Claude Code's ``UserPromptSubmit`` payload carries the prompt, which is
    the only thing that says what a turn is about before the agent has named
    the session — and, for a session driven entirely by slash commands, the
    only thing that ever will, bar a hook-set title.

    Args:
        seconds: How long to watch afterwards. ``Stop`` still sweeps.
        interval: Seconds between snapshots.
    """
    pane_id = os.environ.get("HERDR_PANE_ID")
    try:
        title = from_prompt(HookPayload.model_validate_json(sys.stdin.read()).prompt)
    except (OSError, ValidationError):
        title = ""
    if pane_id and title:
        sweep(_client(), prompted=(pane_id, title))
    watch(seconds=seconds, interval=interval)
