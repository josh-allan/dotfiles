"""Walk back and forward through the panes that had focus.

herdr's own focus history is a single action, ``keys.last_pane``: a toggle
between the two most recently focused panes. Two presses land where one started,
so there is no third pane behind it and nothing to go forward to. This keeps a
list of the panes focus has landed on instead, with a cursor and two keys.

The list is ordered by recency and holds each pane **once** — the alt-tab model
rather than the browser one. A browser-shaped trail records every visit and
discards everything ahead of the cursor whenever focus lands somewhere new,
which spends the whole history on a handful of panes and throws away the rest:
walking back two panes and then clicking a third permanently loses whatever was
behind it. Recency order spends each slot on a different pane, and a walk only
moves the cursor, so landing somewhere new promotes that pane and leaves every
pane the walk crossed still reachable behind it.

Neither half is reachable from a keybinding. Focus order is not observable by
subscription: ``pane.focused`` fires only for focus set over the socket API, so
the panes this plugin jumps to raise it and the panes chosen by hand do not. The
order is fed instead by the focus-watch plugin, which samples focus and invokes
the ``record`` action below. Focusing an arbitrary pane is ``pane.focus`` on the
socket API, which the CLI never exposes — ``herdr pane focus`` takes a
*direction*, and ``herdr agent focus`` answers ``agent_not_found`` for a pane
running a plain shell. So this speaks to the socket, through the shared
client's ``call``.

Every entry point is a separate short-lived process and herdr overlaps them, so
the file is only ever touched under ``flock``. Ordering a walk against the
record that follows it needs nothing further: the walk writes its cursor before
it focuses, and ``visit`` leaves a pane already under the cursor alone, so the
walk's own landing is known by position rather than guessed from timing.

Closed panes are dropped when the list is walked rather than from a
``pane.closed`` hook: a jump has to ask herdr which panes exist anyway, and a
list nobody is walking does not care that it holds a dead id.

``selftest()`` checks the order and the cursor, which are pure;
everything either side of them is one socket call.
"""

import fcntl
import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

from herdr_tools.client import HerdrClient, best_effort

#: Panes kept. Deep enough that the far end is never the reason a walk stops;
#: with one slot per distinct pane that is far more history than it sounds.
LIMIT: Final = 50

#: herdr creates this per plugin and owns nothing inside it. The fallback is the
#: same path herdr would pass, for a run by hand outside the plugin runtime.
STATE_DIR: Final = Path(
    os.environ.get("HERDR_PLUGIN_STATE_DIR")
    or Path.home() / ".local/state/herdr/plugins/user.pane-history",
)
STATE: Final = STATE_DIR / "trail.json"
LOCK: Final = STATE_DIR / "trail.lock"


@contextmanager
def held() -> Iterator[None]:
    """Hold the state file's lock across one read-modify-write.

    herdr runs overlapping plugin processes, so a read-then-write that is not
    serialised drops whichever update lands first.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def dedupe(panes: Iterable[str]) -> list[str]:
    """Keep the first appearance of each pane, in order, up to ``LIMIT``."""
    return list(dict.fromkeys(panes))[:LIMIT]


def load() -> tuple[list[str], int]:
    """Read the pane order and the cursor.

    Every failure means the same thing — there is no usable history — so a
    missing file, a truncated write, and the state an older version of this
    plugin left behind are all answered by starting over rather than by three
    branches. ``dedupe`` runs on the way in so nothing downstream has to cope
    with a file that lost the one-slot-per-pane invariant.
    """
    try:
        state = json.loads(STATE.read_text())
        return dedupe(str(pane) for pane in state["order"]), int(state["at"])
    except (OSError, ValueError, TypeError, KeyError):
        return [], 0


def save(panes: list[str], at: int) -> None:
    """Write the order and the cursor atomically."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=STATE_DIR, delete=False) as handle:
        json.dump({"order": panes, "at": at}, handle)
        temp = Path(handle.name)
    temp.replace(STATE)


