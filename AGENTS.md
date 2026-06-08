# AGENTS.md - Dotfiles Repository Guide

Machine-specific dotfiles managed with GNU Stow, per-host JSON configs, template rendering, and cross-platform package management.

---

## Directory Layout

| Path | Purpose |
|------|---------|
| `hosts/<hostname>.json` | Per-machine manifests defining packages, templates, and OS |
| `templates/` | Files with `{{placeholder}}` values rendered at sync via 1Password CLI |
| `packages.json` | Single source of truth for cross-platform dev tools and apps |
| `scripts/` | Sync orchestrator, package installers, validators, setup helpers |
| `dot_home/` | Stow package for `~` (common home dir configs, scripts, services) |
| `dot_config_common/` | Stow package for `~/.config` (cross-platform tools: fish, nvim, ghostty, wezterm, yazi) |
| `dot_config_linux/` | Stow package for `~/.config` (Linux-only: hypr, greetd, gtk, fuzzel, rofi, sddm, kanata, zen) |
| `dot_config_macos/` | Stow package for `~/.config` (macOS-only configs) |
| `etc_linux/` | Stow package for `/etc` (Linux system configs: greetd) |
| `nvim/` | Git submodule for neovim config |
| `.githooks/` | Git hooks: pre-commit, pre-push, post-checkout, post-merge, prepare-commit-msg |
| `docs/superpowers/specs/` | Design documents for planned features |
| `docs/superpowers/plans/` | Implementation plans with step-by-step tasks |
| `README.md` | Quick start and architecture overview |

---

## Stow Package Map

| Package | Stow Target | Contents |
|---------|-------------|----------|
| `dot_home` | `~` | `.gitignore`, `.ideavimrc`, `.zshrc`, `scripts/`, `services/`, `firefox/`, `wallpaper/` |
| `dot_config_common` | `~/.config` | fish, nvim, ghostty, wezterm, yazi |
| `dot_config_linux` | `~/.config` | hypr, greetd, gtk-3.0, gtk-4.0, fuzzel, rofi, sddm, hyprpanel, kanata, wayle, zen |
| `dot_config_macos` | `~/.config` | macOS-specific configs |
| `etc_linux` | `/etc` | System-level configs (greetd) |

