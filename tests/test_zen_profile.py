"""Run the Zen profile-link run script against a fake profile tree."""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "home/.chezmoiscripts/run_after_45-zen-profile.sh"
ENTRIES = ("user.js", "chrome", "zen-themes.json")

INSTALL_INI = """[Install6ED35B3CA1B5D3AF]
Default=Profiles/abc.Default (release)
Locked=1

[Profile0]
Name=Default (release)
IsRelative=1
Path=Profiles/abc.Default (release)
"""

LEGACY_INI = """[Profile0]
Name=default
IsRelative=1
Path=Profiles/xyz.default
Default=1
"""


def setup_tree(tmp: Path, ini: str, profile: str) -> tuple[dict[str, str], Path, Path]:
    home = tmp / "home"
    config = home / ".config/zen"
    (config / "chrome").mkdir(parents=True)
    (config / "user.js").write_text("// prefs\n")
    (config / "zen-themes.json").write_text("{}\n")
    zen_dir = tmp / "zen"
    profile_dir = zen_dir / profile
    profile_dir.mkdir(parents=True)
    (zen_dir / "profiles.ini").write_text(ini)
    env = {"HOME": str(home), "ZEN_DIR": str(zen_dir), "PATH": "/usr/bin:/bin"}
    return env, config, profile_dir


def run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)


def test_links_every_entry_into_install_default(tmp_path: Path) -> None:
    env, config, profile = setup_tree(tmp_path, INSTALL_INI, "Profiles/abc.Default (release)")
    assert run(env).returncode == 0
    for name in ENTRIES:
        assert (profile / name).is_symlink()
        assert (profile / name).readlink() == config / name


def test_falls_back_to_default_profile_flag(tmp_path: Path) -> None:
    env, config, profile = setup_tree(tmp_path, LEGACY_INI, "Profiles/xyz.default")
    assert run(env).returncode == 0
    assert (profile / "chrome").readlink() == config / "chrome"


def test_second_run_changes_nothing(tmp_path: Path) -> None:
    env, _, profile = setup_tree(tmp_path, INSTALL_INI, "Profiles/abc.Default (release)")
    run(env)
    result = run(env)
    assert result.returncode == 0
    assert sorted(p.name for p in profile.iterdir()) == sorted(ENTRIES)


def test_backs_up_real_files_and_dirs(tmp_path: Path) -> None:
    env, _, profile = setup_tree(tmp_path, INSTALL_INI, "Profiles/abc.Default (release)")
    (profile / "chrome").mkdir()
    (profile / "chrome/userChrome.css").write_text("old\n")
    (profile / "zen-themes.json").write_text("old\n")
    assert run(env).returncode == 0
    backups = [p for p in profile.iterdir() if ".bak." in p.name]
    assert sorted(p.name.split(".bak.")[0] for p in backups) == ["chrome", "zen-themes.json"]
    assert (next(p for p in backups if p.name.startswith("chrome")) / "userChrome.css").read_text() == "old\n"


def test_skips_without_profiles_ini(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path), "ZEN_DIR": str(tmp_path / "missing"), "PATH": "/usr/bin:/bin"}
    result = run(env)
    assert result.returncode == 0
    assert "skipping" in result.stdout


def test_fails_when_a_source_is_missing(tmp_path: Path) -> None:
    env, config, _ = setup_tree(tmp_path, INSTALL_INI, "Profiles/abc.Default (release)")
    (config / "zen-themes.json").unlink()
    assert run(env).returncode == 1


def test_finds_profile_root_under_xdg_config(tmp_path: Path) -> None:
    # Zen 1.21 on Fedora keeps profiles.ini in ~/.config/zen, next to the managed files.
    env, config, _ = setup_tree(tmp_path, INSTALL_INI, "Profiles/abc.Default (release)")
    del env["ZEN_DIR"]
    profile = config / "abc.Default (release)"
    profile.mkdir()
    (config / "profiles.ini").write_text(INSTALL_INI.replace("Profiles/", ""))
    assert run(env).returncode == 0
    assert (profile / "chrome").readlink() == config / "chrome"
