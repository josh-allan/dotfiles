"""Shared fixtures for compliance checker tests."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts/lib is importable from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIB_DIR = str(_REPO_ROOT / "scripts" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)


@pytest.fixture
def repo_root():
    return _REPO_ROOT


@pytest.fixture
def temp_dir():
    """Create a temporary directory, cleaned up after the test."""
    path = tempfile.mkdtemp(prefix="compliance_test_")
    yield Path(path)
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_host_config():
    """Return a minimal valid host config dict."""
    return {
        "os": "linux",
        "packages": {
            "public": ["dot_home"],
            "system": [{"pkg": "etc_linux", "target": "/etc"}],
        },
        "templates": {},
        "skip_paths": [],
        "compliance": {
            "schemaVersion": 1,
            "packages": {"mode": "expected", "expected": [], "absent": []},
            "services": {"mode": "expected", "units": []},
            "files": {"mode": "expected", "expected": []},
        },
    }


@pytest.fixture
def sample_packages_json():
    """Return a minimal packages.json dict."""
    return {
        "tools": [
            {"name": "git"},
            {"name": "neovim"},
            {"name": "awscli", "pacman": "aws-cli"},
            {"name": "lazygit", "aur": True},
        ],
        "apps": [
            {"name": "discord", "aur": True},
            {"name": "ghostty", "aur": True},
            {"name": "blueutil", "platforms": ["macos"]},
        ],
    }


@pytest.fixture
def host_config_file(temp_dir, sample_host_config):
    """Write a host config to a temp file and return its path."""
    path = temp_dir / "host.json"
    path.write_text(json.dumps(sample_host_config, indent=2))
    return str(path)


@pytest.fixture
def packages_json_file(temp_dir, sample_packages_json):
    """Write packages.json to a temp file and return its path."""
    path = temp_dir / "packages.json"
    path.write_text(json.dumps(sample_packages_json, indent=2))
    return str(path)


@pytest.fixture
def mock_pacman_installed():
    """Canned output for 'pacman -Qqe'."""
    return [
        "git",
        "neovim",
        "aws-cli",
        "lazygit",
        "discord",
        "ghostty",
        "base",
        "linux",
        "systemd",
    ]


@pytest.fixture
def mock_systemctl_states():
    """Canned systemctl states keyed by unit name.

    Each entry: (enabled_state, enabled_rc), (active_state, active_rc)
    """
    return {
        "greetd.service": (("enabled", 0), ("active", 0)),
        "mpris-proxy.service": (("disabled", 1), ("inactive", 3)),
        "wol.service": (("not-found", 4), ("inactive", 3)),
        "oneshot-example.service": (("enabled", 0), ("inactive", 3)),
    }


@pytest.fixture
def mock_filesystem_tree(temp_dir):
    """Create a mock filesystem with symlinks and real files.

    Returns (repo_dir, target_dir) both as Path objects.
    """
    repo_dir = temp_dir / "repo"
    target_dir = temp_dir / "home"

    # Repo file structure (simulating a stow package)
    pkg_dir = repo_dir / "dot_home"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / ".gitignore").write_text("*.log\n")
    (pkg_dir / "scripts").mkdir()
    (pkg_dir / "scripts" / "backup.sh").write_text("#!/bin/sh\necho backup\n")

    # Target (home) directory
    target_dir.mkdir(parents=True)

    return repo_dir, target_dir
