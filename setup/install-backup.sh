#!/usr/bin/env bash
# DO NOT CALL THIS DIRECTLY. Use 'just setup'

export PATH="$CHEZMOI_WORKING_TREE/setup:$CHEZMOI_WORKING_TREE/scripts:$PATH"

set -o nounset    ## Force an exit if script tries to use an unset variable
set -o errexit    ## Force an exit if any commands exit with non-zero status
set -euo pipefail ## Catch mid-pipe non-zero exit statuses
IFS=$'\n\t'

log info "Installing Homebrew..."
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

log info "Installing Homebrew packages and casks..."
eval "$(/opt/homebrew/bin/brew shellenv)"
(
  cd "$CHEZMOI_WORKING_TREE"/backup || return

  NONINTERACTIVE=1 brew bundle --file Brewfile
)

log info "Installing backed up 'npm' packages..."
npm install -g backup-global
backup-global install --input "$CHEZMOI_WORKING_TREE"/backup/npm.global.backup.txt

log info "Installing backed up global python packages..."
pipx ensurepath
while IFS= read -r dep; do
  PIPX_DEFAULT_PYTHON="$(pyenv prefix)/bin/python" pipx install "$dep"
done <"$CHEZMOI_WORKING_TREE"/backup/pipx-deps.txt

log info "Installing backup/restore tool..."
cargo install cargo-backup

log info "Installing crates defined in the global backup file..."
cargo restore --backup "$CHEZMOI_WORKING_TREE"/backup/cargo-global.json --skip-remove --skip-update
