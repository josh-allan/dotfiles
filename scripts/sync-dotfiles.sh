#!/usr/bin/env bash
set -euo pipefail

# sync-dotfiles.sh
# Machine-specific dotfiles sync orchestrator.
# Detects hostname, loads host config, renders templates, pulls private repo, stows packages.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOSTS_DIR="$REPO_ROOT/hosts"
TEMPLATES_DIR="$REPO_ROOT/templates"
PRIVATE_DIR="$REPO_ROOT/private"

HOSTNAME="$(hostname | cut -d. -f1)"
HOST_CONFIG="$HOSTS_DIR/$HOSTNAME.json"

# Allow explicit override
if [[ -n "${DOTFILES_HOST_CONFIG:-}" ]]; then
    HOST_CONFIG="$DOTFILES_HOST_CONFIG"
    echo "Using explicit host config: $HOST_CONFIG"
fi

# Fallback to default
if [[ ! -f "$HOST_CONFIG" ]]; then
    HOST_CONFIG="$HOSTS_DIR/default.json"
    echo "No host config found for '$HOSTNAME'. Using default."
fi

echo "Host config: $HOST_CONFIG"

# Step 1: Validate
"$SCRIPT_DIR/validate-config.sh" "$HOST_CONFIG"

# Step 2: Render templates
if [[ -d "$TEMPLATES_DIR" ]]; then
    echo "Rendering templates..."
    "$SCRIPT_DIR/render-templates.sh" "$HOST_CONFIG" "$TEMPLATES_DIR" "$REPO_ROOT"
else
    echo "Step 2: No templates directory — skipping"
fi

# Step 3: Clone/pull private repo
PRIVATE_REPO_URL="$(jq -r '.private_repo.url // empty' "$HOST_CONFIG")"
PRIVATE_REPO_BRANCH="$(jq -r '.private_repo.branch // "main"' "$HOST_CONFIG")"

if [[ -n "$PRIVATE_REPO_URL" ]]; then
    echo "Setting up private repo..."

    if [[ -d "$PRIVATE_DIR/.git" ]]; then
        echo "Pulling latest private repo..."
        git -C "$PRIVATE_DIR" pull origin "$PRIVATE_REPO_BRANCH" || {
            echo "WARNING: Failed to update private repo. Continuing with existing copy." >&2
        }
    else
        echo "Cloning private repo..."
        git clone --branch "$PRIVATE_REPO_BRANCH" "$PRIVATE_REPO_URL" "$PRIVATE_DIR" || {
            echo "WARNING: Failed to clone private repo. Skipping private packages." >&2
        }
    fi
else
    echo "Step 3: No private repo configured — skipping"
fi

# Step 4: Stow public packages
# Bash 3.2 compat: use while read instead of mapfile
public_packages=()
while IFS= read -r pkg; do
    [[ -n "$pkg" ]] && public_packages+=("$pkg")
done < <(jq -r '.packages.public[] // empty' "$HOST_CONFIG" 2>/dev/null || true)

# Build ignore list from skip_paths (once, shared by public and private stow)
skip_args=()
while IFS= read -r skip; do
    [[ -n "$skip" ]] && skip_args+=(--ignore="$skip")
done < <(jq -r '.skip_paths[] // empty' "$HOST_CONFIG" 2>/dev/null || true)

if [[ ${#public_packages[@]} -gt 0 ]]; then
    echo "Stowing public packages: ${public_packages[*]}"

    for pkg in "${public_packages[@]}"; do
        pkg_dir="$REPO_ROOT/$pkg"

        if [[ ! -d "$pkg_dir" ]]; then
            echo "WARNING: Public package not found: $pkg_dir"
            continue
        fi

        stow "${skip_args[@]}" -d "$REPO_ROOT" -t "$HOME" "$pkg"
        echo "  Stowed: $pkg"
    done
fi

# Step 5: Stow private packages
private_packages=()
while IFS= read -r pkg; do
    [[ -n "$pkg" ]] && private_packages+=("$pkg")
done < <(jq -r '.packages.private[] // empty' "$HOST_CONFIG" 2>/dev/null || true)

if [[ ${#private_packages[@]} -gt 0 && -d "$PRIVATE_DIR" ]]; then
    echo "Stowing private packages: ${private_packages[*]}"

    for pkg in "${private_packages[@]}"; do
        pkg_dir="$PRIVATE_DIR/$pkg"

        if [[ ! -d "$pkg_dir" ]]; then
            echo "WARNING: Private package not found: $pkg_dir"
            continue
        fi

        stow "${skip_args[@]}" -d "$PRIVATE_DIR" -t "$HOME" "$pkg"
        echo "  Stowed: $pkg (private)"
    done
fi

# Step 5b: Manual symlinks for packages that can't be stowed (merge into existing dirs)
# private_user fish functions need to merge into ~/.config/fish/ which is already a symlink
if [[ -d "$PRIVATE_DIR/private_user/.config/fish/private_user" ]]; then
    target="$HOME/.config/fish/private_user"
    source="$PRIVATE_DIR/private_user/.config/fish/private_user"
    
    if [[ -L "$target" ]]; then
        current="$(readlink "$target")"
        if [[ "$current" != "$source" ]]; then
            rm "$target"
            ln -s "$source" "$target"
            echo "  Linked: $target -> $source"
        fi
    elif [[ -e "$target" ]]; then
        echo "  WARNING: $target exists and is not a symlink"
    else
        ln -s "$source" "$target"
        echo "  Linked: $target -> $source"
    fi
fi

# Step 6: Post-sync validation — verify stow-created symlinks exist
echo "Running post-sync validation..."

for pkg in "${public_packages[@]}"; do
    found=0
    # Check common patterns for stow-created symlinks
    [[ -L "$HOME/.config/$pkg" ]] && found=1
    [[ -L "$HOME/$pkg" ]] && found=1
    # Also check top-level items from the package directory
    for item in "$REPO_ROOT/$pkg"/*; do
        [[ -e "$item" ]] || continue
        item_name="$(basename "$item")"
        [[ -L "$HOME/$item_name" ]] && found=1 && break
    done
    if [[ $found -eq 0 ]]; then
        echo "WARNING: Public package '$pkg' may not be stowed correctly"
    fi
done

for pkg in "${private_packages[@]}"; do
    found=0
    [[ -L "$HOME/.config/$pkg" ]] && found=1
    [[ -L "$HOME/$pkg" ]] && found=1
    for item in "$PRIVATE_DIR/$pkg"/*; do
        [[ -e "$item" ]] || continue
        item_name="$(basename "$item")"
        [[ -L "$HOME/$item_name" ]] && found=1 && break
    done
    if [[ $found -eq 0 ]]; then
        echo "WARNING: Private package '$pkg' may not be stowed correctly"
    fi
done

echo "Sync complete."
