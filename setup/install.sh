#!/usr/bin/env bash
# DO NOT CALL THIS DIRECTLY. Use 'just setup'

# Assume we're running from the root of the project
export PATH="$CHEZMOI_WORKING_TREE/setup:$CHEZMOI_WORKING_TREE/scripts:$PATH"

set -o nounset    ## Force an exit if script tries to use an unset variable
set -o errexit    ## Force an exit if any commands exit with non-zero status
set -euo pipefail ## Catch mid-pipe non-zero exit statuses
IFS=$'\n\t'

# Exiting the script properly - use "err_exit <message>" to properly exit.
trap "exit 1" SIGUSR1
PROC=$$
err_exit() {
  echo -e "$@" >&2
  kill -10 $PROC
}

setup_directory="${PWD##*/}"
log info "You're currently here: $setup_directory"

if [[ "${setup_directory}" != "chezmoi" ]]; then
  err_exit "You need to run this from the chezmoi root with the 'just' program. Once 'just' is installed, run 'just setup'"
fi

# Ask for the administrator password upfront
log info "We need your password in order to setup things properly."
sudo -v

# Keep-alive: update existing `sudo` time stamp until the script has finished
while true; do
  sudo -n true
  sleep 60
  kill -0 "$$" || exit
done 2>/dev/null &

./setup/macos/_main  # Setting up macOS system settings...
./setup/tools/node   # Setup node with 'n' and some global packages
./setup/tools/python # Setup pyenv with some global requirements
./setup/tools/kube   # Setup Kube tooling
./setup/tools/java   # Setup Java-related things
./setup/tools/rust   # Setup Rust and cargo-related things

./setup/install-backup.sh # Install packages from the backup
./setup/tools/mongo       # Setup MongoDB versions - must be done after restoring from backup

log info "Running chezmoi to setup configuration files..."
chezmoi init --apply

log ok "Done!"
