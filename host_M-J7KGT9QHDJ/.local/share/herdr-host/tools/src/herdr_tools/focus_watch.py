"""Sample which pane has focus, and invoke the plugins that follow it.

herdr 0.9 emits ``pane.focused`` and ``workspace.focused`` from one place —
``accept_current_focus_with_api_events``, reached only when a **public socket
API** request set the focus. Every other path calls
``accept_current_focus_without_events``, which does not merely skip the emit: it
advances the ``last_focus`` baseline the emitting call compares against, so the
transition is swallowed and no later call can re-raise it. Focus moved by a
keybinding, a click, a space switch or the picker therefore announces nothing.

That leaves three plugins reading a focus that only ever changes when one of
them changed it. None of the other twenty-five event kinds carries the fact:
``pane.updated`` is emitted only for an agent rename, and ``layout.updated``
only for a split, close, move or swap. So focus has to be sampled, and sampling
needs something long-lived — which is this.

Its consumers are named as plugin actions rather than as paths into their
directories, so this knows only ids and herdr runs each command in its own
plugin root with its own state directory.

Three things keep a sampler from becoming a stray process, and ``selftest()``
covers the one that is decidable without a server:

* one poller at a time, held by ``flock`` — a lock the kernel drops even if the
  process is killed outright, which a pidfile would not;
* it exits when the socket goes, which is how it dies with herdr;
* ``chezmoi apply`` retires it when this module or the client changes. It does
  not watch its own file: the editable install runs from the main checkout,
  where a ``git pull`` would retire it with nothing to respawn it.
"""

import contextlib
import fcntl
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import IO, Final

from herdr_tools.client import HerdrClient, HerdrError

#: Between samples. Short enough that a focus change is recorded before the next
#: keypress could act on it, long enough to stay invisible: one `pane.current` is
#: a sub-millisecond read on the server side.
INTERVAL: Final = 0.25

#: The plugins that need to know, as `(plugin_id, action_id)`. Each re-derives
#: whatever it keeps from herdr's own state, so the notification carries nothing.
CONSUMERS: Final = (
    ("user.pane-history", "record"),
    ("user.pane-label", "sweep"),
    ("user.space-label", "sweep"),
)

#: herdr creates this per plugin and owns nothing inside it. The fallback is the
#: same path herdr would pass, for a run by hand outside the plugin runtime.
STATE_DIR: Final = Path(
    os.environ.get("HERDR_PLUGIN_STATE_DIR")
    or Path.home() / ".local/state/herdr/plugins/user.focus-watch",
)
LOCK: Final = STATE_DIR / "poller.lock"


def claim(lock: Path) -> IO[str] | None:
    """Take the single-instance lock, or return ``None`` if a poller holds it.

    The handle is returned rather than the lock being released, because the
    lock is held for as long as the poller runs: closing it — or dying, however
    abruptly — is what hands it to the next one.
    """
    lock.parent.mkdir(parents=True, exist_ok=True)
    # Opened without truncation: "w" would empty the file before `flock` decides
    # anything, throwing away the running poller's pid on the way past.
    handle = os.fdopen(os.open(lock, os.O_CREAT | os.O_RDWR, 0o600), "r+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def focused(herdr: HerdrClient) -> str:
    """Return the pane herdr currently considers focused."""
    return str(herdr.call("pane.current", {})["pane"]["pane_id"])


def notify(herdr: HerdrClient) -> None:
    """Invoke every consumer's action once; one failing consumer never stops the rest."""
    for plugin_id, action_id in CONSUMERS:
        with contextlib.suppress(HerdrError):
            herdr.call(
                "plugin.action.invoke",
                {"plugin_id": plugin_id, "action_id": action_id},
            )


def poll(herdr: HerdrClient, interval: float = INTERVAL) -> None:
    """Sample focus until the socket goes away.

    The first sample always notifies: a poller starting up has no idea what its
    consumers last saw, and herdr's own startup hooks fire before a session is
    necessarily settled.

    Args:
        herdr: The client whose socket is sampled.
        interval: Seconds between samples.
    """
    last = ""
    while True:
        try:
            current = focused(herdr)
        except HerdrError:
            # A dead socket is a reason to stop rather than one to retry.
            return
        if current and current != last:
            last = current
            notify(herdr)
        time.sleep(interval)


def stop(lock: Path) -> bool:
    """Ask a running poller to exit. ``True`` if one was there to ask."""
    idle = claim(lock)
    if idle is not None:
        idle.close()
        return False
    try:
        os.kill(int(lock.read_text()), signal.SIGTERM)
    except (OSError, ValueError):
        return False
    return True


def selftest() -> None:
    """Check the single-instance lock that keeps this from becoming a stray process."""
    scratch = Path(tempfile.mkdtemp())

    lock = scratch / "poller.lock"
    held = claim(lock)
    assert held is not None, "the first poller takes the lock"
    assert claim(lock) is None, "a second poller finds it taken and stands down"
    assert lock.read_text() == str(os.getpid()), "the holder's pid stays readable"
    held.close()
    reclaimed = claim(lock)
    assert reclaimed is not None, "releasing the lock hands it to the next poller"
    reclaimed.close()

    print("ok")


def watch_command(*, detach: bool = False, stop_running: bool = False) -> None:
    """Poll for focus changes, or manage the poller that is doing so.

    Args:
        detach: Start a poller in its own session and return. herdr's
            startup hooks are one-shot commands rather than supervised
            daemons, so the hook spawns and exits.
        stop_running: Signal a running poller to exit, and return.
    """
    if stop_running:
        stop(LOCK)
        return
    if detach:
        subprocess.Popen(
            # -P: the inherited cwd must not shadow an import.
            [sys.executable, "-P", "-m", "herdr_tools.cli", "focus", "watch"],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    held = claim(LOCK)
    if held is None:
        return
    with held:
        poll(HerdrClient.from_environment(os.environ))
