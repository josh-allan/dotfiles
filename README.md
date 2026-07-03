# Dotfiles

Machine-specific dotfiles managed with GNU Stow, templates, and per-host configs.

## Quick Start

```bash
# 1. Clone this repo
git clone git@github.com:josh-allan/dotfiles.git ~/.dotfiles
cd ~/dotfiles

# 2. Install dependencies
./scripts/install-deps.sh

# 3. First run: render templates from 1Password (needs op unlocked) and stow packages
./scripts/sync-dotfiles.sh --bootstrap

# 4. Pray.
```

Subsequent syncs skip template rendering (no 1Password needed) and just stow:

```bash
./scripts/sync-dotfiles.sh                # sync only
./scripts/sync-dotfiles.sh --bootstrap    # re-render templates (secrets changed)
./scripts/sync-dotfiles.sh --compliance   # sync + drift checks
./scripts/sync-dotfiles.sh --check-only   # drift check, no sync
```

A missing rendered file is always rendered regardless of flags, and rendering is atomic: if 1Password is locked, the existing file is kept untouched.

## Architecture

| Component | Purpose |
|-----------|---------|
| `hosts/<hostname>.json` | Per-machine config: packages, templates, private repo, compliance |
| `templates/` | Base files with `{{placeholder}}` values rendered at sync |
| `scripts/sync-dotfiles.sh` | Orchestrator: detect → render → pull → stow → compliance |
| `scripts/check-compliance.sh` | Drift detection: packages, services, files with `--accept` for intentional drift |
| `private/` | gitignored staging area for cloned private overlay repo |

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
