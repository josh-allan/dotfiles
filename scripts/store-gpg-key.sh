#!/usr/bin/env bash
# Usage: store-gpg-key.sh [VAULT]   (default vault: Personal)
# Uploads the armored git signing key to 1Password as the "Git Signing Key (private)"
# document, which the chezmoi gpg-import script reads on machines that lack the key.
# Run on a machine that holds the full secret key, once per vault.
set -euo pipefail

vault="${1:-Personal}"
title="Git Signing Key (private)"
key_id="$(git config --get user.signingkey)"

# --with-colons marks a stub (secret part absent) with "#" in field 15 of the sec record.
if ! gpg --list-secret-keys --with-colons "$key_id" 2>/dev/null | awk -F: '$1 == "sec" && $15 != "#" { found = 1 } END { exit !found }'; then
	echo "store-gpg-key: this machine has no full secret key for $key_id (missing or stub only)." >&2
	exit 1
fi

# The key goes through a pipe only, never a file or a command-line argument.
if op document get "$title" --vault "$vault" >/dev/null 2>&1; then
	gpg --export-secret-keys --armor "$key_id" | op document edit "$title" - --vault "$vault" --file-name gpg-signing-key.asc
else
	gpg --export-secret-keys --armor "$key_id" | op document create - --title "$title" --vault "$vault" --file-name gpg-signing-key.asc
fi
echo "store-gpg-key: stored $key_id in $vault/$title"
