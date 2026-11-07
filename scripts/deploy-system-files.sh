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

# Tracked files only: untracked host snapshots kept next to them (e.g. josh-desktop's
# fstab reference copy, with per-install UUIDs) must never reach the live system.
num_failed=0
while IFS= read -r -d '' rel; do
	dest="$target_dir/$rel"
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
