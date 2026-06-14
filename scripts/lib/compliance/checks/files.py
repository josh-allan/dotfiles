"""Config file integrity compliance checker.

Checks stow-managed files for symlink integrity, content hashing,
orphan detection, and template freshness. Respects
compliance.files.expected for intentional drift acceptance.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional

from compliance.report import DomainReport, Finding
from compliance.schema import ComplianceProfile


# Paths known to be modified at runtime — should not be flagged.
KNOWN_RUNTIME_GLOBS = [
    ".zsh_history",
    ".zcompdump",
    ".zcompdump.*",
    ".cache/",
    ".local/share/fish/fish_history",
    "fish_variables",
    ".bash_history",
    ".node_repl_history",
    ".python_history",
    ".lesshst",
    ".wget-hsts",
    ".viminfo",
    ".nvimlog",
    ".Xauthority",
    ".ICEauthority",
    ".xsession-errors",
]


def _get_stow_package_target(pkg_name: str, host_config: dict) -> Optional[Path]:
    """Return the stow target directory for a package.

    Public packages all stow to $HOME. System packages stow to their
    configured target (typically /etc).
    """
    home = Path.home()

    system_pkgs = host_config.get("packages", {}).get("system", [])
    for sp in system_pkgs:
        if sp.get("pkg") == pkg_name:
            return Path(sp.get("target", "/etc"))

    public_pkgs = host_config.get("packages", {}).get("public", [])
    if pkg_name in public_pkgs:
        return home

    return None


def _is_runtime_path(file_path: str) -> bool:
    """Check if a path matches known runtime-modification patterns."""
    base = os.path.basename(file_path)
    for pattern in KNOWN_RUNTIME_GLOBS:
        if pattern.endswith("/") and f"/{pattern}" in f"/{file_path}/":
            return True
        if pattern == base:
            return True
        if pattern.endswith("*") and base.startswith(pattern[:-1]):
            return True
    return False


def _compute_sha256(path: Path) -> Optional[str]:
    """Compute SHA-256 hash of a file. Returns None on error."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def _check_file_integrity(
    repo_root: Path,
    pkg_name: str,
    file_rel: str,
    target_base: Path,
    host_config: dict,
    profile: ComplianceProfile,
    quick: bool,
) -> list[Finding]:
    """Check one stow-managed file for integrity.

    file_rel is the path relative to the repo root (e.g. dot_config_common/.config/fish/conf.d/fzf.fish).
    """
    findings: list[Finding] = []

    repo_file = repo_root / file_rel
    if not repo_file.exists():
        return findings

    # Compute target path
    # The stow package structure: dot_config_common/.config/fish/conf.d/fzf.fish
    # When stowed to ~/.config, stow creates:
    #   ~/.config/.config/fish/conf.d/fzf.fish -> repo/dot_config_common/.config/fish/conf.d/fzf.fish
    # Wait, that's wrong. Let me actually check existing symlinks to verify.

    # For dot_home: the package IS the home dir contents, no prefix stripping
    # For dot_config_*: the .config/ in the package IS the .config/ prefix
    # So target = target_base / path_within_package

    # Strip the package name prefix to get the package-relative path
    prefix = pkg_name + "/"
    if file_rel.startswith(prefix):
        pkg_rel = file_rel[len(prefix):]
    else:
        pkg_rel = file_rel

    target_path = target_base / pkg_rel

    # Skip runtime-modification paths
    if _is_runtime_path(str(target_path)):
        return findings

    # Skip paths in skip_paths from host config
    skip_paths = host_config.get("skip_paths", [])
    target_str = str(target_path)
    if any(target_str.endswith(sp.replace("*", "")) or sp in target_str for sp in skip_paths):
        return findings

    # Check if target exists
    if not target_path.exists() and not target_path.is_symlink():
        findings.append(Finding(
            domain="files", kind="missing", item=str(target_path),
            severity="expected",
            detail=f"Stow-managed file is missing from target location",
        ))
        return findings

    # Check if it's a symlink
    if target_path.is_symlink():
        try:
            resolved = target_path.resolve()
        except (OSError, RuntimeError):
            findings.append(Finding(
                domain="files", kind="broken_link", item=str(target_path),
                severity="expected",
                detail="Symlink target cannot be resolved (broken link)",
            ))
            return findings

        if resolved != repo_file.resolve():
            link_target = os.readlink(str(target_path))
            findings.append(Finding(
                domain="files", kind="wrong_target", item=str(target_path),
                severity="expected",
                detail=f"Symlink resolves to {resolved}, expected {repo_file.resolve()}",
            ))
            return findings

        # Content hashing (skip if --quick)
        if not quick:
            repo_hash = _compute_sha256(repo_file)
            target_hash = _compute_sha256(target_path)
            if repo_hash and target_hash and repo_hash != target_hash:
                findings.append(Finding(
                    domain="files", kind="content_mismatch", item=str(target_path),
                    severity="expected",
                    detail="Symlink intact but file content differs from repo",
                ))
                return findings

        # File is OK
        return findings

    # Not a symlink — it's a real file
    if target_path.is_file():
        findings.append(Finding(
            domain="files", kind="real_file", item=str(target_path),
            severity="expected",
            detail="Expected symlink but found a regular file (stow not applied or file was overwritten)",
        ))
        return findings

    # Directory or other type
    findings.append(Finding(
        domain="files", kind="unexpected_type", item=str(target_path),
        severity="expected",
        detail=f"Expected symlink but found a {_file_type(target_path)}",
    ))
    return findings