def visit(panes: list[str], at: int, pane: str) -> tuple[list[str], int]:
    """Fold a newly focused pane into the order, and return it with the cursor.

    Args:
        panes: Panes in the order focus last left them, most recent first.
        at: Index of the pane the cursor is on.
        pane: The pane that now has focus.

    Returns:
        The order unchanged when ``pane`` is already under the cursor — a walk
        moves the cursor before it focuses, so that is the walk's own landing
        and promoting it would undo the walk. Otherwise ``pane`` moves to the
        front with the pane the walk had settled on behind it, and the cursor
        comes home. Nothing is dropped but the far end at ``LIMIT``, so every
        pane a walk crossed stays reachable by walking back.
    """
    if at < len(panes) and panes[at] == pane:
        return panes, at
    settled = [*panes[at : at + 1], *panes[:at], *panes[at + 1 :]]
    return dedupe([pane, *settled]), 0


def step(
    panes: list[str],
    at: int,
    delta: int,
    alive: frozenset[str],
) -> tuple[list[str], int]:
    """Drop panes that have closed, then move the cursor ``delta`` places.

    Args:
        panes: Panes in the order focus last left them, most recent first.
        at: Index of the pane the cursor is on.
        delta: 1 to walk back towards older panes, -1 to walk forward.
        alive: Every pane id herdr still has.

    Returns:
        The pruned order and the cursor's new index, clamped at both ends — so
        walking off the oldest end stops there rather than wrapping round to the
        newest, which is the one thing a back button must not do.
    """
    kept = [pane for pane in panes if pane in alive]
    if not kept:
        return kept, 0
    # Live panes ahead of the cursor = where the cursor's own pane lands in the
    # pruned order. If that pane is one of the closed ones, the same count is
    # the next survivor along, which is as good a place to walk from as any.
    here = min(sum(1 for pane in panes[:at] if pane in alive), len(kept) - 1)
    return kept, min(max(here + delta, 0), len(kept) - 1)


def record(herdr: HerdrClient) -> None:
    """Fold the pane that now has focus into the order.

    The focused pane is asked for rather than read from ``HERDR_PANE_ID``: this
    runs as an action invoked by the user.focus-watch plugin's poller, whose
    own pane is not the one that just took focus.
    """
    pane: str = herdr.call("pane.current", {})["pane"]["pane_id"]
    with held():
        save(*visit(*load(), pane))


def walk(herdr: HerdrClient, *, back: bool) -> None:
    """Move the cursor one pane and focus what it lands on."""
    # Asked for before the lock: a socket round trip is far longer than the
    # read-modify-write it would otherwise hold the file across, and a pane
    # closing in that gap only costs one more press.
    live_panes: list[dict[str, Any]] = herdr.call("pane.list", {})["panes"]
    alive = frozenset(pane["pane_id"] for pane in live_panes)
    # The poller samples focus rather than being told about it, so a pane
    # focused within its last interval may not be recorded yet. This is the
    # same fold it would have done, on the reply the walk already needed.
    current = next((pane["pane_id"] for pane in live_panes if pane["focused"]), "")
    with held():
        panes, at = load()
        if current:
            panes, at = visit(panes, at, current)
        here = panes[at] if at < len(panes) else ""
        panes, at = step(panes, at, 1 if back else -1, alive)
        stuck = not panes or panes[at] == here
        if not stuck:
            # Written before the jump, never after: the poller reads the cursor
            # to tell the walk's own landing from a pane the user chose, so the
            # cursor has to be published before the focus it explains.
            save(panes, at)
    # The walk clamps at both ends, so a press with nowhere to go comes back
    # holding the pane it started on. Saying so beats a key that silently does
    # nothing — there is no scrollbar here to show which end you are at.
    if stuck:
        # Delivery is whatever `ui.toast.delivery` says; there is no per-call
        # override. The sound is asked for on top of the banner because this
        # fires on a keypress, when the eyes are on the pane rather than on
        # whichever corner the toast lands in; `ui.sound.enabled` still mutes it.
        with best_effort():
            herdr.call(
                "notification.show",
                {
                    "title": f"{'Start' if back else 'End'} of pane history",
                    "body": f"No {'older' if back else 'newer'} pane to go to.",
                    "sound": "request",
                },
            )
        return
    with best_effort():
        herdr.call("pane.focus", {"pane_id": panes[at]})


