"""Tests for the compliance report formatter and --accept functionality."""

import json
from unittest import mock

import pytest

from compliance.report import (
    ComplianceReport,
    DomainReport,
    Finding,
    format_json_report,
    format_markdown_report,
    persist_reports,
)


class TestReportFormatting:
    def test_json_report_structure(self):
        """JSON report should have the expected schema."""
        report = ComplianceReport(
            host="test-host",
            domains=[
                DomainReport(
                    domain="packages",
                    status="warn",
                    findings=[
                        Finding(domain="packages", kind="extra", item="cowsay",
                                severity="info"),
                        Finding(domain="packages", kind="missing", item="bat",
                                severity="required"),
                    ],
                ),
            ],
        )
        result = json.loads(format_json_report(report))

        assert result["schemaVersion"] == 1
        assert result["host"] == "test-host"
        assert "timestamp" in result
        assert result["exitCode"] == 1
        assert result["summary"]["pass"] == 1  # info severity
        assert result["summary"]["fail"] == 1  # required severity
        assert "packages" in result["checks"]
        assert len(result["checks"]["packages"]["findings"]) == 2

    def test_markdown_report_contains_severity_labels(self):
        """Markdown report should use [REQUIRED] / [EXPECTED] / [INFO] labels."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(
                    domain="packages",
                    status="warn",
                    findings=[
                        Finding(domain="packages", kind="missing", item="git",
                                severity="required"),
                    ],
                ),
            ],
        )
        md = format_markdown_report(report)
        assert "[REQUIRED]" in md
        assert "git" in md
        assert "| packages | warn | 1 |" in md

    def test_no_emojis_in_output(self):
        """Output should not contain emoji characters."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(
                    domain="packages",
                    status="warn",
                    findings=[
                        Finding(domain="packages", kind="extra", item="cowsay",
                                severity="expected"),
                        Finding(domain="packages", kind="missing", item="bat",
                                severity="required"),
                    ],
                ),
            ],
        )
        json_out = format_json_report(report)
        md_out = format_markdown_report(report)
        for ch in ["\u274c", "\u26a0", "\u2139", "\u2705"]:
            assert ch not in json_out
            assert ch not in md_out


class TestExitCodes:
    def test_all_pass_exit_zero(self):
        """All domains passing should exit 0."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(domain="packages", status="pass"),
                DomainReport(domain="services", status="pass"),
            ],
        )
        assert report.compute_exit_code() == 0

    def test_drift_exit_one(self):
        """Required-severity finding should exit 1."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(
                    domain="packages",
                    status="fail",
                    findings=[
                        Finding(domain="packages", kind="missing", item="git",
                                severity="required"),
                    ],
                ),
            ],
        )
        assert report.compute_exit_code() == 1

    def test_error_exit_two(self):
        """Domain error status should exit 2."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(domain="packages", status="error"),
            ],
        )
        assert report.compute_exit_code() == 2

    def test_accepted_drift_does_not_cause_exit_one(self):
        """Accepted required findings should not cause exit 1."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(
                    domain="packages",
                    status="warn",
                    findings=[
                        Finding(domain="packages", kind="missing", item="git",
                                severity="required", accepted=True),
                    ],
                ),
            ],
        )
        assert report.compute_exit_code() == 0


class TestPersistence:
    def test_persist_creates_files(self, temp_dir):
        """persist_reports should create config and cache files."""
        home_mock = mock.patch("pathlib.Path.home", return_value=temp_dir)
        with home_mock:
            report = ComplianceReport(
                host="test",
                domains=[
                    DomainReport(
                        domain="packages",
                        status="warn",
                        findings=[
                            Finding(domain="packages", kind="missing", item="git",
                                    severity="required"),
                        ],
                    ),
                ],
            )
            persist_reports(report)

            config_dir = temp_dir / ".config" / "dotfiles"
            cache_dir = temp_dir / ".cache" / "dotfiles"

            assert config_dir.exists()
            assert (config_dir / "drift-report.json").exists()
            assert cache_dir.exists()

            state_path = cache_dir / "drift-state"
            assert state_path.exists()
            state_content = state_path.read_text()
            assert "pending=1" in state_content
            assert "timestamp=" in state_content


class TestSummary:
    def test_summary_counts_findings(self):
        """Summary should aggregate per-finding severity."""
        report = ComplianceReport(
            host="test",
            domains=[
                DomainReport(
                    domain="packages",
                    status="warn",
                    findings=[
                        Finding(domain="packages", kind="missing", item="a",
                                severity="required"),
                        Finding(domain="packages", kind="missing", item="b",
                                severity="required"),
                        Finding(domain="packages", kind="extra", item="c",
                                severity="expected"),
                    ],
                ),
            ],
        )
        s = report.summary
        assert s["fail"] == 2
        assert s["warn"] == 1  # expected finding + domain status
        assert s["pass"] == 0
