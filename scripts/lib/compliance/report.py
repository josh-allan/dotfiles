"""Report formatting, persistence, and state-file management."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    """A single compliance finding."""
    domain: str          # "packages" | "services" | "files"
    kind: str            # "missing" | "extra" | "disabled" | "inactive" | ...
    item: str            # Human-readable identifier
    severity: str        # "required" | "expected" | "info"
    detail: str = ""     # Additional context
    accepted: bool = False  # True if this finding is in an acceptance list


@dataclass
class DomainReport:
    """Aggregated findings for one check domain."""
    domain: str
    status: str = "pass"   # "pass" | "warn" | "fail" | "error" | "unknown" | "skipped"
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """Top-level compliance report."""
    host: str
    timestamp: str = ""
    exit_code: int = 0
    domains: list[DomainReport] = field(default_factory=list)
    accept_items: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def summary(self) -> dict:
        counts = {"pass": 0, "warn": 0, "fail": 0, "error": 0, "unknown": 0}
        for domain in self.domains:
            for f in domain.findings:
                if f.accepted:
                    continue
                if f.severity == "required":
                    counts["fail"] += 1
                elif f.severity == "expected":
                    counts["warn"] += 1
                elif f.severity == "info":
                    counts["pass"] += 1
            if domain.status == "error":
                counts["error"] += 1
            elif domain.status == "unknown":
                counts["unknown"] += 1
        return counts

    def compute_exit_code(self) -> int:
        """Derive exit code: 0=pass, 1=drift, 2=error."""
        has_error = any(d.status == "error" for d in self.domains)
        if has_error:
            return 2
        has_drift = any(
            f.severity == "required" and not f.accepted
            for d in self.domains
            for f in d.findings
        )
        if has_drift:
            return 1
        return 0


SEVERITY_LABELS = {
    "required": "REQUIRED",
    "expected": "EXPECTED",
    "info": "INFO",
}


def format_json_report(report: ComplianceReport, accept_items: Optional[list[str]] = None) -> str:
    """Produce the machine-parseable JSON report matching the schema in the plan."""
    checks = {}
    for d in report.domains:
        checks[d.domain] = {
            "status": d.status,
            "findings": [
                {
                    "kind": f.kind,
                    "item": f.item,
                    "severity": f.severity,
                    "detail": f.detail,
                    "accepted": f.accepted,
                }
                for f in d.findings
            ],
        }

    output = {
        "schemaVersion": 1,
        "host": report.host,
        "timestamp": report.timestamp,
        "exitCode": report.compute_exit_code(),
        "summary": report.summary,
        "checks": checks,
    }

    if accept_items:
        output["accepted"] = accept_items

    return json.dumps(output, indent=2)


def format_markdown_report(report: ComplianceReport) -> str:
    """Produce a human-readable Markdown summary."""
    lines = [
        f"# Compliance Report: {report.host}",
        f"Generated {report.timestamp}",
        "",
        "| Domain | Status | Findings |",
        "|--------|--------|----------|",
    ]

    for d in report.domains:
        non_accepted = [f for f in d.findings if not f.accepted]
        count = len(non_accepted)
        lines.append(f"| {d.domain} | {d.status} | {count} |")

    lines.append("")

    for d in report.domains:
        non_accepted = [f for f in d.findings if not f.accepted]
        if not non_accepted:
            continue
        lines.append(f"## {d.domain.title()}")
        for f in non_accepted:
            label = SEVERITY_LABELS.get(f.severity, f.severity.upper())
            lines.append(f"- **[{label}]** {f.kind}: {f.item}")
            if f.detail:
                lines.append(f"  {f.detail}")
        lines.append("")

    return "\n".join(lines)


def persist_reports(report: ComplianceReport) -> None:
    """Write the JSON report and lightweight state file.

    Full report: ~/.config/dotfiles/drift-report.json
    (previous rotated to drift-report.prev.json)

    Lightweight state: ~/.cache/dotfiles/drift-state
    Contains pending=<count> and timestamp=<ISO8601>
    """
    home = Path.home()

    config_dir = home / ".config" / "dotfiles"
    config_dir.mkdir(parents=True, exist_ok=True)

    report_path = config_dir / "drift-report.json"
    prev_path = config_dir / "drift-report.prev.json"

    if report_path.exists():
        try:
            report_path.rename(prev_path)
        except OSError:
            pass

    json_str = format_json_report(report)
    report_path.write_text(json_str + "\n")

    cache_dir = home / ".cache" / "dotfiles"
    cache_dir.mkdir(parents=True, exist_ok=True)

    state_path = cache_dir / "drift-state"
    s = report.summary
    pending = s.get("warn", 0) + s.get("fail", 0)
    state_path.write_text(
        f"pending={pending}\n"
        f"timestamp={report.timestamp}\n"
    )
