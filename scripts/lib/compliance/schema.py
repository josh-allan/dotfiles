"""Schema loading, validation, and compliance profile resolution."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@dataclass
class PackageComplianceConfig:
    mode: str = "expected"  # "required" | "expected" | "off"
    expected: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)


@dataclass
class ServiceUnitPolicy:
    unit: str
    expected_enabled: bool = True
    expected_active: Optional[bool] = None
    severity: str = "expected"  # "required" | "expected"


@dataclass
class ServiceComplianceConfig:
    mode: str = "off"  # "required" | "expected" | "off"
    units: list[ServiceUnitPolicy] = field(default_factory=list)


@dataclass
class FileComplianceConfig:
    mode: str = "expected"  # "required" | "expected" | "off"
    expected: list[str] = field(default_factory=list)


@dataclass
class ComplianceProfile:
    """Resolved compliance profile for a host."""
    schema_version: int = 1
    packages: PackageComplianceConfig = field(default_factory=PackageComplianceConfig)
    services: ServiceComplianceConfig = field(default_factory=ServiceComplianceConfig)
    files: FileComplianceConfig = field(default_factory=FileComplianceConfig)


def load_schema(path: str) -> dict:
    """Load a JSON Schema file."""
    with open(path, "r") as f:
        import json
        return json.load(f)


def validate_against_schema(instance: dict, schema: dict, label: str = "config") -> None:
    """Validate an instance against a JSON Schema. No-op if jsonschema unavailable."""
    if not HAS_JSONSCHEMA:
        return
    jsonschema.validate(instance=instance, schema=schema)


def load_json(path: str) -> dict:
    """Load and parse a JSON file."""
    import json
    with open(path, "r") as f:
        return json.load(f)


def load_host_config(host_config_path: str) -> dict:
    """Load a host config JSON file."""
    config = load_json(host_config_path)
    return config


def load_packages_json(packages_path: str) -> dict:
    """Load packages.json."""
    return load_json(packages_path)


def resolve_compliance_profile(host_config: dict) -> ComplianceProfile:
    """Extract and merge the compliance section from a host config.

    Returns a ComplianceProfile with defaults applied for any missing
    sections or fields.
    """
    raw = host_config.get("compliance", {})

    if not raw:
        return ComplianceProfile()

    schema_version = raw.get("schemaVersion", 1)

    # Packages
    pkg_raw = raw.get("packages", {})
    packages = PackageComplianceConfig(
        mode=pkg_raw.get("mode", "expected"),
        expected=pkg_raw.get("expected", []),
        absent=pkg_raw.get("absent", []),
    )

    # Services
    svc_raw = raw.get("services", {})
    units = []
    for u in svc_raw.get("units", []):
        units.append(ServiceUnitPolicy(
            unit=u["unit"],
            expected_enabled=u.get("expectedEnabled", True),
            expected_active=u.get("expectedActive"),
            severity=u.get("severity", "expected"),
        ))
    services = ServiceComplianceConfig(
        mode=svc_raw.get("mode", "off"),
        units=units,
    )

    # Files
    file_raw = raw.get("files", {})
    files = FileComplianceConfig(
        mode=file_raw.get("mode", "expected"),
        expected=file_raw.get("expected", []),
    )

    return ComplianceProfile(
        schema_version=schema_version,
        packages=packages,
        services=services,
        files=files,
    )


def load_and_validate_all(
    host_config_path: str,
    packages_json_path: str,
    repo_root: str,
) -> tuple[dict, dict, Path]:
    """Load host config and packages.json, optionally validate against schemas.

    Returns (host_config, packages, repo_root_path).
    Schema validation is best-effort; failures print warnings to stderr.
    """
    import sys

    host_config = load_host_config(host_config_path)
    packages = load_packages_json(packages_json_path)
    repo = Path(repo_root).resolve()

    if HAS_JSONSCHEMA:
        schema_dir = repo / "schemas"
        host_schema_path = schema_dir / "host-config.schema.json"
        pkg_schema_path = schema_dir / "packages.schema.json"

        if host_schema_path.exists():
            try:
                host_schema = load_schema(str(host_schema_path))
                validate_against_schema(host_config, host_schema,
                                        label=host_config_path)
            except Exception as e:
                print(f"WARNING: host config schema validation: {e}", file=sys.stderr)

        if pkg_schema_path.exists():
            try:
                pkg_schema = load_schema(str(pkg_schema_path))
                validate_against_schema(packages, pkg_schema,
                                        label=packages_json_path)
            except Exception as e:
                print(f"WARNING: packages.json schema validation: {e}", file=sys.stderr)

    return host_config, packages, repo
