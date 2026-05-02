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

# Portable canonical path resolution.
# Prefers realpath (macOS 13+, Linux), falls back to perl (available on
# all macOS versions), then readlink -f (GNU coreutils).
_resolve_canonical() {
    if command -v realpath >/dev/null 2>&1; then
        realpath "$1" 2>/dev/null || true
    elif command -v perl >/dev/null 2>&1; then
        perl -MCwd -e 'print Cwd::realpath($ARGV[0])' -- "$1" 2>/dev/null || true
    else
        readlink -f "$1" 2>/dev/null || true
    fi
}

# Validate that a stow package is correctly linked by sampling files
# and comparing their canonical paths.  A single match is sufficient
# because stow is atomic: either all files are linked or the operation
# fails entirely (modulo conflicts).
validate_package() {
    local pkg_label pkg pkg_dir stow_dir
    local found total checked remaining
    local file rel target target_canon expected_canon status
    local -a issues
    local suggestion

    pkg_label="$1"
    pkg="$2"
    pkg_dir="$3"
    stow_dir="$4"
    found=0
    total=0
    checked=0
    issues=()

    # Defensive: strip trailing slash so ${file#"$pkg_dir"/} works correctly.
    pkg_dir="${pkg_dir%/}"

    if [[ ! -d "$pkg_dir" ]]; then
        echo "WARNING: ${pkg_label} package '$pkg' not found at $pkg_dir"
        return
    fi

    # Walk all files in the package directory.
    while IFS= read -r -d '' file; do
        rel="${file#"$pkg_dir"/}"
        target="$HOME/$rel"
        total=$((total + 1))

        # Once we know stow succeeded, stop doing expensive canonicalisation.
        if [[ $found -eq 0 ]]; then
            target_canon="$(_resolve_canonical "$target")"
            expected_canon="$(_resolve_canonical "$file")"
            if [[ -n "$target_canon" && "$target_canon" == "$expected_canon" ]]; then
                found=1
            fi
        fi

        # Collect up to 5 sample issues while we still think stow failed.
        if [[ $found -eq 0 && $checked -lt 5 ]]; then
            if [[ -L "$target" ]]; then
                status="(exists as symlink but points elsewhere)"
            elif [[ -e "$target" ]]; then
                status="(exists but is not a symlink)"
            else
                status="(does not exist)"
            fi
            # shellcheck disable=SC2088 # Tilde is intentional for display output.
            issues+=("~/$rel $status")
            checked=$((checked + 1))
        fi

        # No need to keep walking once we have confirmed stow worked.
        if [[ $found -eq 1 ]]; then
            break
        fi
    done < <(find "$pkg_dir" -type f -not -path '*/.git/*' -print0 2>/dev/null || true)

    if [[ $found -eq 1 ]]; then
        return
    fi

    if [[ $total -eq 0 ]]; then
        echo "WARNING: ${pkg_label} package '$pkg' may not be stowed correctly"
        echo "  Package dir: $pkg_dir (exists)"
        echo "  Note: Package contains no files to stow."
        return
    fi

    echo "WARNING: ${pkg_label} package '$pkg' may not be stowed correctly"

    for issue in "${issues[@]}"; do
        echo "  Checked: $issue"
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

    suggestion="stow -n"
    for arg in "${skip_args[@]}"; do
        suggestion+=" $(printf '%q' "$arg")"
    done
    suggestion+=" -d \"$stow_dir\" -t \"$HOME\" \"$pkg\""
    echo "  Likely cause: Target paths already exist as real files/directories. Run '$suggestion' to see conflicts."
}

for pkg in "${public_packages[@]}"; do
    validate_package "Public" "$pkg" "$REPO_ROOT/$pkg" "$REPO_ROOT"
done

for pkg in "${private_packages[@]}"; do
    validate_package "Private" "$pkg" "$PRIVATE_DIR/$pkg" "$PRIVATE_DIR"
done

echo "Sync complete."
