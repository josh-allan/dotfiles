#!/usr/bin/env bash
# New-machine entry point. Gets git, the repo and mise in place, then hands off to
# `mise run bootstrap` (apps, 1Password + GitHub access, chezmoi init --apply).
#
#   curl -fsSL https://raw.githubusercontent.com/josh-allan/dotfiles/main/scripts/bootstrap.sh | bash
#
# Env overrides: DOTFILES_DIR (default ~/.dotfiles), DOTFILES_BRANCH (default main).
# Prompts read from /dev/tty, because under `curl | bash` stdin is this script.
set -euo pipefail

repo_dir="${DOTFILES_DIR:-$HOME/.dotfiles}"
branch="${DOTFILES_BRANCH:-main}"
# HTTPS needs no key; the applied gitconfig rewrites GitHub URLs to SSH afterwards.
repo_url="https://github.com/josh-allan/dotfiles.git"

log() { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }
die() {
	printf '\033[1;31m[bootstrap]\033[0m %s\n' "$*" >&2
	exit 1
}

ensure_git() {
	command -v git >/dev/null 2>&1 && return
	case "$(uname -s)" in
	Darwin)
		log "Installing the Xcode Command Line Tools (accept the dialog)..."
		xcode-select --install >/dev/null 2>&1 || true
		until xcode-select -p >/dev/null 2>&1 && command -v git >/dev/null 2>&1; do
			sleep 5
		done
		;;
	Linux)
		if command -v dnf >/dev/null 2>&1; then
			sudo dnf install -y git
		elif command -v pacman >/dev/null 2>&1; then
			sudo pacman -S --needed --noconfirm git
		else
			die "install git, then rerun"
		fi
		;;
	*) die "unsupported OS: $(uname -s)" ;;
	esac
}

ensure_repo() {
	if [[ -d "$repo_dir/.git" ]]; then
		log "Using existing checkout at $repo_dir"
		return
	fi
	log "Cloning dotfiles ($branch) into $repo_dir"
	git clone --branch "$branch" "$repo_url" "$repo_dir"
}

ensure_mise() {
	"$repo_dir/scripts/setup-mise.sh" >/dev/null
	export PATH="$HOME/.local/bin:$PATH"
	command -v mise >/dev/null 2>&1 || die "mise not on PATH after install"
	mise trust --yes "$repo_dir/mise.toml" >/dev/null
}

ensure_git
ensure_repo
ensure_mise

log "Handing off to: mise run bootstrap"
cd "$repo_dir"
exec mise run bootstrap </dev/tty
