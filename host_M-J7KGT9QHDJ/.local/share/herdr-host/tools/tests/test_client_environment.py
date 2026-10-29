"""Tests for `HerdrClient.from_environment`, which builds the client from the environment."""

from pathlib import Path

from herdr_tools.client import HerdrClient


def test_uses_the_launching_herdrs_binary_and_socket() -> None:
    environment = {"HERDR_BIN_PATH": "/x/herdr", "HERDR_SOCKET_PATH": "/x/herdr.sock"}

    assert HerdrClient.from_environment(environment) == HerdrClient(
        Path("/x/herdr"),
        socket=Path("/x/herdr.sock"),
    )


def test_falls_back_to_herdr_on_path_and_the_default_socket() -> None:
    assert HerdrClient.from_environment({"HOME": "/h"}) == HerdrClient(
        Path("herdr"),
        socket=Path("/h/.config/herdr/herdr.sock"),
    )
