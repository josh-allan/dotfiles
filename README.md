# Wayland dotfiles.

Dotfiles repository that contains all of my configs.

---

## Dependencies and various configurations:

---

- Build an AUR helper and then install packages from minimum_packages.lst
- aur helper: `git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si`
  `git clone https://github.com/NvChad/NvChad ~/.config/nvim --depth 1 && nvim` followed by `:MasonInstallAll`
- run Stow from inside the dotfiles folder and these should symlink to the correct location
- `stow $appname`
- There's some cruftiness involved to get the powerlevel10k fonts installed correctly, see `https://dane-bulat.medium.com/powerline-on-linux-an-integration-guide-c097831106f6.`
- zsh and powerlevel10k: `https://davidtsadler.com/posts/arch/2020-09-07/installing-zsh-and-powerlevel10k-on-arch-linux/`
- Some liberties and scripts have been borrowed from @Viqueen's Devbox repo and added into `.zshrc`

## Custom services

- keyd (keyboard daemon service)
  - loads the thinkpad acpi driver and injects custom handlers for controlling keyboard brightness (All credit to @Abrasive)
- swaymond
  - a crude python script to dynamically detect and handle monitor swaps on Sway
- headphone_touchcontrols
  - service to load `mpris-proxy` at boot enabling touchpad controls for Sony headphones

---

## Specifically related to the Thinkbook 13s

---

- microphone fixing is clunky pre kernel 5.20:
  - The solution for Lenovo devices is to use the topology provided in https://github.com/thesofproject/linux/files/5981682/sof-hda-generic-2ch-pdm1.zip
  - Unzip and copy sof-hda-generic-2ch-pdm1.tplg over /lib/firmware/intel/sof-tplg/sof-hda-generic-2ch.tplg (KEEP THE INITIAL VERSION AS A BACKUP).
- Keyboard brightness is also clunky - copy keyd to /usr/bin/keyd, chmod 755 + chown root:root. Copy keyd.service -> /etc/systemd/system/keyd.service and then enable service to run at startup
