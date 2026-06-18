"""Tests for the package compliance checker."""

from unittest import mock

import pytest

from compliance.checks.packages import (
    PackagesChecker,
    _build_manifest_sets,
    _detect_platform,
)
from compliance.schema import resolve_compliance_profile


class TestManifestSets:
    def test_build_arch_sets(self, sample_packages_json):
        all_names, aur_names = _build_manifest_sets(sample_packages_json, "arch", "x86_64")
        assert "git" in all_names
        assert "neovim" in all_names
        assert "aws-cli" in all_names  # pacman override
        assert "lazygit" in all_names
        assert "discord" in all_names
        assert aur_names == {"lazygit", "discord", "ghostty", "balena-etcher"}

    def test_macos_platform_filter(self, sample_packages_json):
        all_names, _ = _build_manifest_sets(sample_packages_json, "macos", "x86_64")
        assert "git" in all_names
        assert "neovim" in all_names
        # blueutil is macOS-only
        assert "blueutil" in all_names
        # lazygit has aur:true but no platforms restriction — defaults to both
        # so it IS included for macOS (it's not arch-only)
        assert "lazygit" in all_names

    def test_empty_packages(self):
        all_names, aur_names = _build_manifest_sets({"tools": [], "apps": []}, "arch", "x86_64")
        assert all_names == set()
        assert aur_names == set()

    def test_arch_filter_includes_on_match(self, sample_packages_json):
        """Package tagged x86_64 should appear when running on x86_64."""
        all_names, aur_names = _build_manifest_sets(sample_packages_json, "arch", "x86_64")
        assert "balena-etcher" in all_names
        assert "balena-etcher" in aur_names

    def test_arch_filter_excludes_on_mismatch(self, sample_packages_json):
        """Package tagged x86_64 should NOT appear when running on aarch64."""
        all_names, aur_names = _build_manifest_sets(sample_packages_json, "arch", "aarch64")
        assert "balena-etcher" not in all_names
        assert "balena-etcher" not in aur_names

    def test_arch_filter_defaults_to_all(self, sample_packages_json):
        """Package with no arch field should appear on both architectures."""
        all_names_x86, _ = _build_manifest_sets(sample_packages_json, "arch", "x86_64")
        all_names_arm, _ = _build_manifest_sets(sample_packages_json, "arch", "aarch64")
        assert "git" in all_names_x86
        assert "git" in all_names_arm


class TestPackageChecker:
    @staticmethod
    def _mock_pacman_qe_qi(installed):
        """Return a side_effect for _run_cmd that returns installed for
        pacman -Qqe and rc=1 (not found) for pacman -Qi."""
        def _side_effect(cmd_args):
            cmd_str = " ".join(cmd_args)
            if "-Qi" in cmd_args:
                return ([], 1)
            return (installed, 0)
        return _side_effect

    def make_args(self, pre=True, quick=False, json=False):
        args = mock.Mock()
        args.pre = pre
        args.post = not pre
        args.quick = quick
        args.json = json
        return args

    def test_all_packages_installed(
        self, sample_host_config, sample_packages_json, mock_pacman_installed,
    ):
        """When all expected packages are present, should pass."""
        profile = resolve_compliance_profile(sample_host_config)
        args = self.make_args()

        def run_cmd_side_effect(cmd):
            if cmd[0] == "pacman":
                return (mock_pacman_installed, 0)
            if cmd[0] == "yay":
                return ([], 0)  # no AUR updates
            return ([], 0)

        with mock.patch(
            "compliance.checks.packages._run_cmd",
            side_effect=run_cmd_side_effect,
        ):
            checker = PackagesChecker(
                sample_host_config, sample_packages_json, profile, None, args,
            )
            report = checker.run()

        assert report.status == "pass"
        # Only extras should be found (base, linux, systemd)
        extras = [f for f in report.findings if f.kind == "extra"]
        assert len(extras) == 3

    def test_missing_package(
        self, sample_host_config, sample_packages_json,
    ):
        """When a package in the manifest is not installed."""
        profile = resolve_compliance_profile(sample_host_config)
        args = self.make_args()
        installed = ["git", "neovim"]  # missing aws-cli, lazygit, discord, ghostty

        with mock.patch(
            "compliance.checks.packages._run_cmd",
            side_effect=self._mock_pacman_qe_qi(installed),
        ):
            checker = PackagesChecker(
                sample_host_config, sample_packages_json, profile, None, args,
            )
            report = checker.run()

        missing = [f for f in report.findings if f.kind == "missing"]
        assert len(missing) == 4
        missing_names = {f.item for f in missing}
        assert "aws-cli" in missing_names
        assert "lazygit" in missing_names
        assert report.status == "warn"

    def test_expected_extra_filtered(
        self, sample_host_config, sample_packages_json, mock_pacman_installed,
    ):
        """Extra packages in compliance.packages.expected should be filtered."""
        sample_host_config["compliance"]["packages"]["expected"] = ["base", "linux"]
        profile = resolve_compliance_profile(sample_host_config)
        args = self.make_args()

        with mock.patch(
            "compliance.checks.packages._run_cmd",
            side_effect=self._mock_pacman_qe_qi(mock_pacman_installed),
        ):
            checker = PackagesChecker(
                sample_host_config, sample_packages_json, profile, None, args,
            )
            report = checker.run()

        extras = [f for f in report.findings if f.kind == "extra"]
        extra_names = {f.item for f in extras}
        assert "base" not in extra_names
        assert "linux" not in extra_names
        # systemd should still be there
        assert "systemd" in extra_names

    def test_absent_package_filtered(
        self, sample_host_config, sample_packages_json,
    ):
        """Missing packages in compliance.packages.absent should be filtered."""
        sample_host_config["compliance"]["packages"]["absent"] = ["lazygit"]
        profile = resolve_compliance_profile(sample_host_config)
        args = self.make_args()
        installed = ["git", "neovim", "aws-cli"]

        with mock.patch(
            "compliance.checks.packages._run_cmd",
            side_effect=self._mock_pacman_qe_qi(installed),
        ):
            checker = PackagesChecker(
                sample_host_config, sample_packages_json, profile, None, args,
            )
            report = checker.run()

        missing = [f for f in report.findings if f.kind == "missing"]
        missing_names = {f.item for f in missing}
        assert "lazygit" not in missing_names
        # discord and ghostty should still be missing
        assert "discord" in missing_names
        assert "ghostty" in missing_names

    def test_pacman_failure(self, sample_host_config, sample_packages_json):
        """When pacman fails, should return error status."""
        profile = resolve_compliance_profile(sample_host_config)
        args = self.make_args()

        with mock.patch(
            "compliance.checks.packages._run_cmd",
            return_value=([], 1),
        ):
            checker = PackagesChecker(
                sample_host_config, sample_packages_json, profile, None, args,
            )
            report = checker.run()

        assert report.status == "error"


class TestPlatformDetection:
    def test_linux_detection(self):
        with mock.patch("platform.system", return_value="Linux"):
            assert _detect_platform() == "arch"

    def test_macos_detection(self):
        with mock.patch("platform.system", return_value="Darwin"):
            assert _detect_platform() == "macos"
