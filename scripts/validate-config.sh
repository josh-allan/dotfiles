#!/usr/bin/env bash
set -euo pipefail

# validate-config.sh
# Validates prerequisites and host config before sync.
# Usage: validate-config.sh <host_config.json>

HOST_CONFIG="${1:-}"

if [[ -z "$HOST_CONFIG" ]]; then
    echo "Usage: $0 <host_config.json>" >&2
    exit 1
fi

# Check file existence before validation
if [[ ! -f "$HOST_CONFIG" ]]; then
    echo "ERROR: Config file not found: $HOST_CONFIG" >&2
    exit 1
fi

ERRORS=0

# Check prerequisites
check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $1" >&2
        ERRORS=$((ERRORS + 1))
    fi
}

check_command stow
check_command jq
check_command git

# op is only needed when templates contain 1Password references
if jq -e '.templates | keys | length > 0' "$HOST_CONFIG" >/dev/null 2>&1; then
    check_command op
fi

# Validate JSON syntax
if ! jq empty "$HOST_CONFIG" 2>/dev/null; then
    echo "ERROR: Invalid JSON in $HOST_CONFIG" >&2
    ERRORS=$((ERRORS + 1))
fi

# Validate required fields
if ! jq -e '.packages' "$HOST_CONFIG" >/dev/null 2>&1; then
    echo "ERROR: Missing required field: packages" >&2
    ERRORS=$((ERRORS + 1))
fi

# Validate .packages is an object
if ! jq -e '.packages | type == "object"' "$HOST_CONFIG" >/dev/null 2>&1; then
    echo "ERROR: .packages must be an object" >&2
    ERRORS=$((ERRORS + 1))
fi

# Validate OS value if present
os="$(jq -r '.os // empty' "$HOST_CONFIG")"
if [[ -n "$os" && "$os" != "macos" && "$os" != "linux" ]]; then
    echo "ERROR: Invalid os value: '$os'. Must be 'macos' or 'linux'." >&2
    ERRORS=$((ERRORS + 1))
fi

# JSON Schema validation (guarded: requires jsonschema CLI)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA_DIR="$REPO_ROOT/schemas"
if [[ -f "$SCHEMA_DIR/host-config.schema.json" ]] && command -v jsonschema >/dev/null 2>&1; then
    echo "Running JSON Schema validation..."
    if ! jsonschema -i "$HOST_CONFIG" "$SCHEMA_DIR/host-config.schema.json" 2>/dev/null; then
        echo "WARNING: Host config failed JSON Schema validation (schema may need updating)" >&2
    else
        echo "  host config: valid"
    fi

    if [[ -f "$SCHEMA_DIR/packages.schema.json" ]] && [[ -f "$REPO_ROOT/packages.json" ]]; then
        if ! jsonschema -i "$REPO_ROOT/packages.json" "$SCHEMA_DIR/packages.schema.json" 2>/dev/null; then
            echo "WARNING: packages.json failed JSON Schema validation (schema may need updating)" >&2
        else
            echo "  packages.json: valid"
        fi
    fi
else
    echo "NOTE: jsonschema CLI not available; skipping JSON Schema validation."
    echo "      Install with: pipx install jsonschema"
fi

if [[ $ERRORS -gt 0 ]]; then
    echo "Validation failed with $ERRORS error(s)." >&2
    exit 1
fi

echo "Validation passed."