**Naming convention:** Directories prefixed `dot_` map to `~` (via Stow's `-t ~`). `etc_linux` maps to `/etc` (uses `sudo stow -t /etc`).

**Path mapping within packages:** A file at `dot_config_linux/.config/hypr/hyprland.conf` becomes `~/.config/hypr/hyprland.conf` after stowing. Stow creates symlinks; the actual file lives only in the repo. Remove the stow package to remove the links cleanly.

**Per-package stow-local-ignore:** Place a `.stow-local-ignore` file inside any stow package directory to list glob patterns stow should skip for that package (one pattern per line, `^` prefix for regex anchors). Currently used in `dot_home/` to exclude the old `ai-tools` directory from stowing.

---

## Adding New Files Under Management

1. **Choose the right stow package:**
   - Cross-platform `~/.config` tool → `dot_config_common/.config/<tool>/`
   - Linux-only `~/.config` tool → `dot_config_linux/.config/<tool>/`
   - macOS-only `~/.config` tool → `dot_config_macos/.config/<tool>/`
   - Home directory file (`.gitignore`, `.ideavimrc`, etc.) → `dot_home/`
   - Home directory scripts → `dot_home/scripts/`
   - System config under `/etc` → `etc_linux/` (and add a `system` entry in the host config)
   - Service units or systemd files → `dot_home/services/` (for user services) or `etc_linux/` (for system services)

2. **If the file contains values that differ per machine** (gitconfig user info, email, signing key, etc.), create a template:
   - Add a `.tmpl` file in `templates/` mirroring the target path (e.g. `templates/dot_home/.gitconfig.tmpl`)
   - Use `{{placeholder}}` for variable values (e.g. `{{user.email}}`)
   - Add the target path and 1Password references to the host config's `templates` section
   - Add the rendered output path to `.gitignore` (at repo root, not inside the template)
   - If the template has no placeholders (like `.zshrc`), it still goes through rendering -- the empty `{}` in the host config tells the sync script to copy it as-is

3. **If the file is machine-specific** and shouldn't exist on all machines:
   - Add it to the appropriate platform-specific stow package (e.g. `dot_config_linux` for Linux-only)
   - Only enable that package in relevant host configs (`dot_config_linux` only in Linux host configs)

4. **Register new tools/apps** in `packages.json` (see Package Management section)

5. **Run validation:** `./scripts/validate-config.sh hosts/<hostname>.json`

---

## Host Configs

Host configs live in `hosts/<hostname>.json`. Hostname detection uses `hostname | cut -d. -f1`, falling back to `hosts/default.json` if no exact match exists. Override with `DOTFILES_HOST_CONFIG` env var.

**Schema:**

| Field | Description |
|-------|-------------|
| `os` | `macos` or `linux`. Used for validation and conditional setup steps (e.g. zen-setup runs only on Linux). |
| `packages.public` | Array of stow package names from this repo to enable (e.g. `dot_home`, `dot_config_common`). These must match directory names in the repo root. |
| `packages.system` | Array of `{"pkg": "etc_linux", "target": "/etc"}` objects for stow packages that need `sudo`. Not all host configs use this. |
| `templates` | Map of target paths (relative to repo root, e.g. `dot_home/.gitconfig`) to objects mapping `{{placeholder}}` names to `op://` 1Password references. |
| `skip_paths` | Array of glob patterns to exclude when stowing. Useful when a stow package contains files that don't apply to a specific machine. |

**Example (`hosts/default.json`):**
```json
{
  "os": "linux",
  "packages": {
    "public": ["dot_home", "dot_config_common", "dot_config_linux"],
    "system": [{"pkg": "etc_linux", "target": "/etc"}]
  },
  "templates": {
    "dot_home/.gitconfig": {
      "user.email": "op://Personal/Git Email/username",
      "user.name": "op://Personal/user/username",
      "user.signingkey": "op://Personal/Git Signing Key/public key"
    }
  },
  "skip_paths": []
}
```

**Adding a new machine:**

1. Run `hostname | cut -d. -f1` on the target machine to get the config name
2. Copy `hosts/default.json` to `hosts/<hostname>.json`
3. Set `"os"` to `"macos"` or `"linux"` as appropriate
4. Adjust `packages.public` for the platform:
   - Linux: `["dot_home", "dot_config_common", "dot_config_linux"]`
   - macOS: `["dot_home", "dot_config_common", "dot_config_macos"]`
5. Add `system` entry only on Linux: `[{"pkg": "etc_linux", "target": "/etc"}]`
6. Add template entries for machine-specific values (gitconfig user info, signing keys)
7. Run `./scripts/validate-config.sh hosts/<hostname>.json` to validate
8. Run `./scripts/sync-dotfiles.sh` to apply (requires `op` authenticated)

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `sync-dotfiles.sh` | Main orchestrator: validate config → render templates from 1Password → stow public packages → stow system packages (with sudo) → post-sync validation → zen-setup. Idempotent. |
| `install-deps.sh` | Full bootstrap: install Homebrew (macOS) or yay (Arch), then git, stow, jq, 1Password CLI. Fetches SSH keys from 1Password. Optionally installs all packages from `packages.json`. |
| `install-packages.py` | Reads `packages.json` and installs per-platform packages. Auto-detects platform or accepts `--platform macos\|arch`. Supports `--dry-run` for preview. |
| `audit-packages.py` | Compares `packages.json` against explicitly-installed pacman packages. Reports untracked installed packages (candidates for adding) and tracked-but-missing packages. Linux only. |
| `validate-config.sh` | Pre-sync validation: checks prerequisites (stow, jq, git, `op` if templates exist), validates JSON syntax, checks required fields, validates `os` value. |
| `fetch-ssh-keys.sh` | Reads `ssh_keys` from host config, fetches each key from 1Password, writes to `~/.ssh/`. Safe to re-run; skips existing keys unless `--force` passed. |
| `zen-setup.sh` | Reads `profiles.ini` in `~/.config/zen/`, finds the default profile, symlinks `user.js` into it. Runs automatically at end of sync on Linux. |

**Common usage patterns:**
```bash
# Full setup from scratch
./scripts/install-deps.sh && ./scripts/sync-dotfiles.sh

# Just validate before committing config changes
./scripts/validate-config.sh hosts/$(hostname | cut -d. -f1).json

# See what packages would install without running
./scripts/install-deps.sh --dry-run

# Audit installed vs tracked packages
python3 scripts/audit-packages.py

# Force re-fetch SSH keys
./scripts/fetch-ssh-keys.sh --force
```

---

## Package Management

`packages.json` is the single source of truth for cross-platform dev tools and apps. It has two top-level arrays:

- **`tools`**: CLI tools and language runtimes (ripgrep, git, fish, neovim, etc.)
- **`apps`**: GUI applications and full desktop software (Discord, Ghostty, VSCode, etc.)

**Entry fields:**

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | Canonical package name |
| `platforms` | `["macos","arch"]` | Which platforms this package applies to |
| `pacman` | `name` | Package name on Arch Linux (pacman/yay) |
| `brew` | `name` | Package name on macOS (Homebrew) |
| `aur` | `false` | Install via yay (AUR) on Arch instead of pacman |
| `cask` | `false` | Use `brew install --cask` on macOS |
| `tap` | none | Homebrew tap to enable before installing (macOS only) |

**Platform defaults:** If `platforms` is omitted, the package installs on both macOS and Arch. Use `["macos"]` or `["arch"]` to restrict.

**Adding a new package:**
```bash
# 1. Find the right name for each platform
#    macOS: brew search <name>
#    Arch:  pacman -Ss <name> or yay -Ss <name>

# 2. Add to packages.json
#    Simple case (same name on both platforms):
    {"name": "bat"}
#    Different names:
    {"name": "awscli", "pacman": "aws-cli"}
#    AUR-only:
    {"name": "ast-grep", "aur": true}
#    Platform-specific:
    {"name": "blueutil", "platforms": ["macos"]}

# 3. Install to verify:
    python3 scripts/install-packages.py --dry-run
```

**Audit workflow:**
```bash
python3 scripts/audit-packages.py
# Review untracked packages and add relevant ones to packages.json
# Run after any significant package install session
```

---

## Templates

Files in `templates/` use `{{placeholder}}` values rendered at sync time via `op read` from 1Password.

**Process (in `sync-dotfiles.sh`):**
1. For each entry in the host config's `templates` object, find the matching `.tmpl` file in `templates/`
2. Copy the template to the target output path in the repo root
3. For each placeholder in the template, read the `op://` reference from the host config and replace `{{placeholder}}` with the fetched value
4. The rendered file is now ready for stowing

**Rules:**
- Template files use a `.tmpl` extension mirroring the target path (e.g. `templates/dot_home/.gitconfig.tmpl`)
- Output goes to the corresponding path in the repo root (e.g. `dot_home/.gitconfig`)
- Rendered files are listed in `.gitignore` and MUST NOT be committed
- If a template has no variable placeholders (empty `{}` in host config), the file is still copied through -- useful for files that should exist on disk but don't need to contain secrets
- `op` CLI must be authenticated before sync. Run `op signin` if needed.

**Template example (`templates/dot_home/.gitconfig.tmpl`):**
```ini
[user]
    name = {{user.name}}
    email = {{user.email}}
    signingkey = {{user.signingkey}}
[init]
    defaultBranch = main
[push]
    autoSetupRemote = true
[pull]
    rebase = true
[core]
    editor = nvim
    pager = delta
[delta]
    navigate = true
    side-by-side = true
```

**Corresponding host config entry:**
```json
{
  "templates": {
    "dot_home/.gitconfig": {
      "user.email": "op://Personal/Git Email/username",
      "user.name": "op://Personal/user/username",
      "user.signingkey": "op://Personal/Git Signing Key/public key"
    }
  }
}
```

---

## Githooks

Hooks are active via `git config core.hooksPath .githooks` (set automatically in the repo). Each hook integrates beads (the task tracker) via managed code blocks at the end of each script.

| Hook | Behavior |
|------|----------|
| **pre-commit** | Scans staged files. Blocks commits with: `op://` refs outside host configs/docs/hooks, hardcoded API keys/tokens/passwords/connection strings, any files in `private/`, rendered `dot_home/.gitconfig`, or files under `dot_config/.config/fish/user/`. Runs beads pre-commit hooks after scan. |
| **pre-push** | Ensures out-of-repo overlays are pushed before the public push. Runs beads pre-push hooks. |
| **post-checkout** | On branch changes, checks if templates/hosts/scripts changed and regenerates opencode agent configs if so. Runs beads post-checkout hooks. |
| **post-merge** | After `git pull`, checks if opencode templates/hosts/scripts changed and regenerates agent configs. Runs beads post-merge hooks. |
| **prepare-commit-msg** | Runs beads hooks for commit message templates. |

---

## Submodule: nvim

The `nvim/` directory is a git submodule pointing to `git@github.com:josh-allan/nvim.git`.

**Clone with submodules:**
```bash
git clone --recurse-submodules git@github.com:josh-allan/dotfiles.git ~/.dotfiles
# or after cloning without --recurse-submodules:
git submodule update --init --recursive
```

**Update after upstream changes:**
```bash
git submodule update --remote nvim
git add nvim
git commit -m "chore(nvim): update submodule"
```

**Working on nvim configs:** The nvim submodule is a standalone repo. Make changes inside `nvim/`, commit there, then commit the updated submodule pointer in the dotfiles repo.

---

## Tooling & Validation

- **File search:** prefer `fd` over `find`
- **Content search:** prefer `rg` (ripgrep) over `grep`
- **JSON validation:** `jq empty <file>` to check syntax
- **Config validation:** `./scripts/validate-config.sh <host_config>`
- **Shell scripts:** ensure they pass `shellcheck`

For available skills and agents, invoke the `skills-catalog` or `agents-catalog` skills.
