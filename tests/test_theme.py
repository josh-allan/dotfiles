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


def test_ghostty_theme_renders_the_palette(tmp_path: Path) -> None:
    t = theme()["terminal"]
    out = render("dot_config/ghostty/themes/dotfiles.tmpl", tmp_path)
    assert f"background = #{t['background']}\n" in out
    assert f"foreground = #{t['foreground']}\n" in out
    assert f"cursor-color = #{t['cursor']}\n" in out
    assert f"cursor-text = #{t['cursor_text']}\n" in out
    assert f"selection-background = #{t['selection_background']}\n" in out
    assert f"selection-foreground = #{t['selection_foreground']}\n" in out
    for i, colour in enumerate(t["ansi"]):
        assert f"palette = {i}=#{colour}\n" in out
    assert "theme = dotfiles\n" in (HOME / "dot_config/ghostty/config").read_text()


PROMPT_ROLES = ["text", "muted", "subtle", "faint", "accent", "accent2", "green", "red", "yellow", "orange"]


def fish_theme_vars(tmp: Path) -> dict[str, str]:
    """Load the rendered theme with fish_config, as public_user/theme.fish does."""
    themes = tmp / "cfg/fish/themes"
    themes.mkdir(parents=True)
    (themes / "dotfiles.theme").write_text(render("dot_config/fish/themes/dotfiles.theme.tmpl", tmp))
    out = subprocess.run(
        ["fish", "--no-config", "-c",
         "fish_config theme choose dotfiles; for v in (set -n | string match -r '^fish_(pager_)?color_.*'); echo $v $$v; end"],
        env={"HOME": str(tmp), "XDG_CONFIG_HOME": str(tmp / "cfg"), "PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin"},
        capture_output=True, text=True, check=True,
    ).stdout
    # fish appends " --theme=dotfiles" to every value it loads from a theme file.
    return {k: v.removesuffix(" --theme=dotfiles") for k, _, v in (l.partition(" ") for l in out.splitlines())}


def test_fish_theme_file_sets_syntax_colours(tmp_path: Path) -> None:
    t = theme()
    s, ui = t["syntax"], t["ui"]
    colours = fish_theme_vars(tmp_path)
    assert colours["fish_color_normal"] == t["terminal"]["foreground"]
    assert colours["fish_color_command"] == s["function"]
    assert colours["fish_color_keyword"] == s["keyword"]
    assert colours["fish_color_quote"] == s["string"]
    assert colours["fish_color_comment"] == f"{s['comment']} --italics"
    assert colours["fish_color_autosuggestion"] == ui["faint"]
    assert colours["fish_pager_color_selected_background"] == f"--background={ui['surface']}"
    assert (HOME / "dot_config/fish/public_user/theme.fish").read_text().count("fish_config theme choose dotfiles") == 1


def test_prompt_colours_come_from_the_ui_roles(tmp_path: Path) -> None:
    ui = theme()["ui"]
    out = render("dot_config/fish/conf.d/00-prompt-colours.fish.tmpl", tmp_path)
    for role in PROMPT_ROLES:
        assert f"set -g _prompt_{role} {ui[role]}\n" in out


def test_prompt_has_no_hard_coded_colours() -> None:
    fish = HOME / "dot_config/fish"
    prompt_files = [fish / "conf.d/prompt.fish", *(fish / "functions").glob("*prompt*.fish")]
    old = re.compile(r"_prompt_(overlay[01]|surface2|lavender|mauve|peach)\b")
    for path in prompt_files:
        text = path.read_text()
        assert not old.search(text), f"{path.name} still uses a Catppuccin colour name"
        assert not re.search(r"^set -g _prompt_\w+ [0-9a-f]{6}$", text, re.M), path.name
    assert not list((fish / "themes").glob("Catppuccin*.theme"))
    assert ".config/fish/themes/Catppuccin *.theme" in (HOME / ".chezmoiremove").read_text()


def tm_theme(tmp: Path) -> dict:
    return plistlib.loads(render("dot_config/bat/themes/dotfiles.tmTheme.tmpl", tmp).encode())


def test_tm_theme_draws_only_from_the_palette(tmp_path: Path) -> None:
    t = theme()
    tm = tm_theme(tmp_path)
    assert tm["name"] == t["name"]
    general = tm["settings"][0]["settings"]
    assert general["background"] == f"#{t['terminal']['background']}"
    assert general["foreground"] == f"#{t['terminal']['foreground']}"
    assert general["lineHighlight"] == f"#{t['ui']['line']}"
    by_scope = {s["scope"].split(",")[0]: s["settings"] for s in tm["settings"][1:]}
    assert by_scope["comment"]["foreground"] == f"#{t['syntax']['comment']}"
    assert by_scope["keyword"]["foreground"] == f"#{t['syntax']['keyword']}"
    assert by_scope["string"]["foreground"] == f"#{t['syntax']['string']}"
    assert by_scope["markup.inserted"]["foreground"] == f"#{t['syntax']['inserted']}"
    used = set(re.findall(r"#([0-9a-f]{6})", render("dot_config/bat/themes/dotfiles.tmTheme.tmpl", tmp_path)))
    assert used <= palette()


def test_bat_and_delta_select_the_theme(tmp_path: Path) -> None:
    assert (HOME / "dot_config/bat/config").read_text().strip() == "--theme=dotfiles"
    assert "  syntax-theme = dotfiles\n" in (HOME / "dot_gitconfig.tmpl").read_text()
    script = render(".chezmoiscripts/run_onchange_after_65-bat-cache.sh.tmpl", tmp_path)
    assert "bat cache --build" in script
    assert len(re.findall(r"\b[0-9a-f]{64}\b", script)) == 2, "hashes of the theme data and the shared template"
