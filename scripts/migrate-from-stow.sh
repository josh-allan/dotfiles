#!/usr/bin/env bash
# One-time cutover from the old stow setup to chezmoi.
#
# Usage: migrate-from-stow.sh [--dry-run] [--yes] [--keep-private] [--host NAME]
#   --dry-run       list the stow links (depth 5 under ~) that would be removed, change nothing
#   --yes           skip both confirmation prompts
#   --keep-private  leave links into ~/.dotfiles/private (private-dots not converted yet)
#   --host NAME     host profile for `chezmoi init` (default: prompt, suggesting the hostname)
#
# Steps: remove symlinks under ~ that point into the repo, carry over fish_variables,
# delete the old rendered templates, then `chezmoi init` + diff + apply.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dry_run=false
assume_yes=false
keep_private=false
host=""

while (($# > 0)); do
	case "$1" in
	--dry-run) dry_run=true ;;
	--yes) assume_yes=true ;;
	--keep-private) keep_private=true ;;
	--host)
		host="${2:?--host needs a value}"
		shift
		;;
	*)
		echo "migrate-from-stow: unknown argument $1" >&2
		exit 2
		;;
	esac
	shift
done

# Resolve now: removing the stow links also removes ~/.config/mise, after which the
# mise shim for chezmoi no longer knows which version to run.
chezmoi_bin="$(mise which chezmoi 2>/dev/null || command -v chezmoi)"

confirm() {
	$assume_yes && return 0
	read -r -p "$1 [y/N] " reply
	[[ "$reply" == [yY]* ]]
}

# Stow links are relative (../.dotfiles/...); links restored from a Linux backup are
# absolute (/home/josh/.dotfiles/...). Both contain "/.dotfiles/" or start with ".dotfiles/".
points_into_repo() {
	local target="$1"
	[[ "$target" == */.dotfiles/* || "$target" == .dotfiles/* ]] || return 1
	# chezmoi's own links point into the source dirs; leaving them makes reruns safe.
	if [[ "$target" == *.dotfiles/home/* || "$target" == *.dotfiles/private/home/* ]]; then
		return 1
	fi
	if $keep_private && [[ "$target" == *.dotfiles/private/* ]]; then
		return 1
	fi
}

stow_links=()
# Enablement links (e.g. timers.target.wants/backup.timer) pointing into the repo get
# removed too; re-enable their units after apply, once the unit files are linked again.
reenable_units=()
while IFS= read -r -d '' link; do
	if points_into_repo "$(readlink "$link")"; then
		stow_links+=("$link")
		if [[ "$link" == */systemd/user/*.wants/* ]]; then
			reenable_units+=("$(basename "$link")")
		fi
	fi
done < <(fd --type symlink --hidden --no-ignore --max-depth 5 --exclude .dotfiles --print0 . "$HOME")

echo "Stow links to remove: ${#stow_links[@]}"
for link in ${stow_links[@]+"${stow_links[@]}"}; do
	echo "  ${link/#$HOME/~} -> $(readlink "$link")"
done
$dry_run && exit 0

if ((${#stow_links[@]} > 0)); then
	confirm "Remove these links?" || exit 1
	rm -- "${stow_links[@]}"
fi

old_fish_variables="$repo/dot_config_common/.config/fish/fish_variables"
if [[ -f "$old_fish_variables" && ! -e "$HOME/.config/fish/fish_variables" ]]; then
	mkdir -p "$HOME/.config/fish"
	mv "$old_fish_variables" "$HOME/.config/fish/fish_variables"
	echo "Moved fish_variables to ~/.config/fish"
fi

rm -f "$repo/dot_home/.gitconfig" "$repo/dot_home/.zshrc"

init_args=(init --source "$repo")
if [[ -n "$host" ]]; then
	init_args+=(--promptString "Host profile=$host")
fi
"$chezmoi_bin" "${init_args[@]}"

"$chezmoi_bin" diff || true
confirm "Apply?" || exit 1
"$chezmoi_bin" apply --verbose

if ((${#reenable_units[@]} > 0)) && command -v systemctl >/dev/null 2>&1; then
	systemctl --user daemon-reload
	for unit in "${reenable_units[@]}"; do
		systemctl --user enable "$unit" && echo "Re-enabled $unit"
	done
fi
