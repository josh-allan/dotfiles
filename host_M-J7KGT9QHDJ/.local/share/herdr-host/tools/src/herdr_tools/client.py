"""Reaches herdr through its CLI and its socket.

Every failure it waits for becomes one `HerdrError`.
"""

import shlex
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NamedTuple, Self

DEFAULT_TIMEOUT_SECONDS: Final = 5


class HerdrError(Exception):
    """A herdr command or socket request failed, timed out, or could not start.

    Attributes:
        code: herdr's error code, e.g. `tab_not_found`; empty when it gave none.
    """

    def __init__(self, message: str, *, code: str = "") -> None:
        """Carry `message` and herdr's error `code`."""
        super().__init__(message)
        self.code = code


def _error_code(stderr: str) -> str:
    """Return herdr's `{"error": {"code": ...}}` stderr code, or empty.

    `json` loads here so only a failed call pays its import.
    """
    import json

    try:
        reply: object = json.loads(stderr)
    except ValueError:
        return ""
    error: object = reply.get("error") if isinstance(reply, dict) else None
    code: object = error.get("code") if isinstance(error, dict) else None
    return code if isinstance(code, str) else ""


class _ReplyFailure(NamedTuple):
    detail: str
    code: str = ""


def _reply_failure(reply: str) -> _ReplyFailure | None:
    """Return why a socket reply line is unusable, or None for a usable reply."""
    import json

    try:
        parsed: object = json.loads(reply)
    except ValueError:
        return _ReplyFailure(f"unreadable reply {reply.strip()!r}")
    if not isinstance(parsed, dict):
        return _ReplyFailure(f"reply is not an object: {reply.strip()!r}")
    error: object = parsed.get("error")
    if error is None:
        return None
    fields: dict[object, object] = error if isinstance(error, dict) else {}
    message: object = fields.get("message")
    code: object = fields.get("code")
    return _ReplyFailure(
        message if isinstance(message, str) else json.dumps(error),
        code if isinstance(code, str) else "",
    )


def socket_path(environment: Mapping[str, str]) -> Path:
    """Resolve herdr's socket from the environment or its standard config directory."""
    if configured := environment.get("HERDR_SOCKET_PATH"):
        return Path(configured)
    if config_home := environment.get("XDG_CONFIG_HOME"):
        return Path(config_home) / "herdr" / "herdr.sock"
    home = Path(environment.get("HOME") or Path.home())
    return home / ".config" / "herdr" / "herdr.sock"


@dataclass(frozen=True, slots=True)
class HerdrClient:
    """The herdr CLI and its socket for methods the CLI lacks; reads no environment."""

    executable: Path
    socket: Path | None = None

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> Self:
        """Build the client for the herdr process that launched this command."""
        return cls(
            Path(environment.get("HERDR_BIN_PATH", "herdr")),
            socket=socket_path(environment),
        )

    def call(
        self,
        method: str,
        params: Mapping[str, object],
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Any:
        """Send one socket request and return the reply's result.

        `json` and `socket` load here so CLI-only callers never pay their import.
        """
        import json
        import socket

        if self.socket is None:
            raise HerdrError(f"herdr {method}: no socket configured")
        request: str = json.dumps({
            "id": f"herdr-tools:{method}",
            "method": method,
            "params": params,
        })
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(timeout)
                connection.connect(str(self.socket))
                connection.sendall(f"{request}\n".encode())
                with connection.makefile(encoding="utf-8") as replies:
                    reply: str = replies.readline()
        except (OSError, UnicodeDecodeError) as error:
            raise HerdrError(f"herdr {method}: {self.socket}: {error}") from error
        if not reply.strip():
            raise HerdrError(f"herdr {method}: empty reply")
        if failure := _reply_failure(reply):
            raise HerdrError(f"herdr {method}: {failure.detail}", code=failure.code)
        return json.loads(reply).get("result")

    def run(self, *args: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
        """Run one herdr command and return its stdout."""
        command = f"herdr {shlex.join(args)}"
        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                [str(self.executable), *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise HerdrError(f"{command}: {error}") from error
        if result.returncode:
            detail: str = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"exited {result.returncode}"
            )
            raise HerdrError(f"{command}: {detail}", code=_error_code(result.stderr))
        return result.stdout

    def spawn(self, *args: str) -> subprocess.Popen[str]:
        """Start one herdr command without waiting; the caller owns the process."""
        try:
            return subprocess.Popen(
                [str(self.executable), *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            raise HerdrError(f"herdr {shlex.join(args)}: {error}") from error


@contextmanager
def best_effort() -> Iterator[None]:
    """Suppress a `HerdrError` raised in the block, printing it to stderr."""
    try:
        yield
    except HerdrError as error:
        print(error, file=sys.stderr)
