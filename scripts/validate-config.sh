#!/usr/bin/env bash
set -euo pipefail

# validate-config.sh
# Validates prerequisites and host config before sync.
# Usage: validate-config.sh <host_config.json>

HOST_CONFIG="${1:-}"

if [[ -z "$HOST_CONFIG" ]]; then
    echo "Usage: $0 <host_config.json>"
    exit 1
fi

ERRORS=0

# Check prerequisites
check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $1"
        ERRORS=$((ERRORS + 1))
    fi
}

check_command stow
check_command jq
check_command git
check_command op

# Validate JSON syntax
if ! jq empty "$HOST_CONFIG" 2>/dev/null; then
    echo "ERROR: Invalid JSON in $HOST_CONFIG"
    ERRORS=$((ERRORS + 1))
fi

# Validate required fields
if ! jq -e '.packages' "$HOST_CONFIG" >/dev/null 2>&1; then
    echo "ERROR: Missing required field: packages"
    ERRORS=$((ERRORS + 1))
fi

# Validate OS value if present
os="$(jq -r '.os // empty' "$HOST_CONFIG")"
if [[ -n "$os" && "$os" != "macos" && "$os" != "linux" ]]; then
    echo "ERROR: Invalid os value: '$os'. Must be 'macos' or 'linux'."
    ERRORS=$((ERRORS + 1))
fi

if [[ $ERRORS -gt 0 ]]; then
    echo "Validation failed with $ERRORS error(s)."
    exit 1
fi

echo "Validation passed."