def record_command() -> None:
    """Add the focused pane to the front of the pane history."""
    record(HerdrClient.from_environment(os.environ))


def back_command() -> None:
    """Focus the next older pane in the pane history."""
    walk(HerdrClient.from_environment(os.environ), back=True)


def forward_command() -> None:
    """Focus the next newer pane in the pane history."""
    walk(HerdrClient.from_environment(os.environ), back=False)


def selftest() -> None:
    """Check the order and the cursor, the only parts that can be wrong."""
    assert dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"], (
        "the first appearance wins"
    )

    assert visit([], 0, "p1") == (["p1"], 0), "the first pane starts the order"
    assert visit(["p1"], 0, "p1") == (["p1"], 0), (
        "refocusing the front pane changes nothing"
    )
    assert visit(["p1"], 0, "p2") == (["p2", "p1"], 0), "a new pane goes to the front"
    trio = ["p1", "p2", "p3"]
    assert visit(trio, 0, "p3") == (["p3", "p1", "p2"], 0), (
        "a revisit is promoted, not repeated"
    )

    # Walked back to p3, then focused something else. p3 follows to the front
    # rather than being left where the walk found it, and p1 and p2 both survive
    # — a browser-shaped trail dropped everything past the cursor here.
    assert visit(trio, 2, "p9") == (["p9", "p3", "p1", "p2"], 0), (
        "landing keeps what the walk crossed"
    )

    assert visit(trio, 2, "p3") == (trio, 2), (
        "a pane already under the cursor is left where the walk put it"
    )
    over = [f"p{n}" for n in range(LIMIT)]
    capped, cursor = visit(over, 0, "new")
    assert len(capped) == LIMIT and capped[0] == "new", (
        "the order is capped from the far end"
    )
    assert cursor == 0, "and the cursor comes home to the front"

    walked = ["p1", "p2", "p3", "p4"]
    every = frozenset(walked)
    assert step(walked, 0, 1, every) == (walked, 1), (
        "back moves one towards the older end"
    )
    assert step(walked, 1, -1, every) == (walked, 0), (
        "forward moves one towards the newer end"
    )
    assert step(walked, 3, 1, every) == (walked, 3), (
        "back stops at the oldest, it does not wrap"
    )
    assert step(walked, 0, -1, every) == (walked, 0), "forward stops at the newest"
    assert step([], 0, 1, every) == ([], 0), "an empty order goes nowhere"

    # Clamping lands back on the pane the press started from, and that equality
    # is exactly what `walk` reads as "nowhere to go" before it notifies.
    stuck, cursor = step(walked, 3, 1, every)
    assert stuck[cursor] == walked[3], "a clamped walk returns the pane it started on"

    # p2 and p3 have closed. The cursor was on p4, which survives as index 1.
    some = frozenset({"p1", "p4"})
    assert step(walked, 3, -1, some) == (["p1", "p4"], 0), (
        "closed panes drop out of the walk"
    )
    assert step(walked, 0, 1, some) == (["p1", "p4"], 1), (
        "and the cursor still tracks what is left"
    )
    assert step(walked, 2, 1, some) == (["p1", "p4"], 1), (
        "a cursor on a closed pane lands after it"
    )
    assert step(walked, 1, 1, frozenset({"p9"})) == ([], 0), (
        "nothing left alive, nothing to do"
    )

    print("ok")
