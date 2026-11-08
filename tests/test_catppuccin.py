"""Catppuccin Mocha is wired into every themed CLI tool, from pinned upstream ports."""

import re
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOME = REPO / "home"
SHA = re.compile(r"/[0-9a-f]{40}/")
# Every host flag the public .chezmoiignore and externals read, set to a plain Mac.
DATA = """[data]
host = "test"
work = false
opVault = "Personal"
asahi = false
sunshine = false
server = false
linger = false
hyprHost = ""
fetchSshKey = false
privatePkgs = []
gitName = ""
gitEmail = ""
gitSigningKey = ""
"""


def render(name: str, tmp: Path) -> str:
    config = tmp / "chezmoi.toml"
    config.write_text(DATA)
    return subprocess.run(
        ["chezmoi", "execute-template", "--config", str(config), "--source", str(REPO)],
        input=(HOME / name).read_text(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_theme_externals_are_pinned_to_commits(tmp_path: Path) -> None:
    externals = tomllib.loads(render(".chezmoiexternal.toml.tmpl", tmp_path))
    themes = {k: v for k, v in externals.items() if v.get("type") == "file"}
    assert set(themes) == {
        ".config/bat/themes/Catppuccin Mocha.tmTheme",
        ".config/btop/themes/catppuccin_mocha.theme",
        ".config/lazygit/catppuccin-mocha-blue.yml",
        ".config/eza/theme.yml",
    }
    for target, spec in themes.items():
        assert SHA.search(spec["url"]), f"{target} is not pinned to a commit"
        assert "mocha" in spec["url"].lower(), f"{target} is not the Mocha flavour"


def test_bat_and_delta_use_mocha() -> None:
    assert (HOME / "dot_config/bat/config").read_text().strip() == '--theme="Catppuccin Mocha"'
    assert "  syntax-theme = Catppuccin Mocha\n" in (HOME / "dot_gitconfig.tmpl").read_text()


def test_fish_chooses_mocha_and_frozen_theme_is_gone() -> None:
    theme = (HOME / "dot_config/fish/public_user/theme.fish").read_text()
    assert 'fish_config theme choose "Catppuccin Mocha"' in theme
    assert (HOME / "dot_config/fish/themes/Catppuccin Mocha.theme").exists()
    assert not (HOME / "dot_config/fish/conf.d/fish_frozen_theme.fish").exists()
    assert ".config/fish/conf.d/fish_frozen_theme.fish" in (HOME / ".chezmoiremove").read_text()


def test_fzf_uses_mocha_colours() -> None:
    opts = (HOME / "dot_config/fish/public_user/fzf.fish").read_text()
    assert "bg:#1E1E2E" in opts and "--color=dark" not in opts


def btop(tmp: Path, existing: str) -> str:
    dest = tmp / "home"
    (dest / ".config/btop").mkdir(parents=True)
    (dest / ".config/btop/btop.conf").write_text(existing)
    config = tmp / "chezmoi.toml"
    config.write_text(DATA)
    return subprocess.run(
        [
            "chezmoi", "cat", str(dest / ".config/btop/btop.conf"),
            "--config", str(config), "--source", str(REPO), "--destination", str(dest),
            "--persistent-state", str(tmp / "state.boltdb"),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_btop_modify_sets_only_the_theme(tmp_path: Path) -> None:
    out = btop(tmp_path, 'theme_background = True\ncolor_theme = "Default"\nupdate_ms = 2000\n')
    assert out == 'theme_background = True\ncolor_theme = "catppuccin_mocha"\nupdate_ms = 2000\n'


def test_btop_modify_adds_the_theme_when_absent(tmp_path: Path) -> None:
    out = btop(tmp_path, "update_ms = 2000\n")
    assert out.startswith('color_theme = "catppuccin_mocha"\n')
    assert "update_ms = 2000" in out
