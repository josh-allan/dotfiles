#!/usr/bin/env bash
set -euo pipefail

# fetch-ssh-keys.sh
# Fetches SSH keys from 1Password and writes them to ~/.ssh/.
# Reads key references from the host config's ssh_keys section.
# Safe to re-run: skips keys that already exist unless --force is passed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
FORCE=false

for arg in "$@"; do
    [[ "$arg" == "--force" ]] && FORCE=true
done

HOST_CONFIG="${DOTFILES_HOST_CONFIG:-}"
if [[ -z "$HOST_CONFIG" ]]; then
    HOSTNAME="$(hostname | cut -d. -f1)"
    HOST_CONFIG="$REPO_ROOT/hosts/$HOSTNAME.json"
    [[ ! -f "$HOST_CONFIG" ]] && HOST_CONFIG="$REPO_ROOT/hosts/default.json"
fi

if [[ ! -f "$HOST_CONFIG" ]]; then
    echo "fetch-ssh-keys: no host config found — skipping"
    exit 0
fi

if ! jq -e '.ssh_keys' "$HOST_CONFIG" >/dev/null 2>&1; then
    echo "fetch-ssh-keys: no ssh_keys configured in $HOST_CONFIG — skipping"
    exit 0
fi

if ! command -v op >/dev/null 2>&1; then
    echo "fetch-ssh-keys: 1Password CLI (op) not found — skipping"
    exit 1
fi

mkdir -p ~/.ssh
chmod 700 ~/.ssh

while IFS= read -r key_name; do
    private_ref="$(jq -r ".ssh_keys[\"$key_name\"].private" "$HOST_CONFIG")"
    public_ref="$(jq -r ".ssh_keys[\"$key_name\"].public // empty" "$HOST_CONFIG")"

    private_dest="$HOME/.ssh/$key_name"
    public_dest="$HOME/.ssh/$key_name.pub"

    if [[ -f "$private_dest" ]] && ! $FORCE; then
        echo "fetch-ssh-keys: $key_name already exists — skipping (use --force to overwrite)"
        continue
    fi

    echo "fetch-ssh-keys: fetching $key_name from 1Password..."

    private_key="$(op read "$private_ref" 2>/dev/null)"
    if [[ -z "$private_key" ]]; then
        echo "fetch-ssh-keys: ERROR — could not read private key for $key_name"
        continue
    fi

    # Ensure the key ends with a newline (required by OpenSSH)
    printf '%s\n' "$private_key" > "$private_dest"
    chmod 600 "$private_dest"
    echo "  wrote $private_dest"

    if [[ -n "$public_ref" ]]; then
        public_key="$(op read "$public_ref" 2>/dev/null || true)"
        if [[ -n "$public_key" ]]; then
            printf '%s\n' "$public_key" > "$public_dest"
            chmod 644 "$public_dest"
            echo "  wrote $public_dest"
        fi
    fi

done < <(jq -r '.ssh_keys | keys[]' "$HOST_CONFIG")

echo "fetch-ssh-keys: done"
