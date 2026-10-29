"""The herdr CLI client."""

import json
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Literal

import pytest
from fake_herdr import FakeHerdr

from herdr_tools.client import HerdrClient, HerdrError, best_effort, socket_path

type _Mode = Literal[
    "ok",
    "error",
    "bare_error",
    "null",
    "garbage",
    "truncated",
    "closed",
    "silent",
]


class _ReplyServer(socketserver.ThreadingUnixStreamServer):
    """Answers each socket request per `mode`; `closed` replies nothing, `silent` waits for release."""

    def __init__(self, path: Path, mode: _Mode) -> None:
        super().__init__(str(path), _ReplyHandler)
        self.mode = mode
        self.release = threading.Event()
        self.requests: list[str] = []


class _ReplyHandler(socketserver.StreamRequestHandler):
    server: _ReplyServer

    def handle(self) -> None:
        self.server.requests.append(self.rfile.readline().decode())
        if self.server.mode == "error":
            self.wfile.write(
                b'{"id":"x","error":{"code":"bad","message":"no such tab"}}\n',
            )
        elif self.server.mode == "ok":
            self.wfile.write(b'{"id":"x","result":{}}\n')
        elif self.server.mode == "bare_error":
            self.wfile.write(b'{"id":"x","error":{"code":"bad","message":7}}\n')
        elif self.server.mode == "null":
            self.wfile.write(b"null\n")
        elif self.server.mode == "garbage":
            self.wfile.write(b"garbage\n")
        elif self.server.mode == "truncated":
            self.wfile.write(b'{"id":"x","result":{"m":"\xc3')
        elif self.server.mode == "silent":
            self.server.release.wait()


type Serve = Callable[[_Mode], tuple[Path, _ReplyServer]]


@pytest.fixture
def fake(tmp_path: Path) -> FakeHerdr:
    return FakeHerdr(tmp_path)


@pytest.fixture
def serve() -> Iterator[Serve]:
    # A short root: pytest's tmp_path overruns macOS's 104-byte AF_UNIX sun_path.
    servers: list[_ReplyServer] = []
    with tempfile.TemporaryDirectory() as root:

        def start(mode: _Mode) -> tuple[Path, _ReplyServer]:
            path = Path(root) / f"{mode}.sock"
            server = _ReplyServer(path, mode)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            servers.append(server)
            return path, server

        yield start
        for server in servers:
            server.release.set()
            server.shutdown()
            server.server_close()


def _client(socket: Path | None) -> HerdrClient:
    return HerdrClient(Path("/nonexistent"), socket=socket)


def test_call_ok_reply_sends_one_request_line(serve: Serve) -> None:
    path, server = serve("ok")

    assert _client(path).call("tab.move", {"tab_id": "w1:t9"}) == {}

    request: object = json.loads(server.requests[0])
    assert request == {
        "id": "herdr-tools:tab.move",
        "method": "tab.move",
        "params": {"tab_id": "w1:t9"},
    }


def test_call_error_reply_carries_message_and_code(serve: Serve) -> None:
    path, _ = serve("error")

    with pytest.raises(HerdrError, match=r"herdr tab\.move: no such tab") as raised:
        _client(path).call("tab.move", {})

    assert raised.value.code == "bad"


def test_call_error_reply_without_a_message_carries_its_code(serve: Serve) -> None:
    path, _ = serve("bare_error")

    with pytest.raises(HerdrError, match=r'herdr tab\.move: \{"code"') as raised:
        _client(path).call("tab.move", {})

    assert raised.value.code == "bad"


@pytest.mark.parametrize("mode", ["null", "garbage", "truncated", "closed"])
def test_call_unusable_reply_raises(serve: Serve, mode: _Mode) -> None:
    path, _ = serve(mode)

    with pytest.raises(HerdrError, match=r"herdr tab\.move"):
        _client(path).call("tab.move", {})


def test_call_silent_server_times_out(serve: Serve) -> None:
    path, _ = serve("silent")
    started = time.monotonic()

    with pytest.raises(HerdrError) as raised:
        _client(path).call("tab.move", {}, timeout=0.2)

    assert time.monotonic() - started < 2
    assert raised.value.code == ""


def test_call_missing_socket_raises() -> None:
    with pytest.raises(HerdrError, match=r"herdr tab\.move") as raised:
        _client(Path("/nonexistent/herdr.sock")).call("tab.move", {})

    assert isinstance(raised.value.__cause__, FileNotFoundError)


def test_call_without_a_socket_raises() -> None:
    with pytest.raises(HerdrError, match=r"herdr tab\.move"):
        _client(None).call("tab.move", {})


def test_socket_path_falls_back_through_the_environment() -> None:
    configured: Path = socket_path({
        "HERDR_SOCKET_PATH": "/s.sock",
        "XDG_CONFIG_HOME": "/x",
    })
    assert configured == Path("/s.sock")
    assert socket_path({"XDG_CONFIG_HOME": "/x"}) == Path("/x/herdr/herdr.sock")
    assert socket_path({"HOME": "/h"}) == Path("/h/.config/herdr/herdr.sock")


