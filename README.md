# Dotfiles

Machine-specific dotfiles managed with GNU Stow, templates, and per-host configs.

## Quick Start

```bash
# 1. Clone this repo
git clone git@github.com:josh-allan/.dotfiles.git ~/dotfiles
cd ~/dotfiles

# 2. Install dependencies
./scripts/install-deps.sh

# 3. Run sync (detects hostname, renders templates, stows relevant packages)
./scripts/sync-dotfiles.sh
```

## Architecture

| Component | Purpose |
|-----------|---------|
| `hosts/<hostname>.json` | Per-machine config: packages, templates, private repo |
| `templates/` | Base files with `{{placeholder}}` values rendered at sync |
| `scripts/sync-dotfiles.sh` | Orchestrator: detect → render → pull → stow |
| `private/` | gitignored staging area for cloned private overlay repo |

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
