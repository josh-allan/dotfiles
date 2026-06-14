#!/usr/bin/env python3
"""Compliance checker orchestrator.

Entry point for check-compliance.sh. Parses CLI flags, loads the host
config and compliance profile, dispatches domain checks, aggregates
findings, handles --accept write-back, formats reports, persists state,
and exits with the appropriate code.

Usage:
    python3 -m scripts.lib.compliance.checker \\
        --host-config hosts/josh-desktop.json \\
        --packages-json packages.json \\
        --repo-root . \\
        [--pre | --post] [--json] [--quick] [--accept ...]
"""

import argparse
import json
import os
import sys
from pathlib import Path

_LIB_DIR = str(Path(__file__).resolve().parents[1])
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# Ensure repo root is on sys.path so we can import scripts.*
_REPO_ROOT = str(Path(__file__).resolve().parents[4])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from compliance.schema import (  # noqa: E402
    ComplianceProfile,
    load_and_validate_all,
    resolve_compliance_profile,
)
from compliance.report import (  # noqa: E402
    ComplianceReport,
    DomainReport,
    Finding,
    format_json_report,
    format_markdown_report,
    persist_reports,
)

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dotfiles compliance checker — detect configuration drift.",
    )
    parser.add_argument(
        "--host-config",
        required=True,
        help="Path to host config JSON (e.g. hosts/josh-desktop.json)",
    )
    parser.add_argument(
        "--packages-json",
        required=True,
        help="Path to packages.json",
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        help="Path to the dotfiles repository root",
    )

    # Modes
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pre", action="store_true", default=True,
                      help="Pre-sync mode: full checks before stow (default)")
    mode.add_argument("--post", action="store_true",
                      help="Post-sync mode: symlink-only verification after stow")

    # Domain filters
    parser.add_argument("--packages-only", action="store_true",
                        help="Run only package compliance checks")
    parser.add_argument("--services-only", action="store_true",
                        help="Run only service state checks")
    parser.add_argument("--files-only", action="store_true",
                        help="Run only file integrity checks")

    # Output
    parser.add_argument("--json", action="store_true",
                        help="Output only JSON (no Markdown on stdout)")
    parser.add_argument("--quick", action="store_true",
                        help="Skip content hashing and template freshness checks")

    # Acceptance
    parser.add_argument(
        "--accept",
        action="append",
        default=[],
        metavar="TYPE:DOMAIN:ID",
        help="Accept a drift item (repeatable). "
             "Formats: pkg:extra:<name>, pkg:missing:<name>, "
             "file:modified:<path>, file:orphan:<path>",
    )

    return parser.parse_args(argv)

def _run_domain_check(
    domain: str,
    host_config: dict,
    packages: dict,
    profile: ComplianceProfile,
    repo_root: Path,
    args: argparse.Namespace,
) -> DomainReport:
    """Run a single domain check. Returns a DomainReport with status 'skipped'
    if the domain is off in the profile or the checker module is unavailable."""
    profile_mode = {
        "packages": profile.packages.mode,
        "services": profile.services.mode,
        "files": profile.files.mode,
    }.get(domain, "off")

    if profile_mode == "off":
        return DomainReport(domain=domain, status="skipped")

    # Try to import the domain checker module
    module_name = f"compliance.checks.{domain}"
    try:
        import importlib
        mod = importlib.import_module(module_name)
        checker_cls = getattr(mod, f"{domain.title()}Checker", None)
        if checker_cls is None:
            return DomainReport(
                domain=domain,
                status="error",
                findings=[Finding(
                    domain=domain, kind="internal",
                    item=f"Checker class not found in {module_name}",
                    severity="required", detail="Phase implementation missing",
                )],
            )
        checker = checker_cls(host_config, packages, profile, repo_root, args)
        return checker.run()
    except ImportError:
        return DomainReport(
            domain=domain,
            status="error",
            findings=[Finding(
                domain=domain, kind="internal",
                item=f"Module {module_name} not implemented yet",
                severity="required", detail="Will be implemented in later phases",
            )],
        )

