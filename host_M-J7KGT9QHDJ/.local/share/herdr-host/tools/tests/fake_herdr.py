"""A fake `herdr` executable that logs its calls and answers from staged replies."""

import shlex
from pathlib import Path
from typing import Final

_SEPARATOR: Final = "\x1f"
_RECORD_END: Final = "\x1e"


class FakeHerdr:
    """A `/bin/sh` stub at `root/"herdr"`, answering by its first two args (`"tab list"`).

    An unstaged command exits 0 with no output. Staged answers apply in order: `hang`, then
    `fail`, then `script`, which falls through to `reply` unless it exits.
    """

    def __init__(self, root: Path) -> None:
        self.executable = root / "herdr"
        self._log = root / "herdr.log"
        self._staged = root / "herdr-staged"
        self._staged.mkdir()
        quoted_log: str = shlex.quote(str(self._log))
        quoted_staged: str = shlex.quote(str(self._staged))
        self.executable.write_text(
            f"""#!/bin/sh
record=$(printf '%s\\037' "$@"; printf '\\036')
printf '%s' "$record" >>{quoted_log}
key={quoted_staged}/"$1 $2"
[ -e "$key.hang" ] && exec sleep 30
[ -e "$key.fail" ] && {{ cat "$key.fail" >&2; exit 1; }}
[ -e "$key.sh" ] && . "$key.sh"
[ -e "$key.reply" ] && cat "$key.reply"
exit 0
""",
        )
        self.executable.chmod(0o755)

    def reply(self, command: str, stdout: str) -> None:
        """Answer `command` with `stdout`, exit 0."""
        (self._staged / f"{command}.reply").write_text(stdout)

    def fail(self, command: str, stderr: str) -> None:
        """Answer `command` with `stderr`, exit 1."""
        (self._staged / f"{command}.fail").write_text(stderr)

    def script(self, command: str, shell: str) -> None:
        """Run `shell` for `command`, sourced so it sees the call's `"$@"` and may `exit`."""
        (self._staged / f"{command}.sh").write_text(shell)

    def hang(self, command: str) -> None:
        """Make `command` sleep long enough for any caller's timeout to fire."""
        (self._staged / f"{command}.hang").touch()

    def calls(self) -> list[list[str]]:
        """The arguments of every call so far, oldest first."""
        if not self._log.exists():
            return []
        return [
            record.split(_SEPARATOR)[:-1]
            for record in self._log.read_text().split(_RECORD_END)[:-1]
        ]
