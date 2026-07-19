#!/usr/bin/env bash
set -euo pipefail

# setup-mise.sh
# Installs mise itself if missing. The only step before `mise run bootstrap`.
# Idempotent: safe to re-run.

if command -v mise >/dev/null 2>&1; then
    echo "[OK] mise already installed: $(mise version 2>/dev/null | head -1)"
    exit 0
fi

echo "[INFO] Installing mise via https://mise.run ..."
curl -fsSL https://mise.run | sh

MISE_BIN="$HOME/.local/bin/mise"
if [[ ! -x "$MISE_BIN" ]]; then
    echo "[ERROR] mise install script finished but $MISE_BIN not found" >&2
    exit 1
fi

echo "[OK] mise installed: $("$MISE_BIN" --version)"
echo
echo "Add mise to PATH for this session, trust the repo config, then bootstrap:"
# shellcheck disable=SC2016  # literal $PATH is intentional: it's a snippet for the user to run
echo '  export PATH="$HOME/.local/bin:$PATH"   # bash/zsh'
echo '  fish_add_path ~/.local/bin             # fish'
echo "  mise trust        # required once per clone"
echo "  mise run bootstrap"
echo
echo "Tip: export a GitHub token first or installs may hit the 60/hr"
echo "unauthenticated API limit (fish: set -gx MISE_GITHUB_TOKEN (gh auth token))"
