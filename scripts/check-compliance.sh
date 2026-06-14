#!/usr/bin/env bash
set -euo pipefail

# Thin bash wrapper for the Python compliance checker.
# Detects the host, resolves the config path, and dispatches to Python.
#
# Usage:
#   check-compliance.sh [--pre | --post] [--packages-only] [--services-only]
#                       [--files-only] [--json] [--quick]
#                       [--accept TYPE:DOMAIN:ID] [...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOSTNAME="$(hostname | cut -d. -f1)"
HOST_CONFIG="${DOTFILES_HOST_CONFIG:-$REPO_ROOT/hosts/$HOSTNAME.json}"

if [[ ! -f "$HOST_CONFIG" ]]; then
    HOST_CONFIG="$REPO_ROOT/hosts/default.json"
fi

if [[ ! -f "$HOST_CONFIG" ]]; then
    echo "ERROR: No host config found at hosts/$HOSTNAME.json or hosts/default.json" >&2
    exit 2
fi

exec python3 -m scripts.lib.compliance.checker \
    --host-config "$HOST_CONFIG" \
    --packages-json "$REPO_ROOT/packages.json" \
    --repo-root "$REPO_ROOT" \
    "$@"
