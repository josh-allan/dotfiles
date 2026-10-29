"""Confirm a close that would throw work away, and only then.

herdr's own guard, confirm_close, asks before every workspace close whether or
not there is anything to lose, and a prompt that fires when the answer cannot
matter is one you learn to dismiss unread — including the time it mattered.

A plugin action runs headless, so it cannot ask anything; a popup holds a real
tty and receives every keystroke. The action decides, the popup asks, and the
target travels between them in CLOSE_CONFIRM_JSON rather than being re-read from
focus, so a focus change while the prompt is up cannot redirect the close.
"""

import contextlib
import json
import os
import re
import select
import sys
import termios
import tty
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Final, Self

from herdr_tools.client import HerdrClient, HerdrError

# Four names and a tail fit the border; more truncate mid-word.
MAX_NAMES: Final = 4
# What is left of the popup's top edge once the border's corners have their say.
MAX_TITLE: Final = 52

# Catppuccin mantle, not base: herdr paints the popup's chrome in mantle and the
# pane inherits none of it, so anything else leaves a seam at the border.
BG: Final = "\x1b[48;2;24;24;37m"
TEXT: Final = "\x1b[38;2;205;214;244m"
SOFT: Final = "\x1b[38;2;166;173;200m"
DIM: Final = "\x1b[38;2;127;132;156m"
BLUE: Final = "\x1b[38;2;137;180;250m"
BOLD: Final = "\x1b[1m"
ITALIC: Final = "\x1b[3m"
PICKED_BG: Final = "\x1b[48;2;137;180;250m"
PICKED_FG: Final = "\x1b[38;2;17;17;27m"
REST_BG: Final = "\x1b[48;2;49;50;68m"

ICONS: Final = {
    "pane": "\U000f018d",  # md-console
    "tab": "\U000f04e9",  # md-tab
    "workspace": "\U000f0570",  # md-view_grid
}
HINTS: Final = (
    ("\U000f0312", "switch"),  # md-keyboard_tab
    ("\U000f0311", "confirm"),  # md-keyboard_return
    ("\U000f12b7", "cancel"),  # md-keyboard_esc
)

# Matches the inset herdr gives its own panel rows.
MARGIN: Final = 2