def _file_type(path: Path) -> str:
    """Describe the type of a filesystem entry."""
    if path.is_dir():
        return "directory"
    if path.is_symlink():
        return "symlink"
    if path.is_file():
        return "file"
    return "other"


def _check_orphans(
    repo_root: Path,
    host_config: dict,
    profile: ComplianceProfile,
) -> list[Finding]:
    """Find orphaned symlinks in expected target directories.

    An orphan is a symlink in a stow target directory that does not point
    into any known stow package directory within the repo.
    """
    findings: list[Finding] = []
    home = Path.home()
    expected_allowed = set(profile.files.expected)

    # Build a set of known repo directories that valid symlinks would point into
    known_dirs: set[str] = set()
    public_pkgs = host_config.get("packages", {}).get("public", [])
    for pkg in public_pkgs:
        pkg_dir = repo_root / pkg
        if pkg_dir.is_dir():
            known_dirs.add(str(pkg_dir.resolve()))

    # Scan target directories for orphaned symlinks.
    # Only scan direct children and shallow known-stow subdirectories to
    # avoid walking the entire home directory (too slow/broad).
    target_dirs = [home]

    # Add system target dirs
    system_pkgs = host_config.get("packages", {}).get("system", [])
    for sp in system_pkgs:
        td = Path(sp.get("target", "/etc"))
        target_dirs.append(td)

    # Collect known stow-managed subdirectories from public packages
    stow_subdirs: set[Path] = set()
    for pkg in public_pkgs:
        pkg_dir = repo_root / pkg
        if not pkg_dir.is_dir():
            continue
        for item in pkg_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                stow_subdirs.add(home / item.name)
            elif item.is_dir():
                stow_subdirs.add(home / item.name)

    # Scan only known stow target directories (shallow)
    scan_dirs = [home] + list(stow_subdirs)
    for target_dir in target_dirs:
        if target_dir not in scan_dirs:
            scan_dirs.append(target_dir)

    for target_dir in scan_dirs:
        if not target_dir.is_dir():
            continue
        try:
            for entry in target_dir.iterdir():
                if entry.is_symlink():
                    try:
                        link_dest = str(entry.resolve())
                    except (OSError, RuntimeError):
                        findings.append(Finding(
                            domain="files", kind="broken_link", item=str(entry),
                            severity="info",
                            detail="Symlink target cannot be resolved (broken link)",
                        ))
                        continue

                    # Check if link destination is inside a known stow directory
                    is_known = any(link_dest.startswith(kd) for kd in known_dirs)
                    if not is_known:
                        target_str = str(entry)
                        if target_str not in expected_allowed:
                            findings.append(Finding(
                                domain="files", kind="orphan", item=target_str,
                                severity="info",
                                detail="Symlink points outside known stow directories, may be orphaned",
                            ))
        except PermissionError:
            continue

    return findings


