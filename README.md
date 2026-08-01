# Dotfiles

Machine-specific dotfiles managed with GNU Stow, templates, and per-host configs.

## Quick Start

```bash
# 1. Clone this repo
git clone git@github.com:josh-allan/dotfiles.git ~/.dotfiles
cd ~/.dotfiles

# 2. Install mise (the installer's only prerequisite) and trust the config
./scripts/setup-mise.sh
mise trust

# 2b. Recommended: a GitHub token, or tool downloads hit the 60/hr
#     unauthenticated API limit. In fish:
#     set -gx MISE_GITHUB_TOKEN (gh auth token)

# 3. Bootstrap: CLI tools (mise), apps/system packages (brew/yay/dnf),
#    templates from 1Password (needs op unlocked), stow, private overlay
mise run bootstrap

# 4. Pray.
```

Day-to-day tasks:

```bash
mise run sync         # stow only (no 1Password needed)
mise run compliance   # sync + drift checks
mise run check        # drift check, no sync
mise install          # install/update portable CLI tools
```

A missing rendered file is always rendered regardless of flags, and rendering is atomic: if 1Password is locked, the existing file is kept untouched.

## Architecture

| Component | Purpose |
|-----------|---------|
| `mise.toml` | Portable CLI tools + task entry points (`mise run bootstrap`) |
| `hosts/<hostname>.json` | Per-machine config: packages, templates, private repo, compliance |
| `templates/` | Base files with `{{placeholder}}` values rendered at sync |
| `scripts/sync-dotfiles.sh` | Orchestrator: detect → render → pull → stow → compliance |
| `scripts/check-compliance.sh` | Drift detection: packages, services, files with `--accept` for intentional drift |
| `private/` | gitignored staging area for cloned private overlay repo |

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
