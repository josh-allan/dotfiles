#!/usr/bin/env bash
set -euo pipefail

# Thin bash wrapper for the Python compliance checker.
# Detects the host, resolves the config path, and dispatches to Python.
#
# Usage:
#   check-compliance.sh [--pre | --post] [--packages-only] [--services-only]
#                       [--files-only] [--json] [--full] [--quick]
#                       [--edit] [--fix [--yes]] [--accept TYPE:DOMAIN:ID] [...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
# shellcheck source=SCRIPTDIR/lib/host.sh
source "$SCRIPT_DIR/lib/host.sh"
resolve_host_config "$REPO_ROOT" || exit $?

exec python3 -m scripts.lib.compliance.checker \
    --host-config "$HOST_CONFIG" \
    --packages-json "$REPO_ROOT/packages.json" \
    --repo-root "$REPO_ROOT" \
    "$@"
