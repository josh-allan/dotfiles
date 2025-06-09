# Dotfiles

Dotfiles repository.

## DISCLAIMER

---

This configuration is designed for Linux, however it will work for MacOS with some tinkering
---

## Dependencies and various configurations

---

- Build an AUR helper and then install packages from minimum_packages.lst
- aur helper: `git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si` && yay -S - < minimum_packages.lst
- `stow`

## Custom services

- headphone_touchcontrols
  - service to load `mpris-proxy` at boot enabling touchpad controls for Sony headphones

## Kudos

---

- @viqueen's Devbox repo, some scripts have been borrowed and added into `.zshrc`
- @macintacos for some helpful neovim keybinds, and a remapping helper function, plus some fish inspiration
