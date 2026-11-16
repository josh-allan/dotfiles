"""One theme file, home/.chezmoidata/theme.toml, sets every themed tool's colours."""

import plistlib
import re
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOME = REPO / "home"
THEME_FILE = HOME / ".chezmoidata/theme.toml"
HEX = re.compile(r"^[0-9a-f]{6}$")
TERMINAL_KEYS = {
    "background", "foreground", "cursor", "cursor_text",
    "selection_background", "selection_foreground", "ansi",
}
UI_ROLES = {
    "text", "muted", "subtle", "faint", "surface", "line", "accent", "accent2",
    "cyan", "green", "red", "yellow", "orange",
}
SYNTAX_ROLES = {
    "comment", "keyword", "string", "function", "type", "constant", "operator",
    "variable", "property", "tag", "inserted", "deleted", "changed",
}
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


def theme() -> dict:
    return tomllib.loads(THEME_FILE.read_text())["theme"]


def palette() -> set[str]:
    t = theme()
    term = t["terminal"]
    return {*term["ansi"], *(v for k, v in term.items() if k != "ansi"), *t["ui"].values(), *t["syntax"].values()}


def execute(template: str, tmp: Path) -> str:
    config = tmp / "chezmoi.toml"
    config.write_text(DATA)
    return subprocess.run(
        ["chezmoi", "execute-template", "--config", str(config), "--source", str(REPO)],
        input=template,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def render(name: str, tmp: Path) -> str:
    return execute((HOME / name).read_text(), tmp)


def test_theme_file_is_complete() -> None:
    t = theme()
    assert t["name"]
    assert set(t["terminal"]) == TERMINAL_KEYS
    assert len(t["terminal"]["ansi"]) == 16
    assert set(t["ui"]) == UI_ROLES
    assert set(t["syntax"]) == SYNTAX_ROLES
    assert set(t["nvim"]) == {"colorscheme", "name", "src"}
    assert all(HEX.match(c) for c in palette()), "colours are 6 lowercase hex digits without #"


def test_chezmoi_exposes_the_theme_as_data(tmp_path: Path) -> None:
    assert execute("{{ .theme.terminal.background }}", tmp_path) == theme()["terminal"]["background"]