def _apply_accept_items(
    accept_args: list[str],
    host_config_path: str,
    host_config: dict,
) -> list[str]:
    """Parse --accept flags and write back to the host config JSON.

    Returns a list of acceptance descriptions for the report.
    Only writes if at least one valid --accept flag is present.
    """
    if not accept_args:
        return []

    accepted = []
    modified = False
    # Ensure compliance section exists
    if "compliance" not in host_config:
        host_config["compliance"] = {"schemaVersion": 1}
    c = host_config["compliance"]

    for arg in accept_args:
        parts = arg.split(":", 2)
        if len(parts) != 3:
            print(f"ERROR: invalid --accept format: '{arg}' (expected TYPE:DOMAIN:ID)", file=sys.stderr)
            sys.exit(2)

        typ, domain, item_id = parts

        if typ == "pkg":
            if domain == "extra":
                c.setdefault("packages", {}).setdefault("expected", [])
                if item_id not in c["packages"]["expected"]:
                    c["packages"]["expected"].append(item_id)
                    modified = True
                    accepted.append(f"pkg:extra:{item_id}")
                else:
                    print(f"NOTE: pkg:extra:{item_id} already in expected list, skipping.", file=sys.stderr)
            elif domain == "missing":
                c.setdefault("packages", {}).setdefault("absent", [])
                if item_id not in c["packages"]["absent"]:
                    c["packages"]["absent"].append(item_id)
                    modified = True
                    accepted.append(f"pkg:missing:{item_id}")
                else:
                    print(f"NOTE: pkg:missing:{item_id} already in absent list, skipping.", file=sys.stderr)
            else:
                print(f"ERROR: unknown package domain '{domain}' for --accept", file=sys.stderr)
                sys.exit(2)

        elif typ == "file":
            if domain in ("modified", "orphan"):
                c.setdefault("files", {}).setdefault("expected", [])
                if item_id not in c["files"]["expected"]:
                    c["files"]["expected"].append(item_id)
                    modified = True
                    accepted.append(f"file:{domain}:{item_id}")
                else:
                    print(f"NOTE: file:{domain}:{item_id} already in expected list, skipping.", file=sys.stderr)
            else:
                print(f"ERROR: unknown file domain '{domain}' for --accept", file=sys.stderr)
                sys.exit(2)

        else:
            print(f"ERROR: unknown type '{typ}' for --accept (expected pkg or file)", file=sys.stderr)
            sys.exit(2)

    if modified:
        with open(host_config_path, "w") as f:
            json.dump(host_config, f, indent=2)
            f.write("\n")
        host_name = os.path.basename(host_config_path)
        print(f"Accepted {len(accepted)} item(s). Updated {host_name}.", file=sys.stderr)
        print("Reminder: commit the updated host config.", file=sys.stderr)

    return accepted

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    # Load configurations
    host_config, packages, repo_root = load_and_validate_all(
        args.host_config, args.packages_json, args.repo_root,
    )
    profile = resolve_compliance_profile(host_config)
    hostname = os.path.splitext(os.path.basename(args.host_config))[0]

    # Determine mode
    if args.post:
        args.pre = False

    # Determine which domains to check
    all_domains = ["packages", "services", "files"]
    if args.packages_only:
        domains = ["packages"]
    elif args.services_only:
        domains = ["services"]
    elif args.files_only:
        domains = ["files"]
    else:
        domains = all_domains

    # Run domain checks
    domain_reports: list[DomainReport] = []
    for domain in domains:
        dr = _run_domain_check(domain, host_config, packages, profile, repo_root, args)
        domain_reports.append(dr)

    # Handle --accept (Phase 6: write-back)
    accept_items = _apply_accept_items(args.accept, args.host_config, host_config)

    # Build report
    report = ComplianceReport(
        host=hostname,
        domains=domain_reports,
        accept_items=accept_items,
    )
    report.exit_code = report.compute_exit_code()

    # Persist
    persist_reports(report)

    # Output
    json_output = format_json_report(report, accept_items)
    if args.json:
        print(json_output)
    else:
        print(format_markdown_report(report))

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
