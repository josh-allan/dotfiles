"""The focused `herdr-tools` command surface and lazy imports."""

import re
import subprocess
import sys


def test_root_help_lists_only_the_selected_command_groups() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "herdr_tools.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    for command_group in ("close", "focus", "label"):
        assert re.search(rf"^\W*{command_group}\s{{2,}}", result.stdout, re.MULTILINE)
    for unrelated_group in ("dispatch", "orchestrate", "issue", "tab"):
        assert not re.search(
            rf"^\W*{unrelated_group}\s{{2,}}",
            result.stdout,
            re.MULTILINE,
        )


def test_root_help_does_not_import_command_modules() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from herdr_tools.cli import app; "
            "app(['--help'], result_action='return_value'); "
            "print(sorted(m for m in sys.modules "
            "if m.startswith('herdr_tools.') and m != 'herdr_tools.cli'))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[-1] == "[]"
