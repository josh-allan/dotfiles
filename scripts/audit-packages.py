#!/usr/bin/env python3
"""
Compares packages.json against explicitly-installed pacman packages.
Outputs packages installed on this system that aren't in packages.json,
so they can be evaluated and added.

Usage: python3 scripts/audit-packages.py
"""
import json
import os
import subprocess
import sys


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
        print("[ERROR] pacman -Qqe failed", file=sys.stderr)
        sys.exit(1)
    return set(result.stdout.strip().splitlines())


def main():
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
