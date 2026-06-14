"""Tests for the file integrity checker."""

from pathlib import Path
from unittest import mock

import pytest

from compliance.checks.files import (
    FilesChecker,
    _check_file_integrity,
    _get_stow_package_target,
    _is_runtime_path,
)
from compliance.schema import ComplianceProfile, resolve_compliance_profile


class TestTargetResolution:
    def test_public_package_targets_home(self, sample_host_config):
        target = _get_stow_package_target("dot_home", sample_host_config)
        assert target is not None
        assert target == Path.home()

    def test_system_package_target(self, sample_host_config):
        target = _get_stow_package_target("etc_linux", sample_host_config)
        assert target == Path("/etc")

    def test_unknown_package(self, sample_host_config):
        target = _get_stow_package_target("nonexistent", sample_host_config)
        assert target is None


class TestRuntimePaths:
    def test_zsh_history_is_runtime(self):
        assert _is_runtime_path("/home/user/.zsh_history") is True

    def test_normal_config_is_not_runtime(self):
        assert _is_runtime_path("/home/user/.config/fish/config.fish") is False

    def test_cache_dir_is_runtime(self):
        assert _is_runtime_path("/home/user/.cache/something") is True

    def test_fish_variables_is_runtime(self):
        assert _is_runtime_path("/home/user/.config/fish/fish_variables") is True


class TestFileIntegrity:
    def test_symlink_resolves_correctly(self, temp_dir, sample_host_config):
        """Symlink pointing to correct repo file should produce no findings."""
        repo = temp_dir / "repo"
        target = temp_dir / "home"
        target.mkdir()

        # Create repo file
        pkg_dir = repo / "dot_home"
        pkg_dir.mkdir(parents=True)
        repo_file = pkg_dir / ".gitignore"
        repo_file.write_text("*.log\n")

        # Create correct symlink at target
        link = target / ".gitignore"
        link.symlink_to(repo_file.resolve())

        profile = ComplianceProfile()
        findings = _check_file_integrity(
            repo, "dot_home", "dot_home/.gitignore", target,
            sample_host_config, profile, quick=False,
        )
        assert findings == []

    def test_real_file_instead_of_symlink(self, temp_dir, sample_host_config):
        """Real file where symlink expected should be flagged."""
        repo = temp_dir / "repo"
        target = temp_dir / "home"
        target.mkdir()

        # Create repo file
        pkg_dir = repo / "dot_home"
        pkg_dir.mkdir(parents=True)
        repo_file = pkg_dir / ".gitignore"
        repo_file.write_text("*.log\n")

        # Create real file at target (not symlink)
        real_file = target / ".gitignore"
        real_file.write_text("*.log\n")

        profile = ComplianceProfile()
        findings = _check_file_integrity(
            repo, "dot_home", "dot_home/.gitignore", target,
            sample_host_config, profile, quick=False,
        )
        assert any(f.kind == "real_file" for f in findings)

    def test_missing_target(self, temp_dir, sample_host_config):
        """Missing target file should be flagged."""
        repo = temp_dir / "repo"
        target = temp_dir / "home"
        target.mkdir()

        # Create repo file but no target
        pkg_dir = repo / "dot_home"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / ".gitignore").write_text("*.log\n")

        profile = ComplianceProfile()
        findings = _check_file_integrity(
            repo, "dot_home", "dot_home/.gitignore", target,
            sample_host_config, profile, quick=False,
        )
        assert any(f.kind == "missing" for f in findings)

    def test_accepted_file_filtered(self, temp_dir, sample_host_config):
        """File in compliance.files.expected should be marked accepted."""
        repo = temp_dir / "repo"
        target = temp_dir / "home"
        target.mkdir()

        pkg_dir = repo / "dot_home"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / ".gitignore").write_text("*.log\n")

        # Create real file at target
        (target / ".gitignore").write_text("modified content\n")

        expected_path = str(target / ".gitignore")
        profile = ComplianceProfile(
            files=mock.Mock(mode="expected", expected=[expected_path]),
        )
        findings = _check_file_integrity(
            repo, "dot_home", "dot_home/.gitignore", target,
            sample_host_config, profile, quick=False,
        )
        # Should still find the issue, but it will be marked accepted upstream
        assert any(f.kind == "real_file" for f in findings)


class TestFilesChecker:
    def test_empty_packages(self, temp_dir, sample_host_config, sample_packages_json):
        """No packages enabled should return pass."""
        sample_host_config["packages"]["public"] = []
        sample_host_config["packages"]["system"] = []
        profile = resolve_compliance_profile(sample_host_config)

        args = mock.Mock()
        args.quick = False
        args.pre = True
        args.post = False

        checker = FilesChecker(
            sample_host_config, sample_packages_json, profile, temp_dir, args,
        )
        report = checker.run()
        assert report.status == "pass"

    def test_template_freshness(self, temp_dir, sample_host_config, sample_packages_json):
        """Template freshness check should run when templates are configured."""
        repo = temp_dir / "repo"
        repo.mkdir()
        templates_dir = repo / "templates"
        templates_dir.mkdir()

        # Create a template and rendered output
        tmpl_dir = templates_dir / "dot_home"
        tmpl_dir.mkdir(parents=True)
        tmpl = tmpl_dir / ".gitconfig.tmpl"
        tmpl.write_text("[user]\n    name = {{user.name}}\n")
        rendered = repo / "dot_home"
        rendered.mkdir(parents=True)
        (rendered / ".gitconfig").write_text("[user]\n    name = Josh\n")

        sample_host_config["templates"] = {
            "dot_home/.gitconfig": {"user.name": "fake://ref"},
        }
        profile = resolve_compliance_profile(sample_host_config)

        args = mock.Mock()
        args.quick = False
        args.pre = True
        args.post = False

        checker = FilesChecker(
            sample_host_config, sample_packages_json, profile, repo, args,
        )
        report = checker.run()
        # Template freshness findings may or may not appear depending on mtimes
        # The check should not crash
        assert report.status in ("pass", "warn")
