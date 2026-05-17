#!/usr/bin/env python3
"""
Reads packages.json and installs packages for the current platform.
Usage: python3 install-packages.py [--platform macos|arch] [--dry-run]
"""
import json
import os
import shutil
import subprocess
import sys
import argparse


def detect_platform():
    if sys.platform == "darwin":
        return "macos"
    if os.path.exists("/etc/arch-release"):
        return "arch"
    return "unknown"


def run(cmd, dry_run=False):
    print("  + " + " ".join(cmd))
    if not dry_run:
        subprocess.run(cmd, check=True)


def load_packages():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "..", "packages.json")
    with open(path) as f:
        return json.load(f)


def applies_to(entry, platform):
    return platform in entry.get("platforms", ["macos", "arch"])


def install_macos(tools, apps, dry_run):
    if not shutil.which("brew"):
        print("[ERROR] brew not found -- run install-deps.sh to install Homebrew first")
        sys.exit(1)

    taps = {app["tap"] for app in apps if "tap" in app and applies_to(app, "macos")}
    for tap in sorted(taps):
        run(["brew", "tap", tap], dry_run)

    formulae = [
        t.get("brew", t["name"])
        for t in tools
        if applies_to(t, "macos")
    ]
    if formulae:
        run(["brew", "install"] + formulae, dry_run)

    casks = [
        a.get("brew", a["name"])
        for a in apps
        if applies_to(a, "macos")
    ]
    if casks:
        run(["brew", "install", "--cask"] + casks, dry_run)


def install_arch(tools, apps, dry_run):
    has_yay = bool(shutil.which("yay"))

    pacman_pkgs = []
    yay_pkgs = []

    for entry in tools + apps:
        if not applies_to(entry, "arch"):
            continue
        pkg = entry.get("pacman", entry["name"])
        if entry.get("aur", False):
            yay_pkgs.append(pkg)
        else:
            pacman_pkgs.append(pkg)

    if pacman_pkgs:
        run(["sudo", "pacman", "-S", "--needed", "--noconfirm"] + pacman_pkgs, dry_run)

    if yay_pkgs:
        if not has_yay:
            print("[ERROR] yay not found -- run install-deps.sh to install yay first")
            sys.exit(1)
        run(["yay", "-S", "--needed", "--noconfirm"] + yay_pkgs, dry_run)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["macos", "arch"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plat = args.platform or detect_platform()
    if plat == "unknown":
        print("[ERROR] Could not detect platform. Use --platform macos|arch")
        sys.exit(1)

    print(f"[packages] platform: {plat}" + (" (dry-run)" if args.dry_run else ""))

    data = load_packages()
    tools = data.get("tools", [])
    apps = data.get("apps", [])

    if plat == "macos":
        install_macos(tools, apps, args.dry_run)
    elif plat == "arch":
        install_arch(tools, apps, args.dry_run)


if __name__ == "__main__":
    main()
