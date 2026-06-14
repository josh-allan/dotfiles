#!/usr/bin/env python3
"""
DEPRECATED: Use check-compliance.sh --packages-only instead.

This script is retained for backward compatibility. It delegates to
the new compliance checker and prints a deprecation notice.

Usage: python3 scripts/audit-packages.py
"""

import json
import os
import subprocess
import sys


def main():
    print("NOTE: audit-packages.py is deprecated.", file=sys.stderr)
    print("      Use check-compliance.sh --packages-only instead.", file=sys.stderr)
    print("", file=sys.stderr)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    compliance_script = os.path.join(script_dir, "check-compliance.sh")

    if not os.path.exists(compliance_script):
        print("[WARNING] check-compliance.sh not found. Falling back to legacy.", file=sys.stderr)
        _legacy_audit()
        return

    result = subprocess.run(
        [compliance_script, "--packages-only", "--json"],
        capture_output=True, text=True,
    )

    if result.returncode not in (0, 1, 2):
        print(f"[ERROR] Compliance checker failed (exit {result.returncode}).", file=sys.stderr)
        sys.exit(result.returncode)

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stdout)
        return

    checks = report.get("checks", {}).get("packages", {})
    findings = checks.get("findings", [])

    missing = sorted(
        f["item"] for f in findings
        if f["kind"] == "missing" and not f.get("accepted", False)
    )
    extra = sorted(
        f["item"] for f in findings
        if f["kind"] == "extra" and not f.get("accepted", False)
    )

    if extra:
        print(f"Explicitly installed packages not in packages.json ({len(extra)}):\n")
        for pkg in extra:
            print(f"  {pkg}")

    if missing:
        if extra:
            print()
        print(f"In packages.json but NOT installed ({len(missing)}):\n")
        for pkg in missing:
            print(f"  {pkg}")


def _legacy_audit():
    """Fallback legacy audit (preserved from original audit-packages.py)."""
    def load_packages():
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, "..", "packages.json")
        with open(path) as f:
            return json.load(f)

    def known_pacman_names(data):
        names = set()
        for entry in data.get("tools", []) + data.get("apps", []):
            if "arch" not in entry.get("platforms", ["macos", "arch"]):
                continue
            names.add(entry.get("pacman", entry["name"]))
        return names

    def explicitly_installed():
        result = subprocess.run(["pacman", "-Qqe"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] pacman -Qqe failed (exit {result.returncode}): {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        return set(result.stdout.strip().splitlines())

    data = load_packages()
    known = known_pacman_names(data)
    installed = explicitly_installed()

    untracked = sorted(installed - known)
    print(f"Explicitly installed packages not in packages.json ({len(untracked)}):\n")
    for pkg in untracked:
        print(f"  {pkg}")

    missing = sorted(known - installed)
    if missing:
        print(f"\nIn packages.json but NOT installed ({len(missing)}):\n")
        for pkg in missing:
            print(f"  {pkg}")


if __name__ == "__main__":
    main()
