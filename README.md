# dotfiles

My machines, managed by [chezmoi](https://www.chezmoi.io/) in symlink mode. Packages live in
`packages/packages.json` (brew / pacman / dnf) and `mise.toml` (CLI tools). Repo layout and
conventions are in `AGENTS.md`.

## New machine

```fish
curl -fsSL https://raw.githubusercontent.com/josh-allan/dotfiles/main/scripts/bootstrap.sh | bash
```

Clones to `~/.dotfiles`, installs mise, then `mise run bootstrap`: tools → apps and
packages → 1Password and GitHub SSH check → `chezmoi init --apply`.

- 1Password CLI must be signed in: unlock the app, Settings > Developer > Integrate with
  1Password CLI. Bootstrap waits for it.
- `chezmoi init` asks for the host name once (stored in `~/.config/chezmoi/chezmoi.toml`).
  An unlisted name gets the defaults.
- Already cloned: `mise run bootstrap`. Other branch: `DOTFILES_BRANCH=<branch>`.

## Day to day

```fish
chezmoi apply        # mise run sync
chezmoi diff         # mise run diff
chezmoi update       # pull, then apply
chezmoi managed
```

Plain files are symlinks into `home/`, so edits in `~/.config` land in the repo. Templates
(`*.tmpl`) and `private_` files are copies: edit the source in `home/`, then apply.

## Hosts

| Host | OS | Notes |
|------|----|-------|
| `EverythingMacbook` | macOS | |
| `EverythingLaptop` | Fedora Asahi | Asahi hypr config and system files, ssh key from 1Password |
| `josh-desktop` | Linux | Sunshine streaming, linger |
| `M-J7KGT9QHDJ` | macOS | Work, `Work` 1Password vault |
| `everythingcomputer` | Arch (x86_64) | Server |

Apply enables `Sunshine.service` and `steam-bpm.service` on josh-desktop. Enable these by
hand: `mpris-proxy.service`, `titdb.service`, `tzupdate.timer` on EverythingLaptop;
`mpris-proxy.service` on josh-desktop.

## Secrets

- Git name, email and signing key id come from 1Password at `chezmoi init` only; applies
  don't touch 1Password.
- The gpg signing key imports from the 1Password document **Git Signing Key (private)** on
  machines without it. Upload from a machine that has it: `mise run store-gpg-key [vault]`
  (default `Personal`).

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
