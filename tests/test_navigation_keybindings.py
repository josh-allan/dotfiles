"""Guard the existing macOS Cmd+H Hide suppression condition."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KARABINER = REPO / "home/.linked/karabiner/karabiner.json"


def test_cmd_h_hide_is_suppressed_only_outside_rex() -> None:
    config = json.loads(KARABINER.read_text())
    selected_profiles = [
        profile for profile in config["profiles"] if profile.get("selected")
    ]
    assert len(selected_profiles) == 1

    rules = selected_profiles[0]["complex_modifications"]["rules"]
    matching_rules = [
        rule
        for rule in rules
        if rule.get("description") == "Disable Cmd+H Hide (rev 2)"
    ]
    assert len(matching_rules) == 1

    manipulators = matching_rules[0]["manipulators"]
    assert len(manipulators) == 1
    manipulator = manipulators[0]
    assert manipulator["from"] == {
        "key_code": "h",
        "modifiers": {"mandatory": ["command"]},
    }
    assert manipulator["conditions"] == [
        {
            "bundle_identifiers": [r"^com\.superlogical\.rex$"],
            "type": "frontmost_application_unless",
        }
    ]
    assert "to" not in manipulator
