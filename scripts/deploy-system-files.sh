#!/usr/bin/env bash
# Usage: deploy-system-files.sh SRC_DIR TARGET_DIR
# Copies every git-tracked file under SRC_DIR to the same relative path under TARGET_DIR,
# with sudo. Copies rather than links: systemd refuses unit files that are symlinks into a
# home dir, and on josh-desktop /home mounts after early boot (wol.service needs a real file).
set -euo pipefail

src_dir="${1:?usage: deploy-system-files.sh SRC_DIR TARGET_DIR}"
target_dir="${2:?usage: deploy-system-files.sh SRC_DIR TARGET_DIR}"

if [[ ! -d "$src_dir" ]]; then
	echo "deploy-system-files: $src_dir not found" >&2
	exit 1
fi

src_real="$(readlink -f "$src_dir")"

# The old stow setup linked whole directories into the repo (e.g. /etc/systemd/system-sleep).
# Copying through such a link targets the source file itself, so remove any link on the
# path to REL that resolves into SRC_DIR. Links elsewhere are left alone.
remove_links_into_src() {
	local path="$target_dir" part resolved
	local -a parts
	IFS=/ read -r -a parts <<<"$1"
	for part in "${parts[@]}"; do
		path="$path/$part"
		[[ -L "$path" ]] || continue
		resolved="$(readlink -f "$path")"
		if [[ "$resolved" == "$src_real" || "$resolved" == "$src_real"/* ]]; then
			sudo rm "$path"
			echo "deploy-system-files: removed old link $path -> $resolved"
			return
		fi
	done
}

# Tracked files only: untracked host snapshots kept next to them (e.g. josh-desktop's
# fstab reference copy, with per-install UUIDs) must never reach the live system.
num_failed=0
while IFS= read -r -d '' rel; do
	dest="$target_dir/$rel"
	remove_links_into_src "$rel"
	sudo mkdir -p "$(dirname "$dest")"
	if ! sudo cp --remove-destination "$src_dir/$rel" "$dest"; then
		echo "deploy-system-files: failed to copy $dest" >&2
		num_failed=$((num_failed + 1))
	fi
done < <(git -C "$src_dir" ls-files -z)

if ((num_failed > 0)); then
	echo "deploy-system-files: $num_failed file(s) failed under $src_dir" >&2
	exit 1
fi
echo "deploy-system-files: $src_dir -> $target_dir"
