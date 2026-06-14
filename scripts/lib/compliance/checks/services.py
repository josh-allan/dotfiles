"""Systemd service state compliance checker.

Walks stow packages enabled for this host, discovers .service files,
queries systemctl for is-enabled/is-active state, and compares against
the compliance.services.units policy.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from compliance.report import DomainReport, Finding
from compliance.schema import ComplianceProfile


def _run_systemctl(args: list[str], user: bool = False) -> tuple[str, int]:
    """Run systemctl and return (stdout_stripped, returncode)."""
    cmd = ["systemctl"]
    if user:
        cmd.append("--user")
    cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        return "", -1
    except subprocess.TimeoutExpired:
        return "", -2


def _discover_service_files(repo_root: Path, host_config: dict) -> list[tuple[str, str]]:
    """Walk stow packages enabled for this host and find .service files.

    Returns a list of (relative_path, unit_name) tuples.
    Determines user vs system based on the package destination path.
    """
    public_pkgs = host_config.get("packages", {}).get("public", [])
    system_pkgs = [s["pkg"] for s in host_config.get("packages", {}).get("system", [])]
    all_pkgs = set(public_pkgs + system_pkgs)

    services: list[tuple[str, str]] = []

    for pkg_name in sorted(all_pkgs):
        pkg_dir = repo_root / pkg_name
        if not pkg_dir.is_dir():
            continue

        for service_file in sorted(pkg_dir.rglob("*.service")):
            rel = str(service_file.relative_to(repo_root))
            unit_name = service_file.name

            # Determine scope: user vs system
            rel_lower = rel.lower()
            if ".config/systemd/user" in rel_lower:
                scope = "user"
            elif "etc/systemd/system" in rel_lower or pkg_name.startswith("etc_"):
                scope = "system"
            elif "home/" in rel_lower and ".config/systemd/user" in rel_lower:
                scope = "user"
            else:
                # Default: assume user service for dot_* packages, system for etc_*
                if pkg_name.startswith("etc_"):
                    scope = "system"
                else:
                    scope = "user"

            services.append((f"{scope}:{unit_name}", unit_name))

    return services


def _check_service_state(
    unit_name: str,
    scope: str,
    policy: Optional[dict] = None,
) -> list[Finding]:
    """Check one service unit against policy and return findings."""
    findings: list[Finding] = []
    user = (scope == "user")

    # Check if XDG_RUNTIME_DIR is needed for user services
    if user and not os.environ.get("XDG_RUNTIME_DIR"):
        return [Finding(
            domain="services", kind="unknown", item=unit_name,
            severity="info",
            detail="XDG_RUNTIME_DIR not set; cannot query user services",
        )]

    expected_enabled = policy.get("expectedEnabled", True) if policy else True
    expected_active = policy.get("expectedActive") if policy else None
    severity = policy.get("severity", "expected") if policy else "expected"

    # is-enabled
    enabled_out, enabled_rc = _run_systemctl(["is-enabled", unit_name], user=user)
    enabled_state = enabled_out if enabled_rc in (0, 1) else "unknown"

    # is-active
    active_out, active_rc = _run_systemctl(["is-active", unit_name], user=user)
    active_state = active_out if active_rc in (0, 3) else "unknown"

    # Handle service not found
    if "not-found" in enabled_state.lower() or enabled_rc == 4:
        return [Finding(
            domain="services", kind="not_found", item=unit_name,
            severity=severity,
            detail=f"Service unit not loaded on this system",
        )]

    # is-enabled check
    if expected_enabled and enabled_state not in ("enabled", "enabled-runtime", "static"):
        if enabled_state == "masked":
            findings.append(Finding(
                domain="services", kind="masked", item=unit_name,
                severity=severity,
                detail=f"Service is masked (expected enabled)",
            ))
        elif enabled_state == "disabled":
            findings.append(Finding(
                domain="services", kind="disabled", item=unit_name,
                severity=severity,
                detail=f"Service is disabled (expected enabled)",
            ))
        elif enabled_state == "indirect":
            findings.append(Finding(
                domain="services", kind="indirect", item=unit_name,
                severity="info",
                detail="Service is indirectly enabled (via Another enablement)",
            ))
    elif not expected_enabled and enabled_state in ("enabled", "enabled-runtime"):
        findings.append(Finding(
            domain="services", kind="enabled_unexpected", item=unit_name,
            severity=severity,
            detail=f"Service is enabled but should not be",
        ))

    # is-active check (only if expected_active is explicitly set)
    if expected_active is True and active_state != "active":
        if active_state == "inactive":
            # Check if it's a oneshot service that completed
            is_oneshot = _is_oneshot_service(unit_name, user)
            if is_oneshot:
                findings.append(Finding(
                    domain="services", kind="inactive_oneshot", item=unit_name,
                    severity="info",
                    detail="Oneshot service completed (inactive is normal after exit)",
                ))
            else:
                findings.append(Finding(
                    domain="services", kind="inactive", item=unit_name,
                    severity=severity,
                    detail=f"Service is inactive (expected active)",
                ))
        elif active_state == "failed":
            findings.append(Finding(
                domain="services", kind="failed", item=unit_name,
                severity="required",
                detail=f"Service has failed",
            ))
    elif expected_active is False and active_state == "active":
        findings.append(Finding(
            domain="services", kind="active_unexpected", item=unit_name,
            severity=severity,
            detail=f"Service is active but should not be",
        ))

    # Transient services
    if active_state == "transient":
        findings.append(Finding(
            domain="services", kind="transient", item=unit_name,
            severity="info",
            detail="Service is transient (dynamic, not persistent)",
        ))

    if not findings:
        findings.append(Finding(
            domain="services", kind="ok", item=unit_name,
            severity="info",
            detail=f"Service state OK (enabled={enabled_state}, active={active_state})",
        ))

    return findings


def _is_oneshot_service(unit_name: str, user: bool) -> bool:
    """Check if a service is Type=oneshot."""
    out, rc = _run_systemctl(["show", "-p", "Type", unit_name], user=user)
    if rc == 0:
        return "Type=oneshot" in out
    return False


def _get_policy_for_unit(unit_name: str, profile: ComplianceProfile) -> Optional[dict]:
    """Find the unit policy from the compliance profile. Returns None if no policy."""
    for u in profile.services.units:
        if u.unit == unit_name:
            return {
                "expectedEnabled": u.expected_enabled,
                "expectedActive": u.expected_active,
                "severity": u.severity,
            }
    return None


class ServicesChecker:
    """Checks systemd service state against compliance policy."""

    def __init__(self, host_config, packages, profile, repo_root, args):
        self.host_config = host_config
        self.packages = packages
        self.profile = profile
        self.repo_root = repo_root
        self.args = args

    def run(self) -> DomainReport:
        # Check if systemctl is available
        if not _systemctl_available():
            return DomainReport(
                domain="services",
                status="unknown",
                findings=[Finding(
                    domain="services", kind="internal",
                    item="systemctl not available",
                    severity="info",
                    detail="Not a Linux system or systemd not installed",
                )],
            )

        # Discover services
        all_services = _discover_service_files(self.repo_root, self.host_config)

        if not all_services:
            return DomainReport(
                domain="services",
                status="pass",
                findings=[Finding(
                    domain="services", kind="internal",
                    item="no services discovered",
                    severity="info",
                    detail="No .service files found in enabled stow packages",
                )],
            )

        # Check each service
        findings: list[Finding] = []
        for service_key, unit_name in all_services:
            scope = service_key.split(":")[0]
            policy = _get_policy_for_unit(unit_name, self.profile)
            unit_findings = _check_service_state(unit_name, scope, policy)
            findings.extend(unit_findings)

        # Determine status
        if any(f.severity == "required" for f in findings):
            status = "fail"
        elif any(f.severity == "expected" for f in findings):
            status = "warn"
        else:
            status = "pass"

        return DomainReport(domain="services", status=status, findings=findings)


def _systemctl_available() -> bool:
    """Check if systemctl is on PATH."""
    import shutil
    return shutil.which("systemctl") is not None