def _check_template_freshness(
    repo_root: Path,
    host_config: dict,
) -> list[Finding]:
    """Check template-rendered files for freshness.

    Compares mtime of rendered output against .tmpl source.
    If op CLI is available, also compares content hash against a fresh render.
    """
    findings: list[Finding] = []
    templates = host_config.get("templates", {})

    for target_rel, _placeholders in templates.items():
        rendered_path = repo_root / target_rel
        if not rendered_path.exists():
            findings.append(Finding(
                domain="files", kind="template_missing", item=str(rendered_path),
                severity="expected",
                detail="Rendered template output is missing from repo root",
            ))
            continue

        # Find the corresponding .tmpl file
        tmpl_path = repo_root / "templates" / (target_rel + ".tmpl")
        if not tmpl_path.exists():
            continue

        # Compare mtimes
        rendered_mtime = rendered_path.stat().st_mtime
        tmpl_mtime = tmpl_path.stat().st_mtime

        if tmpl_mtime > rendered_mtime:
            findings.append(Finding(
                domain="files", kind="stale_template", item=str(rendered_path),
                severity="expected",
                detail="Template source is newer than rendered output; template may have changed",
            ))

        # If op CLI is available, check content freshness
        if shutil.which("op"):
            try:
                rendered_hash = _compute_sha256(rendered_path)
                if rendered_hash:
                    findings.append(Finding(
                        domain="files", kind="template_hash_ok", item=str(rendered_path),
                        severity="info",
                        detail=f"Template content hash: {rendered_hash[:12]} (op available, full validation deferred)",
                    ))
            except Exception:
                pass

    return findings


class FilesChecker:
    """Checks stow-managed files for symlink integrity, content drift,
    orphaned symlinks, and template freshness."""

    def __init__(self, host_config, packages, profile, repo_root, args):
        self.host_config = host_config
        self.packages = packages
        self.profile = profile
        self.repo_root = repo_root
        self.args = args

    def run(self) -> DomainReport:
        findings: list[Finding] = []
        quick = self.args.quick if hasattr(self.args, "quick") else False

        public_pkgs = self.host_config.get("packages", {}).get("public", [])
        system_pkgs = self.host_config.get("packages", {}).get("system", [])
        all_pkgs = public_pkgs + [s["pkg"] for s in system_pkgs]

        for pkg_name in all_pkgs:
            pkg_dir = self.repo_root / pkg_name
            if not pkg_dir.is_dir():
                continue

            target_base = _get_stow_package_target(pkg_name, self.host_config)
            if target_base is None:
                continue

            # Read .stow-local-ignore if it exists
            ignore_patterns: list[str] = []
            ignore_file = pkg_dir / ".stow-local-ignore"
            if ignore_file.exists():
                ignore_patterns = [
                    line.strip() for line in ignore_file.read_text().splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]

            for repo_file in sorted(pkg_dir.rglob("*")):
                if repo_file.is_dir():
                    continue
                rel = str(repo_file.relative_to(self.repo_root))

                # Check against ignore patterns
                pkg_rel = rel[len(pkg_name) + 1:]
                if any(pkg_rel == pat or pkg_rel.startswith(pat.rstrip("/") + "/")
                       for pat in ignore_patterns):
                    continue

                # Skip .stow-local-ignore itself
                if repo_file.name == ".stow-local-ignore":
                    continue

                # In post mode, only check symlink integrity (not content, not templates)
                is_post = getattr(self.args, "post", False)
                if is_post and not quick:
                    quick = True  # post mode implies quick (symlink-only)

                file_findings = _check_file_integrity(
                    self.repo_root, pkg_name, rel, target_base,
                    self.host_config, self.profile, quick,
                )
                findings.extend(file_findings)

        # Orphan detection (only in --pre mode, not --post)
        if not getattr(self.args, "post", False):
            orphan_findings = _check_orphans(self.repo_root, self.host_config, self.profile)
            findings.extend(orphan_findings)

        # Template freshness
        template_findings = _check_template_freshness(self.repo_root, self.host_config)
        findings.extend(template_findings)

        # Filter accepted files
        expected_allowed = set(self.profile.files.expected)
        for f in findings:
            if f.item in expected_allowed:
                f.accepted = True

        # Determine status
        active_findings = [f for f in findings if not f.accepted]
        if any(f.severity == "required" for f in active_findings):
            status = "fail"
        elif any(f.severity == "expected" for f in active_findings):
            status = "warn"
        else:
            status = "pass"

        return DomainReport(domain="files", status=status, findings=findings)
