#!/usr/bin/env bash
# Run by `mise run bootstrap` before `chezmoi init`, which needs both of these:
#   1. the 1Password CLI signed in (init reads git identity; templates read keys)
#   2. SSH access to GitHub (private repo, nvim and go-git externals use git@github.com)
# If SSH fails and no key exists, writes ~/.ssh/id_ed25519 from 1Password.
#
# Env overrides: OP_SSH_KEY_ITEM (default "op://Personal/Primary SSH key (id_ed25519) ").
set -euo pipefail

ssh_key_item="${OP_SSH_KEY_ITEM:-op://Personal/Primary SSH key (id_ed25519) }"
ssh_key="$HOME/.ssh/id_ed25519"

log() { printf '\033[1;34m[access]\033[0m %s\n' "$*"; }
die() {
	printf '\033[1;31m[access]\033[0m %s\n' "$*" >&2
	exit 1
}

op_ready=false

# Warns rather than blocks: headless hosts have no 1Password app to unlock.
check_op() {
	if ! command -v op >/dev/null 2>&1; then
		log "1Password CLI (op) not installed; continuing without 1Password"
		return
	fi
	# Not `op whoami`: with the desktop-app integration it reports "not signed in" until a
	# real request triggers authorization. Listing vaults is such a request.
	if op vault list >/dev/null 2>&1; then
		op_ready=true
		log "1Password CLI signed in"
		return
	fi
	log "1Password CLI is not signed in; continuing without 1Password (git identity stays empty)."
	log "To fill it later: unlock the 1Password app with CLI integration, or on a headless host"
	log "'set -x OP_BIOMETRIC_UNLOCK_ENABLED false; op signin | source', then rerun 'chezmoi init'."
}

# `ssh -T` exits 1 even on success, so match GitHub's greeting instead. Captured rather
# than piped: under pipefail a pipe would take ssh's exit status and always fail.
github_ssh_ok() {
	local greeting
	greeting="$(ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com 2>&1 || true)"
	[[ "$greeting" == *"successfully authenticated"* ]]
}

ensure_github_ssh() {
	if github_ssh_ok; then
		log "GitHub SSH access works"
		return
	fi
	if [[ -e "$ssh_key" ]]; then
		die "GitHub SSH fails but $ssh_key exists; add it to GitHub or ssh-agent, then rerun"
	fi
	$op_ready || die "GitHub SSH fails and 1Password is unavailable to fetch $ssh_key; add a key to GitHub, then rerun"
	log "Writing $ssh_key from 1Password"
	mkdir -p "$HOME/.ssh"
	chmod 700 "$HOME/.ssh"
	# printf adds the trailing newline OpenSSH requires; op read may omit it.
	(
		umask 077
		printf '%s\n' "$(op read "${ssh_key_item}/private key")" >"$ssh_key"
	)
	printf '%s\n' "$(op read "${ssh_key_item}/public key")" >"$ssh_key.pub"
	chmod 644 "$ssh_key.pub"
	github_ssh_ok || die "GitHub SSH still fails with the 1Password key; check it is added to GitHub"
	log "GitHub SSH access works"
}

check_op
ensure_github_ssh
