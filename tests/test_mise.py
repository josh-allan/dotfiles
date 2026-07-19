"""Validate mise.toml structure and its split against packages.json."""

import json
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TASKS = {"bootstrap", "install-tools", "install-apps", "sync", "compliance", "check"}


@pytest.fixture(scope="module")
def mise_config():
    with open(_REPO_ROOT / "mise.toml", "rb") as f:
        return tomllib.load(f)


@pytest.fixture(scope="module")
def packages_json():
    with open(_REPO_ROOT / "packages.json") as f:
        return json.load(f)


def test_mise_toml_parses(mise_config):
    assert "tools" in mise_config
    assert "tasks" in mise_config


def test_required_tasks_present(mise_config):
    assert REQUIRED_TASKS <= set(mise_config["tasks"])


def test_bootstrap_depends_on_installs(mise_config):
    depends = set(mise_config["tasks"]["bootstrap"]["depends"])
    assert depends == {"install-tools", "install-apps"}


def test_tools_nonempty(mise_config):
    assert len(mise_config["tools"]) >= 20


def test_no_tool_in_both_manifests(mise_config, packages_json):
    """A tool must live in mise.toml OR packages.json, never both."""
    # Strip backend prefixes like "npm:" and map registry aliases back to
    # the names packages.json historically used.
    aliases = {"delta": "git-delta", "tree-sitter": "tree-sitter-cli"}
    mise_names = set()
    for tool in mise_config["tools"]:
        name = tool.split(":", 1)[-1]
        mise_names.add(aliases.get(name, name))
    pkg_names = {e["name"] for e in packages_json["tools"] + packages_json["apps"]}
    overlap = mise_names & pkg_names
    assert not overlap, f"tools present in both mise.toml and packages.json: {overlap}"