def test_run_returns_stdout_and_logs_args(fake: FakeHerdr) -> None:
    fake.reply("tab list", "tabs\n")

    output: str = HerdrClient(fake.executable).run("tab", "list", "--all")

    assert output == "tabs\n"
    assert fake.calls() == [["tab", "list", "--all"]]


def test_calls_keep_a_multi_line_argument_whole(fake: FakeHerdr) -> None:
    HerdrClient(fake.executable).run("agent", "prompt", "a_1", "line one\nline two")

    assert fake.calls() == [["agent", "prompt", "a_1", "line one\nline two"]]


def test_concurrent_calls_log_whole_records(fake: FakeHerdr) -> None:
    client = HerdrClient(fake.executable)
    processes = [client.spawn("agent", "wait", f"a{i}") for i in range(20)]
    for process in processes:
        process.communicate()

    assert sorted(fake.calls()) == sorted([["agent", "wait", f"a{i}"] for i in range(20)])


def test_non_zero_exit_raises_with_stderr_detail(fake: FakeHerdr) -> None:
    fake.fail("tab get", "no such tab")

    with pytest.raises(HerdrError, match="herdr tab get t_1: no such tab"):
        HerdrClient(fake.executable).run("tab", "get", "t_1")


def test_timeout_override_raises(fake: FakeHerdr) -> None:
    fake.hang("tab list")

    with pytest.raises(HerdrError, match="herdr tab list") as raised:
        HerdrClient(fake.executable).run("tab", "list", timeout=0.2)

    assert isinstance(raised.value.__cause__, subprocess.TimeoutExpired)


def test_missing_binary_raises(fake: FakeHerdr) -> None:
    fake.executable.unlink()

    with pytest.raises(HerdrError) as raised:
        HerdrClient(fake.executable).run("tab", "list")

    assert isinstance(raised.value.__cause__, FileNotFoundError)


def test_spawn_returns_without_waiting(fake: FakeHerdr) -> None:
    fake.hang("agent wait")

    process: subprocess.Popen[str] = HerdrClient(fake.executable).spawn(
        "agent",
        "wait",
        "x",
    )
    time.sleep(0.3)

    try:
        assert process.poll() is None
    finally:
        process.terminate()
        process.communicate()


def test_spawn_start_failure_raises_herdr_error(fake: FakeHerdr) -> None:
    fake.executable.unlink()

    with pytest.raises(HerdrError, match="herdr agent wait x") as raised:
        HerdrClient(fake.executable).spawn("agent", "wait", "x")

    assert isinstance(raised.value.__cause__, FileNotFoundError)


def test_spawn_output_is_text(fake: FakeHerdr) -> None:
    fake.reply("agent wait", "done\n")

    process: subprocess.Popen[str] = HerdrClient(fake.executable).spawn(
        "agent",
        "wait",
        "x",
    )

    assert process.communicate() == ("done\n", "")


def test_best_effort_logs_and_suppresses_herdr_error(
    fake: FakeHerdr,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake.fail("pane rename", "refused")

    with best_effort():
        HerdrClient(fake.executable).run("pane", "rename", "p_1", "x")

    assert "herdr pane rename p_1 x: refused" in capsys.readouterr().err


def test_best_effort_lets_other_errors_through() -> None:
    with pytest.raises(ValueError), best_effort():
        raise ValueError


def test_client_imports_without_pydantic() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['pydantic'] = None; import herdr_tools.client",
        ],
        check=True,
    )


def test_json_error_reply_carries_its_code(fake: FakeHerdr) -> None:
    fake.fail("tab get", '{"error":{"code":"tab_not_found","message":"gone"}}')

    with pytest.raises(HerdrError) as raised:
        HerdrClient(fake.executable).run("tab", "get", "t_1")

    assert raised.value.code == "tab_not_found"


@pytest.mark.parametrize(
    "stderr",
    [
        "no such tab",
        "null",
        "[1]",
        "3",
        '{"error":"tab_not_found"}',
        '{"error":{"code":7}}',
    ],
)
def test_error_without_a_string_code_has_empty_code(fake: FakeHerdr, stderr: str) -> None:
    fake.fail("tab get", stderr)

    with pytest.raises(HerdrError) as raised:
        HerdrClient(fake.executable).run("tab", "get", "t_1")

    assert raised.value.code == ""


def test_timeout_and_missing_binary_have_empty_code(fake: FakeHerdr) -> None:
    fake.hang("tab list")
    with pytest.raises(HerdrError) as timed_out:
        HerdrClient(fake.executable).run("tab", "list", timeout=0.2)
    fake.executable.unlink()
    with pytest.raises(HerdrError) as missing:
        HerdrClient(fake.executable).run("tab", "list")

    assert (timed_out.value.code, missing.value.code) == ("", "")
