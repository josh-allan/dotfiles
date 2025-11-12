#!/usr/bin/env bash

set -euo pipefail

sudo -n true
test $? -eq 0 || exit 1 "This should be run as root"

# First off, install yay
#git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si

# Install the minimum required packages
cat minimum_packages.lst | while read line; do yay -S $line --y; done 


