# AGENTS.md - Dotfiles Repository Guide

Dotfiles managed by chezmoi in symlink mode. A gitignored `private/` checkout is a second
chezmoi source, applied after this one; its conventions live in `private/AGENTS.md`.

---

## Layout

| Path | Purpose |
|------|---------|
| `.chezmoiroot` | Points chezmoi at `home/`; everything else in the repo is not managed |
| `home/` | chezmoi source state: `dot_config/<tool>` → `~/.config/<tool>` |
| `home/.chezmoi.toml.tmpl` | Host prompt (asked once) and derived per-host data flags |
| `home/.chezmoiignore` | Gating by `.chezmoi.os` and host flags |
| `home/.chezmoiexternal.toml.tmpl` | git-repo externals (nvim config, go-git) |
| `home/.chezmoiscripts/` | `run_` scripts: packages, system files, gpg import, `private/` pull and apply |
| `home/.linked/` | Directories linked whole via `symlink_` templates (chezmoi ignores dot-dirs in the source) |
| `etc_linux/`, `asahi_system/` | System files, deployed with `scripts/deploy-system-files.sh` |
| `packages.json` + `schemas/packages.schema.json` | Platform packages and their field reference |
| `mise.toml` | Portable CLI tools and `mise run` tasks |
| `private/` | Second chezmoi source (gitignored); see `private/AGENTS.md` |

---

## Host Data

`home/.chezmoi.toml.tmpl` prompts for `host` once (`promptStringOnce`) and derives flags.
Templates check flags, never host names:

| Flag | Meaning |
|------|---------|
| `work` / `opVault` | Work Mac; 1Password vault `Work` or `Personal` |
| `asahi`, `sunshine`, `hyprHost` | Linux host variants (hypr `host.*` selection, system files) |
| `linger` | Enable `loginctl enable-linger` |
| `fetchSshKey` | Write `~/.ssh/id_ed25519` from 1Password if missing |
| `cloneGoGit` | Clone `~/src/go-git` |
| `privatePkgs` | Packages the `private/` source applies on this host |
| `gitName`, `gitEmail`, `gitSigningKey` | Read from 1Password at init only |

An unknown host gets the defaults: all flags false, `Personal` vault, default `privatePkgs`.
The OS always comes from `.chezmoi.os`. To add a machine-specific behaviour, add the host
name to the flag expressions in `.chezmoi.toml.tmpl`.

---

## Adding Files

1. Put the file under `home/` with chezmoi naming: `.foo` → `dot_foo`, a name starting
   with a chezmoi prefix (`private_`, `run_`, ...) → `literal_<name>`, a real `.tmpl` file →
   `<name>.tmpl.literal`. Or run `chezmoi add --follow <path>` and move it if needed.
2. OS- or host-specific? Add its target path to `home/.chezmoiignore` under the right gate.
3. Per-machine values? Make it a `.tmpl` and use host data. Secrets: `onepasswordRead`
   (pre-commit only allows `op://` in `home/**/*.tmpl`). Templates are copied, not linked.
4. App rewrites its config by replacing the file (breaks a symlink)? Put the directory in
   `home/.linked/<name>` and add `home/dot_config/symlink_<name>.tmpl`.
5. Belongs in `private/`? Follow `private/AGENTS.md`.
6. Check: `chezmoi diff`, then `chezmoi apply`.

Executables in `home/` keep their git mode and are linked, so no `executable_` prefix.

---

## Scripts and Tasks

| Command | Purpose |
|---------|---------|
| `scripts/bootstrap.sh` | New machine via `curl \| bash`: git, HTTPS clone, mise, then `mise run bootstrap` |
| `mise run bootstrap` | install-tools → install-apps → `ensure-access.sh` (op signed in, GitHub SSH) → `chezmoi init --apply` |
| `mise run sync` / `diff` | `chezmoi apply` / `chezmoi diff` |
| `mise run migrate` | `scripts/migrate-from-stow.sh`: one-time cutover from the old stow setup |
| `mise run store-gpg-key` | Upload the signing key to 1Password (`Git Signing Key (private)`) |
| `scripts/install-deps.sh` | Package-manager bootstrap (brew / yay / Fedora repos), git, jq, op, packages.json |
| `scripts/deploy-system-files.sh SRC TARGET` | sudo-copies git-tracked files only (never untracked snapshots like fstab) |

Run scripts use `bash`; anything handed to the user to type must be fish-compatible.
Python runs on mise's pinned interpreter (`mise exec -- python3`), never the system one.

---

## Packages

`packages.json` holds `tools` and `apps`. Fields are documented in
`schemas/packages.schema.json` (`platforms`, `brew`, `pacman`, `dnf`, `aur`, `copr`,
`flatpak`, `cask`, `tap`, `arch`). A tool lives in `mise.toml` **or** `packages.json`,
never both (`tests/test_mise.py`). Edits rerun the packages script on the next apply.

---

## Githooks

`core.hooksPath = .githooks`. Each hook ends with a managed beads block; leave it intact.

| Hook | Behavior |
|------|----------|
| pre-commit | Blocks `op://` outside `home/**/*.tmpl`, likely secrets, anything under `private/`; shellchecks staged `.sh` |
| pre-push | Pushes the `private/` repo first if it has unpushed commits |
| post-checkout / post-merge | Regenerate opencode agents via `~/.config/opencode/scripts/bootstrap.sh` when their templates change |

---

## Tests

- `tests/test_mise.py`: `uvx pytest tests/test_mise.py` (needs Python 3.11+ for `tomllib`)
- `tests/test_keybindings.lua`: `lua tests/test_keybindings.lua .` (reads rex/hypr configs from `home/`)
- Shell: `shellcheck` every script; render `run_` templates with
  `chezmoi execute-template < file | shellcheck -s bash -`
