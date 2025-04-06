# Dotfiles

Dotfiles repository that contains all of my configs.

## DISCLAIMER
--- 
This config is designed for Linux, however it will work for MacOS with some tinkering
---

## Linux 

---

## Dependencies and various configurations:

---

- Build an AUR helper and then install packages from minimum_packages.lst
- aur helper: `git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si` && yay -S - < minimum_packages.lst
- run Stow from inside the dotfiles folder and these should symlink to the correct location
- `stow $appname`
- There's some cruftiness involved to get the powerlevel10k fonts installed correctly, see `https://dane-bulat.medium.com/powerline-on-linux-an-integration-guide-c097831106f6.`
- zsh and powerlevel10k: `https://davidtsadler.com/posts/arch/2020-09-07/installing-zsh-and-powerlevel10k-on-arch-linux/`

## Custom services

- keyd (keyboard daemon service)
  - loads the thinkpad acpi driver and injects custom handlers for controlling keyboard brightness 
- swaymond
  - a crude python script to dynamically detect and handle monitor swaps on Sway
- headphone_touchcontrols
  - service to load `mpris-proxy` at boot enabling touchpad controls for Sony headphones

## Kudos 
---
- @viqueen's Devbox repo, some scripts have been borrowed and added into `.zshrc`
- @macintacos for some helpful neovim keybinds, and a remapping helper function
- @abrasive for the keyboard daemon service
