# Dotfiles

Machine-specific dotfiles managed with GNU Stow, templates, and per-host configs.

## Quick Start

```bash
# 1. Clone
git clone git@github.com:josh-allan/.dotfiles.git ~/dotfiles
cd ~/dotfiles

# 2. Run sync (detects hostname, renders templates, stows relevant packages)
./scripts/sync-dotfiles.sh
```

## Architecture

| Component | Purpose |
|-----------|---------|
| `hosts/<hostname>.json` | Per-machine config: packages, templates, private repo |
| `templates/` | Base files with `{{placeholder}}` values rendered at sync |
| `scripts/sync-dotfiles.sh` | Orchestrator: detect → render → pull → stow |
| `private/` | gitignored staging area for cloned private overlay repo |

## Host Configs

Create `hosts/<hostname>.json` to define what a machine receives:

- `packages.public`: Stow packages from this repo
- `packages.private`: Stow packages from private repo
- `templates`: Files to render with 1Password CLI values
- `skip_paths`: Files to exclude within a package
- `private_repo`: Optional private overlay repo URL

## Stow Packages

| Package | Contents |
|---------|----------|
| `dot_home` | Cross-platform home directory configs |
| `dot_config_common` | Cross-platform `.config/` tools (fish, nvim, wezterm, yazi) |
| `dot_config_macos` | macOS-only `.config/` tools (aerospace, karabiner) |
| `dot_config_linux` | Linux-only `.config/` tools (hypr, greetd, gtk, fuzzel, rofi, sddm, hyprpanel, kanata) |

## Adding a New Machine

1. Create `hosts/<hostname>.json`
2. Define `packages.public` and optionally `packages.private`
3. Add templates for machine-specific values
4. Run `./scripts/sync-dotfiles.sh`

## Templates

Templates live in `templates/` and use `{{key}}` placeholders:

```ini
# templates/dot_home/.gitconfig.tmpl
[user]
    name = {{user.name}}
    email = {{user.email}}
```

Values are fetched from 1Password CLI at sync time using `op read`.

## Private Overlays

Sensitive or work-specific files live in a separate private repo. The sync script clones the private repo into `private/` (gitignored) and stows enabled packages from it.

## Fish Config Structure

The fish config uses a dynamic loading pattern:

```fish
# config.fish
for config in $__fish_config_dir/user/**/*.fish
    source $config
end
```

This means private overlays simply add `.fish` files to `user/` subdirectories (e.g., `user/functions/work/`, `user/env/`) and they're automatically sourced. The public repo no longer contains `user/env/env.fish` — environment variables live in the private repo.

## Leak Prevention

- Real values never exist in this repo; only template placeholders
- `private/` is gitignored
- Pre-commit hook blocks `op://` references, secrets, and generated files

## Kudos

- @viqueen's Devbox repo
- @macintacos for neovim keybinds and fish inspiration
