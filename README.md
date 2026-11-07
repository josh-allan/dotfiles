# Dotfiles

Dotfiles managed by [chezmoi](https://www.chezmoi.io/) in symlink mode. Packages come from `packages.json`
(brew / pacman / dnf) and `mise.toml` (portable CLI tools).

## Quick start

```fish
# 1. Clone
git clone git@github.com:josh-allan/dotfiles.git ~/.dotfiles
cd ~/.dotfiles

# 2. Install mise and trust the repo config
./scripts/setup-mise.sh
mise trust

# 3. Bootstrap: CLI tools, apps (including the 1Password CLI), then `chezmoi init --apply`.
#    Keep the 1Password app unlocked with CLI integration on: init reads git identity
#    and keys from it.
mise run bootstrap
```

`chezmoi init` asks for a **host profile** once and stores it in
`~/.config/chezmoi/chezmoi.toml`. Use one of `EverythingMacbook`, `EverythingLaptop`,
`josh-desktop`, `M-J7KGT9QHDJ`, or any new name to get the defaults.

**Migrating a machine still on the old stow setup:** `mise run migrate`. It removes the
stow links, carries over `fish_variables`, then runs `chezmoi init` and `apply`.

## Day to day

```fish
chezmoi apply        # or: mise run sync
chezmoi diff         # or: mise run diff
chezmoi update       # pull this repo, then apply
chezmoi managed      # list managed paths
```

Plain config files are **symlinks** into `home/`, so editing `~/.config/fish/config.fish`
edits the repo. Templates (`*.tmpl`) and `private_` files are copies: change the source in
`home/` and run `chezmoi apply`.

## Layout

| Path | Purpose |
|------|---------|
| `home/` | chezmoi source (`.chezmoiroot`). `dot_config/fish` → `~/.config/fish`, etc. |
| `home/.chezmoi.toml.tmpl` | Host prompt and the per-host flags every template gates on |
| `home/.chezmoiignore` | OS and host gating (Linux-only, macOS-only, per-host files) |
| `home/.chezmoiexternal.toml.tmpl` | Repos cloned into `$HOME`: nvim config, go-git |
| `home/.chezmoiscripts/` | Run scripts: packages, system files, gpg key |
| `home/.linked/karabiner` | Linked as a whole directory (Karabiner needs the dir linked) |
| `etc_linux/`, `asahi_system/` | System files copied into `/etc` and `/` with sudo on Linux |
| `packages.json` | GUI apps and system packages per platform (`schemas/packages.schema.json` documents the fields) |
| `mise.toml` | Portable CLI tools and the `mise run` tasks |
| `scripts/` | `install-deps.sh`, `install-packages.py`, `deploy-system-files.sh`, `migrate-from-stow.sh`, `store-gpg-key.sh`, `zen-setup.sh`, `setup-mise.sh` |

## Hosts

| Host | OS | Notes |
|------|----|-------|
| `EverythingMacbook` | macOS | |
| `EverythingLaptop` | Linux | Asahi hypr host config and system files, ssh key from 1Password. Notes said Arch Linux ARM; now runs Fedora |
| `josh-desktop` | Linux | Sunshine streaming, linger |
| `M-J7KGT9QHDJ` | macOS | Work: `Work` 1Password vault |

**Services expected to be enabled** (not enabled automatically; the old compliance
checker only warned): `mpris-proxy.service`, `titdb.service` and `tzupdate.timer` on
EverythingLaptop; `mpris-proxy.service` on josh-desktop.

## Secrets

- Git name, email and signing key id are read from 1Password once, at `chezmoi init`.
  Routine applies don't need 1Password.
- The gpg signing key is imported from the 1Password document **Git Signing Key (private)**
  when a machine has no full secret key. Upload it from a machine that has the key with
  `mise run store-gpg-key` (optional vault argument, default `Personal`).

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
