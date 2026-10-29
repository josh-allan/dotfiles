"""A fake herdr socket that logs each request and answers it by method from staged replies."""

import json
import socketserver
import tempfile
import threading
from pathlib import Path
from types import TracebackType
from typing import Self, cast


class _Server(socketserver.ThreadingUnixStreamServer):
    def __init__(self, path: Path) -> None:
        super().__init__(str(path), _Handler)
        self.replies: dict[str, dict[str, object]] = {}
        self.requests: list[tuple[str, dict[str, object]]] = []


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server = cast(_Server, self.server)
        request: dict[str, object] = json.loads(self.rfile.readline())
        method = str(request["method"])
        params: object = request.get("params")
        server.requests.append((method, params if isinstance(params, dict) else {}))
        reply: dict[str, object] = {
            "id": request.get("id"),
            **server.replies[method],
        }
        self.wfile.write(f"{json.dumps(reply)}\n".encode())


class FakeSocket:
    """A unix socket server, used as a context manager; an unstaged method drops the connection."""

    def __enter__(self) -> Self:
        # Keep the path below macOS's 104-byte AF_UNIX sun_path limit.
        self._root = tempfile.TemporaryDirectory()
        self.path = Path(self._root.name) / "herdr.sock"
        self._server = _Server(self.path)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._root.cleanup()

    def reply(self, method: str, result: object) -> None:
        """Answer `method` with `result`."""
        self._server.replies[method] = {"result": result}

    def fail(self, method: str) -> None:
        """Answer `method` with an error reply."""
        self._server.replies[method] = {
            "error": {"code": "bad", "message": f"{method} failed"},
        }

    @property
    def requests(self) -> list[tuple[str, dict[str, object]]]:
        """Every request's method and params, oldest first."""
        return list(self._server.requests)