@dataclass(frozen=True, slots=True)
class Prompt:
    """The question the action decided is owed, as the popup receives it.

    The shape is built on one side of a process boundary and read on the other,
    so the field list is the only place the two agree.

    Attributes:
        target: The level that actually closes, after any escalation.
        pressed: The level the pressed key named, which may be a smaller one.
        target_id: herdr's id for the thing `target` closes.
        location: Space and tab labels, for the context line under the question.
        running: What a yes would kill, one name per busy pane.
    """

    target: str
    pressed: str
    target_id: str
    location: str
    running: list[str]

    def to_json(self) -> str:
        """Render for the CLOSE_CONFIRM_JSON the popup is launched with."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, payload: str) -> Self:
        """Read one back out of that variable."""
        return cls(**json.loads(payload))


def busy_label(info: dict[str, Any]) -> str | None:
    """Name what occupies a pane, or None when it sits at its shell prompt.

    A shell leads its own process group only while nothing runs in front of it,
    so the comparison decides busy and the name is read for wording alone.
    Either id missing counts as idle: a close the user asked for should not be
    blocked by a pane herdr cannot introspect.
    """
    shell, group = info.get("shell_pid"), info.get("foreground_process_group_id")
    if shell is None or group is None or shell == group:
        return None
    processes = info.get("foreground_processes") or []
    leader = next((p for p in processes if p.get("pid") == group), None)
    front = leader or (processes[0] if processes else {})
    # argv0 over name: an agent that rewrites its own title reports `name` as a
    # version string, and argv0 still says "claude". Wrappers put a whole command
    # line in argv0 ("npm exec ..."), hence the first word only.
    argv0 = (front.get("argv0") or "").strip()
    return PurePosixPath(argv0.split()[0]).name if argv0 else (front.get("name") or "?")


def decide(pressed: str, pane_count: int, tab_count: int, busy: bool) -> tuple[str, bool]:
    """Return what actually gets closed, and whether to ask first.

    A close escalates to what herdr would really take — the last pane in a tab is
    the tab, the last tab in a space is the space — because that reach is the
    surprise. Only reaching the space asks unconditionally; anything smaller is
    governed by busy-ness alone. An explicit workspace close escalates nowhere:
    naming the space is already the intent the last-tab case is missing.
    """
    target = pressed
    if target == "pane" and pane_count <= 1:
        target = "tab"
    if target == "tab" and tab_count <= 1:
        return "workspace", True
    return target, busy


# A workspace is a "space" throughout this config's user-facing text.
LEVELS: Final = {"pane": "pane", "tab": "tab", "workspace": "space"}


def headline(target: str, pressed: str) -> str:
    """Ask the question in terms of what a yes actually destroys."""
    if target == pressed:
        return f"Close this {LEVELS[target]}?"
    return f"Close the last {LEVELS[pressed]}, and the {LEVELS[target]} with it?"


def clip(text: str, width: int) -> str:
    """Trim to width, marking the cut so a truncated name never reads as whole."""
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def summarise(names: list[str]) -> str:
    """Fold repeated process names into one counted line, longest run first."""
    counts = Counter(names)
    listed = [
        name if n == 1 else f"{name} ({n})" for name, n in counts.most_common(MAX_NAMES)
    ]
    if (rest := len(counts) - MAX_NAMES) > 0:
        listed.append(f"and {rest} more")
    return " · ".join(listed)


def border_title(running: list[str]) -> str:
    """Name the popup after whatever a yes would end, for the border herdr draws.

    Padded because the border sets its label hard against the corner.
    """
    if not running:
        return " close "
    noun = "process" if len(running) == 1 else "processes"
    return f" {clip(f'close {noun} {summarise(running)}?', MAX_TITLE)} "


def span(text: str, *styles: str) -> str:
    r"""Style one run of text, re-establishing the panel background first.

    \x1b[0m drops the background along with the bold or colour it is there to
    clear, and the rest of the row would then paint in the terminal's own.
    """
    return f"\x1b[0m{BG}{''.join(styles)}{text}"


def row(line: int, *spans: str, indent: int = MARGIN) -> str:
    r"""Place one row, clearing the rest of its width in the panel background.

    The trailing span("") is load-bearing: \x1b[K clears with whatever background
    is current, so a row ending in a styled run would bleed it to the right edge.
    """
    return f"\x1b[{line};1H" + span(" " * indent) + "".join(spans) + span("") + "\x1b[K"


KEEP: Final = 0
CLOSE: Final = 1
CHOICE_PAD: Final = 4
CHOICE_GAP: Final = 3
# Counted up from the bottom edge. `ask` redraws this one row in place between
# presses, so it and `render` have to agree on which row it is.
CHOICE_ROW: Final = 5


def hints(line: int, cols: int) -> str:
    """Name the keys that answer, centred on the row the border leaves at the bottom."""
    legend = "   ".join(f"{icon} {word}" for icon, word in HINTS)
    return row(
        line,
        span(legend, DIM, ITALIC),
        indent=max(MARGIN, (cols - len(legend)) // 2),
    )


def choices(picked: int, line: int, cols: int) -> str:
    """Draw the two choices as equal blocks, centred, the picked one accented."""
    labels = ["Cancel", "Okay"]
    width = max(len(label) for label in labels) + CHOICE_PAD * 2
    blocks = [
        span(
            label.center(width),
            *((PICKED_BG, PICKED_FG, BOLD) if i == picked else (REST_BG, SOFT)),
        )
        for i, label in enumerate(labels)
    ]
    total_width = width * 2 + CHOICE_GAP
    return row(
        line,
        blocks[KEEP],
        span(" " * CHOICE_GAP),
        blocks[CLOSE],
        indent=max(MARGIN, (cols - total_width) // 2),
    )


def render(prompt: Prompt, picked: int, rows: int, cols: int) -> str:
    """Draw the prompt: question at the top, choices and keys pinned to the bottom."""
    width = cols - MARGIN * 2
    return "".join(
        [
            "\x1b[0m",
            BG,
            "\x1b[2J",
            "\x1b[?25l",
            row(
                2,
                span(ICONS[prompt.target], BLUE),
                span(
                    "  " + clip(headline(prompt.target, prompt.pressed), width - 3),
                    TEXT,
                    BOLD,
                ),
            ),
            # Blank either side of the choices: their filled background would
            # otherwise read as a stripe across the text rather than as buttons.
            row(rows - CHOICE_ROW - 1),
            choices(picked, rows - CHOICE_ROW, cols),
            row(rows - CHOICE_ROW + 1),
            hints(rows - 3, cols),
            row(rows - 2),
            row(rows - 1, span(clip(prompt.location, width), DIM)),
            row(rows),
        ],
    )


YES: Final = frozenset({"y", "Y"})
NO: Final = frozenset({"n", "N", "q", "Q", "\x03"})


def _has_input(fd: int) -> bool:
    """Report whether more bytes are already waiting, without blocking for them."""
    return bool(select.select([fd], [], [], 0.02)[0])


def read_key(fd: int) -> str:
    """Block for one keypress and name it.

    Escape opens both a lone esc and every arrow key, so the two are told apart
    by whether more bytes are already waiting — nothing follows a key pressed
    alone. Every sequence named below is three bytes, so only two are taken after
    the Escape: a key pressed hard on an arrow's heels stays in the buffer to be
    read as itself rather than being consumed with the arrow.
    """
    first = os.read(fd, 1).decode("latin-1")
    if not first:
        return "esc"
    if first != "\x1b":
        return {"\r": "enter", "\n": "enter", "\t": "next"}.get(first, first)
    if not _has_input(fd):
        return "esc"
    rest = os.read(fd, 2).decode("latin-1")
    return {"[C": "next", "[B": "next", "[D": "prev", "[A": "prev", "[Z": "prev"}.get(
        rest,
        "",
    )


def ask(prompt: Prompt) -> bool:
    """Draw the prompt and hold the tty until a choice is made.

    Opens on "Okay", pointing the default at the destructive answer: the prompt
    only appears when a close was already asked for, so the default agrees with
    the key that was pressed rather than overriding it. esc keeps whatever is
    picked, so the safe answer is always one key.

    Drawing happens inside the try, so the hidden cursor is never left hidden by
    a failure between the two. Only the choices redraw between presses, so the
    text that has not changed does not flicker.
    """
    fd = sys.stdin.fileno()
    size = os.get_terminal_size(fd)
    picked = CLOSE
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write(render(prompt, picked, size.lines, size.columns))
        sys.stdout.flush()
        while True:
            key = read_key(fd)
            if key in ("next", "prev"):
                picked ^= 1
                sys.stdout.write(choices(picked, size.lines - CHOICE_ROW, size.columns))
                sys.stdout.flush()
            elif key == "enter":
                return picked == CLOSE
            elif key == "esc" or key in NO:
                return False
            elif key in YES:
                return True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def close_target(herdr: HerdrClient, level: str, target_id: str) -> None:
    """Close one pane, tab or space through the herdr API.

    A space holding linked worktree spaces closes as a group or not at all —
    anything less is refused as workspace_group_close_required, and a refusal
    here reads as the key having done nothing. The flag is accepted on a space
    that holds none, so it costs nothing to always mean it.
    """
    group = {"close_group": True} if level == "workspace" else {}
    herdr.call(f"{level}.close", {f"{level}_id": target_id, **group})


def worktree_group(spaces: list[dict[str, Any]], workspace_id: str) -> list[str]:
    """Name the linked worktree spaces that close along with this one.

    Only a repo parent has any: herdr refuses to open a worktree from a space
    that is itself a linked checkout, so a linked space is never the head of a
    group and closes alone.
    """
    mine = next((w for w in spaces if w["workspace_id"] == workspace_id), {}).get(
        "worktree",
    )
    if not mine or mine.get("is_linked_worktree"):
        return []
    return [
        w["workspace_id"]
        for w in spaces
        if (wt := w.get("worktree"))
        and wt.get("is_linked_worktree")
        and wt.get("repo_key") == mine.get("repo_key")
    ]


def occupants(herdr: HerdrClient, pane_ids: Iterable[str]) -> list[str]:
    """Name whatever holds each of these panes, leaving out the ones at a prompt."""
    infos = (
        herdr.call("pane.process_info", {"pane_id": pane_id})["process_info"]
        for pane_id in pane_ids
    )
    return [label for info in infos if (label := busy_label(info))]


def open_popup(herdr: HerdrClient, prompt: Prompt) -> None:
    """Hand the question to a popup, the only side of this that holds a tty."""
    herdr.run(
        "plugin",
        "pane",
        "open",
        "--plugin",
        os.environ.get("HERDR_PLUGIN_ID", "user.close-confirm"),
        "--entrypoint",
        "confirm",
        "--env",
        f"CLOSE_CONFIRM_JSON={prompt.to_json()}",
    )


def close_or_prompt(herdr: HerdrClient, pressed: str) -> None:
    """Decide what the pressed key really closes, then close it or raise the prompt."""
    context = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
    workspace = context.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID")
    tab = context.get("tab_id") or os.environ.get("HERDR_TAB_ID")
    pane = context.get("focused_pane_id") or os.environ.get("HERDR_PANE_ID")
    if not workspace or not tab or not pane:
        sys.exit("herdr-tools close: no focused pane in the plugin context")

    panes: list[dict[str, Any]] = herdr.call("pane.list", {"workspace_id": workspace})[
        "panes"
    ]
    tabs: list[dict[str, Any]] = herdr.call("tab.list", {"workspace_id": workspace})[
        "tabs"
    ]
    tab_panes = [p for p in panes if p["tab_id"] == tab]
    # A space closes with its linked worktree spaces or not at all, so what a
    # yes throws away reaches past the space the key named.
    group_panes = [
        p
        for wid in worktree_group(
            herdr.call("workspace.list", {})["workspaces"],
            workspace,
        )
        for p in herdr.call("pane.list", {"workspace_id": wid})["panes"]
    ]
    # Only ever the panes the pressed key would take: an escalation widens what
    # gets closed but not what was inspected, and the last pane in a tab holds
    # the same panes either way.
    scope = {
        "pane": [p for p in panes if p["pane_id"] == pane],
        "tab": tab_panes,
        "workspace": panes + group_panes,
    }

    running = occupants(herdr, (p["pane_id"] for p in scope[pressed]))
    target, must_ask = decide(pressed, len(tab_panes), len(tabs), bool(running))
    target_id = {"pane": pane, "tab": tab, "workspace": workspace}[target]
    if not must_ask:
        close_target(herdr, target, target_id)
        return

    tab_label = next((t.get("label") or "" for t in tabs if t["tab_id"] == tab), "")
    open_popup(
        herdr,
        Prompt(
            target=target,
            pressed=pressed,
            target_id=target_id,
            location=" · ".join(
                part
                for part in (context.get("workspace_label") or workspace, tab_label)
                if part
            ),
            running=running,
        ),
    )


def rename_self(herdr: HerdrClient, label: str) -> None:
    """Put the question in the border, which shows herdr's name for this pane.

    A manifest title is one fixed string, so the question a particular close
    raises can only be asked there from in here. A refusal raises `HerdrError`,
    which `_run` would turn into an exit — for a title, trading a blemish for a
    prompt that never appeared.
    """
    if not (pane_id := os.environ.get("HERDR_PANE_ID")):
        return
    with contextlib.suppress(HerdrError):
        herdr.call("pane.rename", {"pane_id": pane_id, "label": label})


def confirm(herdr: HerdrClient) -> None:
    """The popup's side: ask, and close only on a yes."""
    prompt = Prompt.from_json(os.environ["CLOSE_CONFIRM_JSON"])
    rename_self(herdr, border_title(prompt.running))
    if ask(prompt):
        close_target(herdr, prompt.target, prompt.target_id)


def selftest() -> None:
    """Exercise the policy, the wording and the key reader — everything not I/O."""
    idle = {"shell_pid": 10, "foreground_process_group_id": 10}
    assert busy_label(idle) is None
    assert busy_label({"shell_pid": 10}) is None
    assert busy_label({"shell_pid": 10, "foreground_process_group_id": None}) is None

    agent = {
        "shell_pid": 10,
        "foreground_process_group_id": 20,
        "foreground_processes": [
            {"pid": 99, "argv0": "node", "name": "node"},
            {"pid": 20, "argv0": "claude", "name": "2.1.260"},
        ],
    }
    assert busy_label(agent) == "claude", (
        "the group leader names the pane, not the first child"
    )
    assert busy_label({**agent, "foreground_processes": []}) == "?"
    assert (
        busy_label(
            {
                "shell_pid": 10,
                "foreground_process_group_id": 20,
                "foreground_processes": [
                    {"pid": 20, "argv0": "/usr/bin/nvim -R", "name": "nvim"},
                ],
            },
        )
        == "nvim"
    ), "a path and its arguments reduce to the program"

    def space(wid: str, repo: str, linked: bool) -> dict[str, Any]:
        return {
            "workspace_id": wid,
            "worktree": {"repo_key": repo, "is_linked_worktree": linked},
        }

    spaces = [
        space("w1", "/r", False),
        space("w2", "/r", True),
        space("w3", "/other", True),
        {"workspace_id": "w4", "worktree": None},
    ]
    assert worktree_group(spaces, "w1") == ["w2"], (
        "a parent closes with its own worktrees only"
    )
    assert worktree_group(spaces, "w2") == [], (
        "a linked space is never the head of a group"
    )
    assert worktree_group(spaces, "w4") == [], "a space outside a repo has no group"
    assert worktree_group(spaces, "w9") == [], "an unknown id names no group"

    assert decide("tab", 2, 3, False) == ("tab", False), (
        "an idle tab among others just closes"
    )
    assert decide("tab", 2, 3, True) == ("tab", True)
    assert decide("tab", 2, 1, False) == ("workspace", True), "the last tab always asks"
    assert decide("tab", 2, 1, True) == ("workspace", True)
    assert decide("workspace", 1, 1, False) == ("workspace", False), (
        "naming it is the intent"
    )
    assert decide("workspace", 3, 4, True) == ("workspace", True)

    assert decide("pane", 3, 2, False) == ("pane", False), (
        "one idle pane of several just goes"
    )
    assert decide("pane", 3, 2, True) == ("pane", True)
    assert decide("pane", 1, 3, False) == ("tab", False), (
        "the last pane is the tab, and idle"
    )
    assert decide("pane", 1, 3, True) == ("tab", True)
    assert decide("pane", 1, 1, False) == ("workspace", True), (
        "last pane, last tab: the space"
    )
    assert decide("pane", 1, 1, True) == ("workspace", True)

    assert headline("pane", "pane") == "Close this pane?"
    assert headline("workspace", "workspace") == "Close this space?", (
        "a workspace is a space"
    )
    assert headline("tab", "pane") == "Close the last pane, and the tab with it?"
    assert headline("workspace", "pane") == "Close the last pane, and the space with it?"
    assert headline("workspace", "tab") == "Close the last tab, and the space with it?"

    assert summarise([]) == ""
    assert summarise(["claude", "claude", "nvim"]) == "claude (2) · nvim"
    assert summarise([f"p{n}" for n in range(9)]).endswith(f"and {9 - MAX_NAMES} more")

    assert clip("short", 10) == "short"
    assert clip("abcdefghij", 5) == "abcd…", "a trimmed name must not read as whole"

    assert border_title([]) == " close ", "nothing running, nothing to name"
    assert border_title(["claude"]) == " close process claude? "
    assert border_title(["claude", "nvim"]) == " close processes claude · nvim? "
    assert border_title(["x" * 80]).endswith("… "), (
        "the border keeps its padding when cut"
    )
    assert len(border_title(["x" * 80])) == MAX_TITLE + 2

    prompt = Prompt(
        target="tab",
        pressed="pane",
        target_id="w1:t2",
        location="trunk · api",
        running=["claude"],
    )
    assert Prompt.from_json(prompt.to_json()) == prompt, (
        "the popup reads back what the action sent"
    )

    drawn = render(prompt, CLOSE, 9, 59)
    assert "\x1b[4;1H" in drawn, "the choices sit under the question"
    assert "\x1b[3;1H" in drawn and "\x1b[5;1H" in drawn, (
        "with a blank row either side of them"
    )
    assert "\x1b[6;1H" in drawn and "\x1b[8;1H" in drawn, (
        "then the keys, then the context"
    )
    assert "\x1b[7;1H" in drawn and "\x1b[9;1H" in drawn, (
        "each with a clear row beneath it"
    )
    assert drawn.index(HINTS[0][1]) < drawn.index(prompt.location), "the keys come first"
    assert "\x1b[?25l" in drawn, "no stray block cursor over the prompt"
    assert drawn.count(BG) == drawn.count("\x1b[0m"), (
        "every reset re-establishes the panel bg"
    )
    assert ICONS["tab"] in drawn
    assert all(icon in drawn and word in drawn for icon, word in HINTS)
    assert ITALIC in drawn, "the key legend is set apart from what it sits under"
    assert "claude" not in drawn, (
        "what is running is named on the border, not in the body"
    )

    picked_close = choices(CLOSE, 5, 59)
    picked_keep = choices(KEEP, 5, 59)
    assert picked_close != picked_keep, (
        "the picked choice has to look different from the other"
    )
    assert picked_close.index("Cancel") < picked_close.index("Okay"), (
        "cancelling is on the left"
    )
    assert picked_close.index(PICKED_BG) > picked_close.index("Cancel"), (
        "Okay opens picked"
    )
    assert picked_keep.index(PICKED_BG) < picked_keep.index("Cancel"), (
        "and the pick moves"
    )

    assert picked_close.rstrip().endswith("\x1b[K"), (
        "the row ends restoring the panel background"
    )
    assert BG + "\x1b[K" in picked_close, (
        "so an unpicked choice cannot bleed to the right edge"
    )

    # The row clears its tail with \x1b[K rather than padding it, so the right
    # margin is what the row does not cover.
    plain = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", picked_close)
    # lstrip would eat the padding inside the first choice too, so the indent is
    # read from the leading run before any styled span begins.
    indent = re.match(r"\x1b\[[0-9;]*H(?:\x1b\[[0-9;]*m)+( *)", picked_close)
    left = len(indent.group(1)) if indent else -1
    right = 59 - len(plain)
    assert abs(left - right) <= 1, f"the choices are centred (margins {left} vs {right})"
    assert plain.count("Cancel") == 1 and plain.count("Okay") == 1
    assert plain.index("Cancel") < plain.index("Okay")

    legend = hints(7, 59)
    lead = re.match(r"\x1b\[[0-9;]*H(?:\x1b\[[0-9;]*m)+( *)", legend)
    bare = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", legend)
    assert abs((len(lead.group(1)) if lead else -1) - (59 - len(bare))) <= 1, (
        "the keys are centred"
    )

    keys, typed = os.pipe()
    os.write(typed, b"\x1b[C\r")
    assert read_key(keys) == "next"
    assert read_key(keys) == "enter", (
        "a key hard behind an arrow is not swallowed with it"
    )
    os.write(typed, b"\x1b[B\x1b[B")
    assert [read_key(keys), read_key(keys)] == ["next", "next"], "a held arrow repeats"
    os.write(typed, b"\x1b")
    assert read_key(keys) == "esc", "and a lone esc is not an arrow-key prefix"
    os.close(keys)
    os.close(typed)

    print("ok")


def _run(action: Callable[[HerdrClient], None]) -> None:
    """Run one side of the close, leaving a herdr failure as one line rather than a traceback.

    This runs behind a key the user pressed to close something, where a
    traceback nobody reads is indistinguishable from the close quietly not
    happening.
    """
    try:
        action(HerdrClient.from_environment(os.environ))
    except HerdrError as error:
        sys.exit(f"herdr-tools close: {error}")


def pane_command() -> None:
    """Close the focused pane, confirming first if it is busy or the last one."""
    _run(lambda herdr: close_or_prompt(herdr, "pane"))


def tab_command() -> None:
    """Close the focused tab, confirming first if it is busy or the last one."""
    _run(lambda herdr: close_or_prompt(herdr, "tab"))


def workspace_command() -> None:
    """Close the focused space, confirming first if anything in it is busy."""
    _run(lambda herdr: close_or_prompt(herdr, "workspace"))


def confirm_command() -> None:
    """Ask in the popup whether to close, and close only on a yes."""
    _run(confirm)
