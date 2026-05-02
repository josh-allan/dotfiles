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

        if stow "${skip_args[@]}" -d "$PRIVATE_DIR" -t "$HOME" "$pkg" 2>/dev/null; then
            echo "  Stowed: $pkg (private)"
        else
            echo "  WARNING: Stow failed for $pkg (may need manual symlinks)"
        fi
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

# Helper: validate a stow package by checking that stowed files resolve
# to the correct package directory via canonical path comparison.
# Args: label ("Public"/"Private"), package_name, package_dir, stow_dir
validate_package() {
    local pkg_label pkg pkg_dir stow_dir
    local found total checked i remaining
    local file rel target target_canon expected_canon status
    local -a issues

    pkg_label="$1"
    pkg="$2"
    pkg_dir="$3"
    stow_dir="$4"
    found=0
    total=0
    checked=0
    issues=()

    if [[ ! -d "$pkg_dir" ]]; then
        echo "WARNING: ${pkg_label} package '$pkg' not found at $pkg_dir"
        return
    fi

    # Walk all files in the package directory
    while IFS= read -r -d '' file; do
        rel="${file#"$pkg_dir"/}"
        target="$HOME/$rel"
        total=$((total + 1))

        # Only one file needs to resolve correctly to confirm stow worked.
        # readlink -f follows directory symlinks (common with stow) to
        # canonical paths, so we compare resolved paths instead of checking [[ -L ]].
        if [[ $found -eq 0 ]]; then
            target_canon="$(readlink -f "$target" 2>/dev/null || true)"
            expected_canon="$(readlink -f "$file" 2>/dev/null || true)"
            if [[ -n "$target_canon" && "$target_canon" == "$expected_canon" ]]; then
                found=1
            fi
        fi

        # Collect up to 5 issues for diagnostic output
        if [[ $found -eq 0 && $checked -lt 5 ]]; then
            if [[ -L "$target" ]]; then
                status="(exists as symlink but points elsewhere)"
            elif [[ -e "$target" ]]; then
                status="(exists but is not a symlink)"
            else
                status="(does not exist)"
            fi
            issues[${#issues[@]}]="$rel"
            issues[${#issues[@]}]="$status"
            checked=$((checked + 1))
        fi
    done < <(find "$pkg_dir" -type f -not -path '*/.git/*' -print0 2>/dev/null || true)

    if [[ $found -eq 0 ]]; then
        echo "WARNING: ${pkg_label} package '$pkg' may not be stowed correctly"

        i=0
        while [[ $i -lt ${#issues[@]} ]]; do
            echo "  Checked: ~/${issues[$i]} ${issues[$i+1]}"
            i=$((i + 2))
        done

        remaining=$((total - checked))
        if [[ $remaining -gt 0 ]]; then
            if [[ $remaining -eq 1 ]]; then
                echo "  ... (1 more file)"
            else
                echo "  ... ($remaining more files)"
            fi
        fi

        echo "  Package dir: $pkg_dir (exists)"
        echo "  Likely cause: Target paths already exist as real files/directories. Run 'stow -n ${skip_args[*]} -d \"$stow_dir\" -t \"$HOME\" \"$pkg\"' to see conflicts."
    fi
}

for pkg in "${public_packages[@]}"; do
    validate_package "Public" "$pkg" "$REPO_ROOT/$pkg" "$REPO_ROOT"
done

for pkg in "${private_packages[@]}"; do
    validate_package "Private" "$pkg" "$PRIVATE_DIR/$pkg" "$PRIVATE_DIR"
done

echo "Sync complete."
