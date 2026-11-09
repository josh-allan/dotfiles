"""Run the Vesktop link run script against a fake HOME."""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "home/.chezmoiscripts/run_after_46-vesktop-links.sh"
ENTRIES = ("settings.json", "settings/settings.json", "settings/quickCss.css")
MAC = "Library/Application Support/vesktop"
FLATPAK = ".var/app/dev.vencord.Vesktop/config/vesktop"


def fake_home(tmp: Path, *roots: str) -> tuple[dict[str, str], Path]:
    home = tmp / "home"
    src = home / ".config/vesktop"
    (src / "settings").mkdir(parents=True)
    for name in ENTRIES:
        (src / name).write_text("{}\n")
    for root in roots:
        (home / root).mkdir(parents=True)
    return {"HOME": str(home), "PATH": "/usr/bin:/bin"}, home


def run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)


def test_links_into_every_existing_root(tmp_path: Path) -> None:
    env, home = fake_home(tmp_path, MAC, FLATPAK)
    assert run(env).returncode == 0
    for root in (MAC, FLATPAK):
        for name in ENTRIES:
            assert (home / root / name).readlink() == home / ".config/vesktop" / name


def test_skips_roots_that_do_not_exist(tmp_path: Path) -> None:
    env, home = fake_home(tmp_path, FLATPAK)
    assert run(env).returncode == 0
    assert not (home / MAC).exists()
    assert (home / FLATPAK / "settings.json").is_symlink()


def test_no_roots_is_a_no_op(tmp_path: Path) -> None:
    env, _ = fake_home(tmp_path)
    assert run(env).returncode == 0


def test_backs_up_real_files_and_is_idempotent(tmp_path: Path) -> None:
    env, home = fake_home(tmp_path, FLATPAK)
    (home / FLATPAK / "settings").mkdir()
    (home / FLATPAK / "settings/settings.json").write_text("old\n")
    run(env)
    assert run(env).returncode == 0
    settings = home / FLATPAK / "settings"
    backups = [p for p in settings.iterdir() if ".bak." in p.name]
    assert [p.read_text() for p in backups] == ["old\n"]
    assert (settings / "settings.json").is_symlink()


def test_fails_when_a_source_is_missing(tmp_path: Path) -> None:
    env, home = fake_home(tmp_path, FLATPAK)
    (home / ".config/vesktop/settings/quickCss.css").unlink()
    assert run(env).returncode == 1
