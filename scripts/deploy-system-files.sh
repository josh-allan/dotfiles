#!/usr/bin/env bash
# Usage: deploy-system-files.sh SRC_DIR TARGET_DIR
# Copies every file under SRC_DIR to the same relative path under TARGET_DIR, with sudo.
# Copies rather than links: systemd refuses unit files that are symlinks into a home dir.
set -euo pipefail

src_dir="${1:?usage: deploy-system-files.sh SRC_DIR TARGET_DIR}"
target_dir="${2:?usage: deploy-system-files.sh SRC_DIR TARGET_DIR}"

if [[ ! -d "$src_dir" ]]; then
	echo "deploy-system-files: $src_dir not found" >&2
	exit 1
fi

num_failed=0
while IFS= read -r -d '' file; do
	dest="$target_dir/${file#"$src_dir"/}"
	sudo mkdir -p "$(dirname "$dest")"
	if ! sudo cp --remove-destination "$file" "$dest"; then
		echo "deploy-system-files: failed to copy $dest" >&2
		num_failed=$((num_failed + 1))
	fi
done < <(fd --type f --hidden --no-ignore --exclude .stow-local-ignore --print0 . "$src_dir")

if ((num_failed > 0)); then
	echo "deploy-system-files: $num_failed file(s) failed under $src_dir" >&2
	exit 1
fi
echo "deploy-system-files: $src_dir -> $target_dir"
