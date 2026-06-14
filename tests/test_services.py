"""Tests for the service compliance checker."""

from unittest import mock

import pytest

from compliance.checks.services import (
    ServicesChecker,
    _check_service_state,
    _discover_service_files,
)
from compliance.schema import resolve_compliance_profile


class TestServiceDiscovery:
    def test_discovers_service_files(self, temp_dir, sample_host_config):
        """Should find .service files in enabled stow packages."""
        repo = temp_dir / "repo"
        pkg = repo / "dot_home"
        svc_dir = pkg / ".config" / "systemd" / "user"
        svc_dir.mkdir(parents=True)
        (svc_dir / "mpris-proxy.service").write_text("[Unit]\nDescription=Test\n")

        services = _discover_service_files(repo, sample_host_config)
        assert len(services) >= 1
        assert any("mpris-proxy.service" in s[1] for s in services)

    def test_empty_packages(self, temp_dir, sample_host_config):
        """Should return empty list when no services exist."""
        repo = temp_dir / "repo"
        repo.mkdir()
        services = _discover_service_files(repo, {"packages": {"public": []}})
        assert services == []


class TestServiceState:
    def test_enabled_active_passes(self):
        """Enabled + active service with default policy should pass."""
        with mock.patch(
            "compliance.checks.services._run_systemctl",
            side_effect=[
                ("enabled", 0),   # is-enabled
                ("active", 0),    # is-active
                ("", 0),          # show Type (not needed)
            ],
        ):
            findings = _check_service_state("test.service", "user")
        assert len(findings) == 1
        assert findings[0].kind == "ok"

    def test_disabled_when_expected_enabled(self):
        """Disabled service should produce a finding."""
        with mock.patch(
            "compliance.checks.services._run_systemctl",
            side_effect=[
                ("disabled", 1),  # is-enabled
                ("inactive", 3),  # is-active
                ("", 0),          # show Type
            ],
        ):
            findings = _check_service_state("test.service", "user")
        assert any(f.kind == "disabled" for f in findings)

    def test_oneshot_inactive_ok(self):
        """Oneshot service that completed is informative, not a failure."""
        with mock.patch(
            "compliance.checks.services._run_systemctl",
            side_effect=[
                ("enabled", 0),    # is-enabled
                ("inactive", 3),   # is-active
                ("Type=oneshot", 0),  # show Type
            ],
        ):
            findings = _check_service_state(
                "test.service", "user",
                policy={"expectedEnabled": True, "expectedActive": True, "severity": "expected"},
            )
        # Should have an inactive_oneshot finding, not inactive
        kinds = {f.kind for f in findings}
        assert "inactive_oneshot" in kinds
        assert "inactive" not in kinds

    def test_not_found_service(self):
        """Not-found service should produce a finding."""
        with mock.patch(
            "compliance.checks.services._run_systemctl",
            return_value=("not-found", 4),
        ):
            findings = _check_service_state("missing.service", "user")
        assert any(f.kind == "not_found" for f in findings)


class TestServicesChecker:
    def test_no_systemctl(self, temp_dir, sample_host_config, sample_packages_json):
        """When systemctl is unavailable, should return unknown."""
        profile = resolve_compliance_profile(sample_host_config)
        args = mock.Mock()
        args.quick = False
        args.pre = True
        args.post = False

        with mock.patch(
            "compliance.checks.services._systemctl_available",
            return_value=False,
        ):
            checker = ServicesChecker(
                sample_host_config, sample_packages_json, profile, temp_dir, args,
            )
            report = checker.run()

        assert report.status == "unknown"

    def test_no_services_discovered(self, temp_dir, sample_host_config, sample_packages_json):
        """When no .service files exist, should pass."""
        profile = resolve_compliance_profile(sample_host_config)
        args = mock.Mock()
        args.quick = False
        args.pre = True
        args.post = False

        repo = temp_dir / "repo"
        repo.mkdir()
        sample_host_config["packages"]["public"] = []  # No packages

        with mock.patch(
            "compliance.checks.services._systemctl_available",
            return_value=True,
        ):
            checker = ServicesChecker(
                sample_host_config, sample_packages_json, profile, repo, args,
            )
            report = checker.run()

        assert report.status == "pass"
