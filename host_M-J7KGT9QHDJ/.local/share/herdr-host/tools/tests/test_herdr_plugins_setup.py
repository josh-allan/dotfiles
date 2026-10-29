"""Tests the host-gated Herdr installer without touching live user state."""

import json
import os
import subprocess
from pathlib import Path

HOST_PACKAGE = "host_M-J7KGT9QHDJ"
REPO_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "scripts" / "sync-dotfiles.sh").is_file()
)
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup-herdr-plugins.sh"
HOST_CONFIG = REPO_ROOT / "hosts" / "M-J7KGT9QHDJ.json"
PLUGIN_NAMES = (
    "close-confirm",
    "focus-watch",
    "lazygit",
    "pane-history",
    "pane-label",
    "space-label",
)


def _executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(0o755)


def _fake_tools(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "calls.log"
    _executable(
        fake_bin / "uv",
        '#!/bin/sh\nprintf \'uv %s\\n\' "$*" >>"$HERDR_SETUP_LOG"\n',
    )
    _executable(
        fake_bin / "herdr",
        """#!/bin/sh
printf 'herdr %s\\n' "$*" >>"$HERDR_SETUP_LOG"
if [ "$1" = plugin ] && [ "$2" = config-dir ]; then
    config_dir="$XDG_CONFIG_HOME/herdr/plugins/config/$3"
    mkdir -p "$config_dir"
    printf '%s\\n' "$config_dir"
fi
""",
    )
    return fake_bin, log


def _environment(tmp_path: Path, fake_bin: Path, log: Path) -> dict[str, str]:
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    return {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "HERDR_CONFIG_PATH": str(home / ".config" / "herdr-host" / "config.toml"),
        "HERDR_SETUP_LOG": str(log),
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    }


def _stow_host(home: Path) -> None:
    (home / ".config").mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "stow",
            "--dir",
            str(REPO_ROOT),
            "--target",
            str(home),
            HOST_PACKAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _run_setup(
    config: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SETUP_SCRIPT), str(config)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_setup_skips_unselected_host(tmp_path: Path) -> None:
    fake_bin, log = _fake_tools(tmp_path)
    config = tmp_path / "other-host.json"
    config.write_text(json.dumps({"packages": {"public": ["dot_config_common"]}}))

    result = _run_setup(config, _environment(tmp_path, fake_bin, log))

    assert result.returncode == 0, result.stderr
    assert not log.exists()


def test_setup_links_selected_plugins_and_managed_reviewr_config(tmp_path: Path) -> None:
    fake_bin, log = _fake_tools(tmp_path)
    environment = _environment(tmp_path, fake_bin, log)
    home = Path(environment["HOME"])
    _stow_host(home)

    result = _run_setup(HOST_CONFIG, environment)

    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert (
        sum(call.startswith("uv tool install --editable --reinstall") for call in calls)
        == 1
    )
    links = [call for call in calls if call.startswith("herdr plugin link ")]
    assert len(links) == len(PLUGIN_NAMES)
    for name in PLUGIN_NAMES:
        assert any(call.endswith(f"/plugins/{name}") for call in links)

    reviewr_config = home / ".config/herdr/plugins/config/persiyanov.reviewr/config.toml"
    managed_config = home / ".local/share/herdr-host/reviewr/config.toml"
    assert reviewr_config.is_symlink()
    assert reviewr_config.resolve() == managed_config.resolve()


def test_setup_preserves_custom_reviewr_config(tmp_path: Path) -> None:
    fake_bin, log = _fake_tools(tmp_path)
    environment = _environment(tmp_path, fake_bin, log)
    home = Path(environment["HOME"])
    _stow_host(home)
    reviewr_config = home / ".config/herdr/plugins/config/persiyanov.reviewr/config.toml"
    reviewr_config.parent.mkdir(parents=True)
    reviewr_config.write_text("auto_open = true\n")

    result = _run_setup(HOST_CONFIG, environment)

    assert result.returncode == 0, result.stderr
    assert not reviewr_config.is_symlink()
    assert reviewr_config.read_text() == "auto_open = true\n"


def test_setup_preserves_dangling_reviewr_config_symlink(tmp_path: Path) -> None:
    fake_bin, log = _fake_tools(tmp_path)
    environment = _environment(tmp_path, fake_bin, log)
    home = Path(environment["HOME"])
    _stow_host(home)
    reviewr_config = home / ".config/herdr/plugins/config/persiyanov.reviewr/config.toml"
    reviewr_config.parent.mkdir(parents=True)
    custom_target = tmp_path / "not-yet-created-reviewr-config.toml"
    reviewr_config.symlink_to(custom_target)

    result = _run_setup(HOST_CONFIG, environment)

    assert result.returncode == 0, result.stderr
    assert reviewr_config.is_symlink()
    assert reviewr_config.resolve(strict=False) == custom_target
