"""Package compliance checker.

Compares installed packages (pacman/yay on Arch, brew on macOS) against
the packages.json manifest and host-level asahi_system_packages list.
Respects compliance.packages.expected and compliance.packages.absent
for intentional drift acceptance.
"""

import subprocess
import sys
from typing import Optional

from compliance.report import DomainReport, Finding
from compliance.schema import ComplianceProfile


def _run_cmd(cmd: list[str]) -> tuple[list[str], int]:
    """Run a command and return (stdout_lines, returncode)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip().splitlines() if result.stdout.strip() else [], result.returncode
    except FileNotFoundError:
        return [], -1
    except subprocess.TimeoutExpired:
        return [], -2


def _detect_platform() -> str:
    """Return 'arch', 'macos', or 'unknown'."""
    import platform
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "arch"
    return "unknown"


def _build_manifest_sets(packages: dict, platform: str) -> tuple[set[str], set[str]]:
    """Build the set of expected package names for a platform.

    Returns (all_names, aur_names) where all_names includes everything
    expected for this platform and aur_names is the subset installed via AUR.
    """
    all_names: set[str] = set()
    aur_names: set[str] = set()

    for entry in packages.get("tools", []) + packages.get("apps", []):
        platforms = entry.get("platforms", ["macos", "arch"])
        if platform not in platforms:
            continue

        pkg_name = entry.get("pacman", entry["name"]) if platform == "arch" else entry.get("brew", entry["name"])
        all_names.add(pkg_name)

        if entry.get("aur", False):
            aur_names.add(pkg_name)

    return all_names, aur_names


def _check_arch(
    host_config: dict,
    packages: dict,
    profile: ComplianceProfile,
) -> DomainReport:
    """Run package compliance checks on Arch Linux."""
    findings: list[Finding] = []

    # Build expected sets from packages.json
    expected_all, expected_aur = _build_manifest_sets(packages, "arch")

    # Get explicitly installed packages
    installed_lines, pacman_rc = _run_cmd(["pacman", "-Qqe"])
    if pacman_rc != 0:
        return DomainReport(
            domain="packages",
            status="error",
            findings=[Finding(
                domain="packages", kind="internal",
                item="pacman -Qqe failed",
                severity="required",
                detail="Is pacman available on this system?",
            )],
        )
    installed = set(installed_lines)

    # Missing: in manifest but not installed (and not in absent list)
    absent_allowed = set(profile.packages.absent)
    missing = (expected_all - installed) - absent_allowed
    for pkg in sorted(missing):
        findings.append(Finding(
            domain="packages", kind="missing", item=pkg,
            severity="expected",
            detail=f"Package is in packages.json but not installed",
        ))

    # Extra: installed but not in manifest (and not in expected list)
    extra_allowed = set(profile.packages.expected)
    extra = (installed - expected_all) - extra_allowed
    for pkg in sorted(extra):
        findings.append(Finding(
            domain="packages", kind="extra", item=pkg,
            severity="info",
            detail=f"Package is installed but not in packages.json",
        ))

    # AUR updates
    if expected_aur:
        aur_updates_lines, yay_rc = _run_cmd(["yay", "-Qua"])
        if yay_rc == 0 and aur_updates_lines:
            aur_updates = set()
            for line in aur_updates_lines:
                name = line.split()[0] if line.strip() else ""
                if name:
                    aur_updates.add(name)
            outdated = expected_aur & aur_updates
            for pkg in sorted(outdated):
                findings.append(Finding(
                    domain="packages", kind="aur_outdated", item=pkg,
                    severity="expected",
                    detail="AUR package has an update available",
                ))

    # Asahi system packages check
    asahi_pkgs = host_config.get("asahi_system_packages", [])
    if asahi_pkgs:
        asahi_set = set(asahi_pkgs)
        asahi_missing = asahi_set - installed
        for pkg in sorted(asahi_missing):
            findings.append(Finding(
                domain="packages", kind="asahi_missing", item=pkg,
                severity="required",
                detail=f"Asahi system package is missing (critical for Asahi functionality)",
            ))
        asahi_extra = installed & asahi_set
        for pkg in sorted(asahi_extra):
            findings.append(Finding(
                domain="packages", kind="asahi_present", item=pkg,
                severity="info",
                detail=f"Asahi system package is installed",
            ))

    # Determine status
    if any(f.severity == "required" for f in findings):
        status = "fail"
    elif any(f.severity == "expected" for f in findings):
        status = "warn"
    else:
        status = "pass"

    return DomainReport(domain="packages", status=status, findings=findings)


def _check_macos(
    host_config: dict,
    packages: dict,
    profile: ComplianceProfile,
) -> DomainReport:
    """Run package compliance checks on macOS."""
    findings: list[Finding] = []

    # Build expected sets from packages.json
    expected_all, _ = _build_manifest_sets(packages, "macos")

    # Homebrew formula leaves
    leaves_lines, leaves_rc = _run_cmd(["brew", "leaves", "--installed-on-request"])
    leaves_installed: set[str] = set()
    if leaves_rc == 0:
        leaves_installed = set(leaves_lines)

    # Homebrew casks
    cask_lines, cask_rc = _run_cmd(["brew", "list", "--cask"])
    cask_installed: set[str] = set()
    if cask_rc == 0:
        cask_installed = set(cask_lines)

    installed = leaves_installed | cask_installed

    if leaves_rc != 0 and cask_rc != 0:
        return DomainReport(
            domain="packages",
            status="error",
            findings=[Finding(
                domain="packages", kind="internal",
                item="brew not available",
                severity="required",
                detail="Homebrew commands failed. Is brew installed?",
            )],
        )

    # Missing: in manifest but not installed (and not in absent list)
    absent_allowed = set(profile.packages.absent)
    missing = (expected_all - installed) - absent_allowed
    for pkg in sorted(missing):
        findings.append(Finding(
            domain="packages", kind="missing", item=pkg,
            severity="expected",
            detail=f"Package is in packages.json but not installed",
        ))

    # Extra: installed but not in manifest (and not in expected list)
    extra_allowed = set(profile.packages.expected)
    extra = (installed - expected_all) - extra_allowed
    for pkg in sorted(extra):
        findings.append(Finding(
            domain="packages", kind="extra", item=pkg,
            severity="info",
            detail=f"Package is installed but not in packages.json",
        ))

    # Determine status
    if any(f.severity == "required" for f in findings):
        status = "fail"
    elif any(f.severity == "expected" for f in findings):
        status = "warn"
    else:
        status = "pass"

    return DomainReport(domain="packages", status=status, findings=findings)


class PackagesChecker:
    """Checks installed packages against packages.json manifest."""

    def __init__(self, host_config, packages, profile, repo_root, args):
        self.host_config = host_config
        self.packages = packages
        self.profile = profile
        self.repo_root = repo_root
        self.args = args

    def run(self) -> DomainReport:
        platform = _detect_platform()

        if platform == "arch":
            return _check_arch(self.host_config, self.packages, self.profile)
        elif platform == "macos":
            return _check_macos(self.host_config, self.packages, self.profile)
        else:
            return DomainReport(
                domain="packages",
                status="unknown",
                findings=[Finding(
                    domain="packages", kind="internal",
                    item=f"unsupported platform: {platform}",
                    severity="required",
                    detail="Only Arch Linux and macOS are supported",
                )],
            )
