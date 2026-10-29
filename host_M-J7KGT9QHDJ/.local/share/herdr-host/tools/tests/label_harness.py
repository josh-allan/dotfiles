"""Run a label command as a real subprocess, outside any herdr, against a given `herdr`."""

import os
import subprocess
import sys
from pathlib import Path

from fake_herdr import FakeHerdr


def run_label_command(
    module: str,
    home: Path,
    herdr: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `python -m module *args` with `HOME`, its state and the socket under `home`.

    Every `HERDR_*` variable that would place the run inside a live pane is dropped, so only
    `env` puts it back.
    """
    environ: dict[str, str] = {
        **os.environ,
        "HOME": str(home),
        "XDG_STATE_HOME": str(home / "state"),
        "PANE_LABEL_STATE": str(home / "pane-label.json"),
        "HERDR_SOCKET_PATH": str(home / "missing.sock"),
        "HERDR_BIN_PATH": str(herdr),
    }
    for name in ("HERDR_ENV", "HERDR_PANE_ID", "HERDR_WORKSPACE_ID", "HERDR_PLUGIN_ID"):
        environ.pop(name, None)
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        env={**environ, **(env or {})},
        input="",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def writes(fake: FakeHerdr, *prefixes: list[str]) -> list[list[str]]:
    """The calls `fake` logged whose first two args are one of `prefixes`, oldest first."""
    return [call for call in fake.calls() if call[:2] in prefixes]
