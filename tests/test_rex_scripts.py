"""Render the Rex run scripts and run them against fake rex/defaults/pgrep binaries."""

import os
import platform
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "home/.chezmoiscripts"

FAKE_REX = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_LOG"
case "$*" in
  *"server status"*) exit "${FAKE_STATUS_EXIT:-0}" ;;
  *"skill setup --dry-run --json"*) printf '%s' "$FAKE_DRYRUN_JSON" ;;
esac
exit 0
"""

FAKE_DEFAULTS = """#!/usr/bin/env bash
printf 'defaults %s\\n' "$*" >> "$FAKE_LOG"
"""

# pgrep finds no Rex unless FAKE_PGREP_EXIT=0.
FAKE_PGREP = """#!/usr/bin/env bash
exit "${FAKE_PGREP_EXIT:-1}"
"""


def render(tmp: Path, name: str) -> Path:
    config = tmp / "chezmoi.toml"
    config.write_text("")
    out = subprocess.run(
        ["chezmoi", "execute-template", "--config", str(config), "--source", str(REPO)],
        input=(SCRIPTS / name).read_text(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    script = tmp / (name.removesuffix(".tmpl"))
    script.write_text(out)
    return script


def fakes(tmp: Path) -> dict[str, str]:
    bindir = tmp / "bin"
    bindir.mkdir()
    for name, body in {"rex": FAKE_REX, "defaults": FAKE_DEFAULTS, "pgrep": FAKE_PGREP}.items():
        path = bindir / name
        path.write_text(body)
        path.chmod(0o755)
    home = tmp / "home"
    home.mkdir()
    return {
        "PATH": f"{bindir}:/usr/bin:/bin",
        "HOME": str(home),
        "REX_BIN_DIR": str(bindir),
        "FAKE_LOG": str(tmp / "calls.log"),
    }


def run(script: Path, env: dict[str, str]) -> tuple[list[str], str]:
    result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, check=True)
    log = Path(env["FAKE_LOG"])
    calls = log.read_text().splitlines() if log.exists() else []
    return calls, result.stderr


darwin_only = pytest.mark.skipif(platform.system() != "Darwin", reason="settings script is darwin-only")


@darwin_only
def test_settings_pins_every_key(tmp_path: Path) -> None:
    script = render(tmp_path, "run_onchange_after_60-rex-settings.sh.tmpl")
    calls, stderr = run(script, fakes(tmp_path))
    writes = [c for c in calls if c.startswith("defaults write com.superlogical.rex ")]
    assert len(writes) == 16
    assert "defaults write com.superlogical.rex Workspace.tabStyle -string vertical" in writes
    assert "quit and reopen Rex" not in stderr


@darwin_only
def test_settings_warns_when_rex_runs(tmp_path: Path) -> None:
    script = render(tmp_path, "run_onchange_after_60-rex-settings.sh.tmpl")
    env = fakes(tmp_path) | {"FAKE_PGREP_EXIT": "0"}
    _, stderr = run(script, env)
    assert "quit and reopen Rex" in stderr


def test_config_reload_hashes_each_lua_file(tmp_path: Path) -> None:
    text = render(tmp_path, "run_onchange_after_61-rex-config-reload.sh.tmpl").read_text()
    lua = sorted((REPO / "home/dot_config/rex").glob("*.lua"))
    assert lua
    for path in lua:
        assert f"\n# {path.name} " in text


def test_config_reload_runs_only_with_a_server(tmp_path: Path) -> None:
    script = render(tmp_path, "run_onchange_after_61-rex-config-reload.sh.tmpl")
    env = fakes(tmp_path)
    calls, _ = run(script, env)
    assert "--autostart=false config reload" in calls
    Path(env["FAKE_LOG"]).unlink()
    calls, _ = run(script, env | {"FAKE_STATUS_EXIT": "4"})
    assert "--autostart=false config reload" not in calls


def test_terminfo_entry_only_when_ssh_config_is_linked(tmp_path: Path) -> None:
    script = render(tmp_path, "run_onchange_after_62-rex-terminfo.sh.tmpl")
    env = fakes(tmp_path)
    calls, _ = run(script, env)
    assert calls == ["terminfo setup"]
    ssh = Path(env["HOME"]) / ".ssh"
    ssh.mkdir()
    (ssh / "config").symlink_to(tmp_path / "chezmoi.toml")
    Path(env["FAKE_LOG"]).unlink()
    calls, stderr = run(script, env)
    assert calls == ["terminfo setup --entry-only"]
    assert "managed" in stderr


def test_skill_setup_skips_when_nothing_changes(tmp_path: Path) -> None:
    script = render(tmp_path, "run_after_63-rex-skill-setup.sh.tmpl")
    unchanged = '{"steps":[{"change":"unchanged"},{"change":"skipped"}]}'
    calls, _ = run(script, fakes(tmp_path) | {"FAKE_DRYRUN_JSON": unchanged})
    assert calls == ["--autostart=false skill setup --dry-run --json"]


def test_skill_setup_runs_when_a_step_changes(tmp_path: Path) -> None:
    script = render(tmp_path, "run_after_63-rex-skill-setup.sh.tmpl")
    pending = '{"steps":[{"change":"unchanged"},{"change":"updated"}]}'
    calls, _ = run(script, fakes(tmp_path) | {"FAKE_DRYRUN_JSON": pending})
    assert calls[-1] == "--autostart=false skill setup"
