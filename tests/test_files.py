"""Tests for the file integrity checker."""

import os
from pathlib import Path
from unittest import mock


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

    def test_accepted_real_file_is_marked_accepted(
        self, temp_dir, sample_host_config, sample_packages_json,
    ):
        """A real file listed in compliance.files.expected is reported but accepted."""
        repo = temp_dir / "repo"
        home = temp_dir / "home"
        home.mkdir()
        pkg_dir = repo / "dot_home"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / ".gitignore").write_text("*.log\n")
        (home / ".gitignore").write_text("modified content\n")

        sample_host_config["packages"] = {"public": ["dot_home"]}
        sample_host_config["compliance"]["files"]["expected"] = [str(home / ".gitignore")]
        profile = resolve_compliance_profile(sample_host_config)
        args = mock.Mock(quick=False, pre=True, post=False)

        with mock.patch("pathlib.Path.home", return_value=home):
            report = FilesChecker(
                sample_host_config, sample_packages_json, profile, repo, args,
            ).run()

        real_file = [f for f in report.findings if f.kind == "real_file"]
        assert [f.accepted for f in real_file] == [True]
        assert report.status == "pass"


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

    @staticmethod
    def _template_repo(temp_dir, sample_host_config):
        """Lay out one template and its rendered output; return (repo, tmpl, rendered)."""
        repo = temp_dir / "repo"
        tmpl = repo / "templates" / "dot_home" / ".gitconfig.tmpl"
        tmpl.parent.mkdir(parents=True)
        tmpl.write_text("[user]\n    name = {{user.name}}\n")
        rendered = repo / "dot_home" / ".gitconfig"
        rendered.parent.mkdir(parents=True)
        rendered.write_text("[user]\n    name = Josh\n")
        (temp_dir / "home").mkdir()

        sample_host_config["packages"] = {"public": []}
        sample_host_config["templates"] = {
            "dot_home/.gitconfig": {"user.name": "fake://ref"},
        }
        return repo, tmpl, rendered

    @staticmethod
    def _stale_findings(repo, temp_dir, sample_host_config, sample_packages_json):
        profile = resolve_compliance_profile(sample_host_config)
        args = mock.Mock(quick=False, pre=True, post=False)
        with mock.patch("pathlib.Path.home", return_value=temp_dir / "home"):
            report = FilesChecker(
                sample_host_config, sample_packages_json, profile, repo, args,
            ).run()
        return [f for f in report.findings if f.kind == "stale_template"]

    def test_rendered_newer_than_template_is_fresh(
        self, temp_dir, sample_host_config, sample_packages_json,
    ):
        repo, tmpl, rendered = self._template_repo(temp_dir, sample_host_config)
        os.utime(tmpl, (1_000_000, 1_000_000))
        os.utime(rendered, (2_000_000, 2_000_000))

        assert self._stale_findings(repo, temp_dir, sample_host_config, sample_packages_json) == []

    def test_template_newer_than_rendered_is_stale(
        self, temp_dir, sample_host_config, sample_packages_json,
    ):
        repo, tmpl, rendered = self._template_repo(temp_dir, sample_host_config)
        os.utime(rendered, (1_000_000, 1_000_000))
        os.utime(tmpl, (2_000_000, 2_000_000))

        stale = self._stale_findings(repo, temp_dir, sample_host_config, sample_packages_json)
        assert [f.item for f in stale] == [str(rendered)]
