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

# Flags
BOOTSTRAP=0
COMPLIANCE="${DOTFILES_COMPLIANCE:-0}"
for arg in "$@"; do
    case "$arg" in
        --bootstrap) BOOTSTRAP=1 ;;
        --compliance) COMPLIANCE=1 ;;
        --check-only)
            echo "Running compliance check only..."
            if [[ -x "$SCRIPT_DIR/check-compliance.sh" ]]; then
                exec "$SCRIPT_DIR/check-compliance.sh" --pre
            else
                echo "ERROR: check-compliance.sh not found" >&2
                exit 2
            fi
            ;;
        *)
            echo "Unknown flag: $arg" >&2
            echo "Usage: sync-dotfiles.sh [--bootstrap] [--compliance] [--check-only]" >&2
            exit 2
            ;;
    esac
done

# Render templates from 1Password references.
# Skips templates whose output already exists unless --bootstrap is given,
# so routine syncs don't depend on 1Password being unlocked.
# Renders to a temp file and only replaces the output on full success, so a
# failed `op read` can never clobber a working config with raw placeholders.
render_templates() {
    local template_key template_file output_file tmp_file placeholder op_ref value ok

    while IFS= read -r template_key; do
        [[ -n "$template_key" ]] || continue

        template_file="$TEMPLATES_DIR/$template_key.tmpl"
        output_file="$REPO_ROOT/$template_key"

        if [[ ! -f "$template_file" ]]; then
            echo "WARNING: Template not found: $template_file"
            continue
        fi

        if [[ -f "$output_file" && $BOOTSTRAP -eq 0 ]]; then
            echo "  $template_key: already rendered (--bootstrap to re-render)"
            continue
        fi

        mkdir -p "$(dirname "$output_file")"
        tmp_file="$(mktemp)"
        cp "$template_file" "$tmp_file"
        ok=1

        while IFS= read -r placeholder; do
            [[ -n "$placeholder" ]] || continue

            op_ref="$(jq -r --arg t "$template_key" --arg p "$placeholder" '.templates[$t][$p]' "$HOST_CONFIG")"
            value="$(op read "$op_ref" 2>/dev/null || true)"

            if [[ -z "$value" ]]; then
                echo "WARNING: Could not read 1Password reference for '$placeholder' in '$template_key'"
                ok=0
                break
            fi

            OP_KEY="{{$placeholder}}" OP_VALUE="$value" \
                perl -i -pe 's/\Q$ENV{OP_KEY}\E/$ENV{OP_VALUE}/g' -- "$tmp_file"
            echo "  $template_key: {{$placeholder}} -> [redacted]"
        done < <(jq -r --arg t "$template_key" '.templates[$t] | keys[]' "$HOST_CONFIG" 2>/dev/null || true)

        if [[ $ok -eq 1 ]]; then
            mv "$tmp_file" "$output_file"
            echo "  Rendered: $template_key"
        else
            rm -f "$tmp_file"
            if [[ -f "$output_file" ]]; then
                echo "  Kept existing $template_key (render failed; is 1Password unlocked?)"
            else
                echo "  ERROR: $template_key not rendered and no existing file (unlock 1Password and re-run with --bootstrap)"
            fi
        fi
    done < <(jq -r '.templates | keys[]' "$HOST_CONFIG" 2>/dev/null || true)
}


# Step 1: Validate
"$SCRIPT_DIR/validate-config.sh" "$HOST_CONFIG"

# Step 1.5: Pre-sync compliance check (opt-in via --compliance flag or DOTFILES_COMPLIANCE=1)
if [[ "$COMPLIANCE" == "1" && -x "$SCRIPT_DIR/check-compliance.sh" ]]; then
    echo "Running pre-sync compliance check..."
    "$SCRIPT_DIR/check-compliance.sh" --pre || {
        echo "WARNING: Pre-sync compliance check found drift. See ~/.config/dotfiles/drift-report.json"
    }
fi

# Step 2: Render templates
if [[ -d "$TEMPLATES_DIR" ]]; then
    echo "Rendering templates..."
    render_templates
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

# Step 3b: Clone/pull auxiliary repos (e.g. josh_nvim)
while IFS=$'\t' read -r repo_url repo_target repo_branch; do
    [[ -z "$repo_url" ]] && continue
    repo_target="${repo_target/#\~/$HOME}"
    repo_branch="${repo_branch:-main}"
    if [[ -d "$repo_target/.git" ]]; then
        echo "Pulling $repo_url -> $repo_target"
        git -C "$repo_target" pull origin "$repo_branch" || {
            echo "WARNING: Failed to update $repo_target. Continuing with existing copy." >&2
        }
    elif [[ -L "$repo_target" && ! -e "$repo_target" ]]; then
        # Dangling symlink (e.g. old stow link after a package rename): safe to replace.
        echo "Removing dangling symlink $repo_target"
        rm "$repo_target"
        echo "Cloning $repo_url -> $repo_target"
        git clone --branch "$repo_branch" "$repo_url" "$repo_target" || {
            echo "WARNING: Failed to clone $repo_url. Continuing." >&2
        }
    elif [[ -d "$repo_target" && ! -L "$repo_target" && -z "$(find "$repo_target" -type f -print -quit 2>/dev/null)" ]]; then
        # Real directory but no regular files anywhere inside: stow residue
        # (folded dir of now-dangling symlinks). Nothing to lose — replace it.
        echo "Removing stow residue directory $repo_target"
        rm -rf "$repo_target"
        echo "Cloning $repo_url -> $repo_target"
        git clone --branch "$repo_branch" "$repo_url" "$repo_target" || {
            echo "WARNING: Failed to clone $repo_url. Continuing." >&2
        }
    elif [[ -e "$repo_target" ]]; then
        echo "WARNING: $repo_target exists but is not a git repo (contains real files). Skipping $repo_url." >&2
    else
        echo "Cloning $repo_url -> $repo_target"
        git clone --branch "$repo_branch" "$repo_url" "$repo_target" || {
            echo "WARNING: Failed to clone $repo_url. Continuing." >&2
        }
    fi
done < <(jq -r '.repos[]? | [.url, .target, .branch // "main"] | @tsv' "$HOST_CONFIG" 2>/dev/null || true)

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

# Packages that share a target directory with another package (e.g. both
# "sunshine" and the private "systemd" package populate .config/systemd/user).
# GNU Stow folds a directory into one symlink when it's first claimed by a
# single package; a second package then can't add files alongside it —
# "target exists" conflict. --no-folding keeps the shared dir real so both
# packages' files can coexist. Scoped to just these two (not applied
# blanket) since it changes maintenance behavior: files added later inside
# a --no-folding'd package need a re-sync to appear, unlike a folded symlink
# where new files show up automatically.
fold_flag_for() {
    case "$1" in
        sunshine|systemd) echo "--no-folding" ;;
    esac
}

if [[ ${#public_packages[@]} -gt 0 ]]; then
    echo "Stowing public packages: ${public_packages[*]}"

    for pkg in "${public_packages[@]}"; do
        pkg_dir="$REPO_ROOT/$pkg"

        if [[ ! -d "$pkg_dir" ]]; then
            echo "WARNING: Public package not found: $pkg_dir"
            continue
        fi

        stow $(fold_flag_for "$pkg") --adopt ${skip_args+"${skip_args[@]}"} -d "$REPO_ROOT" -t "$HOME" "$pkg"
        git -C "$REPO_ROOT" restore "$pkg/" 2>/dev/null || true
        echo "  Stowed: $pkg"
    done
fi

# Step 5: Stow private packages
private_packages=()
while IFS= read -r pkg; do
    [[ -n "$pkg" ]] && private_packages+=("$pkg")
done < <(jq -r '.packages.private[] // empty' "$HOST_CONFIG" 2>/dev/null || true)

# Ensure $target is a symlink to $source. Replaces stale symlinks and empty
# dirs; refuses to touch real files or non-empty dirs.
link_fallback() {
    local source="$1" target="$2"
    if [[ -L "$target" ]]; then
        [[ "$(readlink "$target")" == "$source" ]] && return
        rm "$target"
    elif [[ -d "$target" ]]; then
        if ! rmdir "$target" 2>/dev/null; then
            echo "  WARNING: $target is a non-empty dir — skipping (remove it manually if you want the dotfiles version)"
            return
        fi
    elif [[ -e "$target" ]]; then
        echo "  WARNING: $target exists and is not a symlink — skipping (remove it manually if you want the dotfiles version)"
        return
    fi
    ln -s "$source" "$target"
    echo "  Linked: $target -> $source"
}

if [[ ${#private_packages[@]} -gt 0 && -d "$PRIVATE_DIR" ]]; then
    echo "Stowing private packages: ${private_packages[*]}"

    for pkg in "${private_packages[@]}"; do
        pkg_dir="$PRIVATE_DIR/$pkg"

        if [[ ! -d "$pkg_dir" ]]; then
            echo "WARNING: Private package not found: $pkg_dir"
            continue
        fi

        if stow $(fold_flag_for "$pkg") --adopt ${skip_args+"${skip_args[@]}"} -d "$PRIVATE_DIR" -t "$HOME" "$pkg" 2>/dev/null; then
            git -C "$PRIVATE_DIR" restore "$pkg/" 2>/dev/null || true
            echo "  Stowed: $pkg (private)"
        else
            case "$pkg" in
                private_user)
                    echo "  Stow conflict: $pkg (using manual symlink fallback)"
                    # private_user fish functions need to merge into ~/.config/fish/ which is already a symlink
                    if [[ -d "$PRIVATE_DIR/private_user/.config/fish/private_user" ]]; then
                        link_fallback "$PRIVATE_DIR/private_user/.config/fish/private_user" "$HOME/.config/fish/private_user"
                    fi
                    ;;
                augment)
                    echo "  Stow conflict: $pkg (using manual symlink fallback)"
                    # ~/.augment already exists (Auggie runtime dir) — descend and link contents
                    mkdir -p "$HOME/.augment"
                    for sub in rules skills; do
                        link_fallback "$PRIVATE_DIR/augment/.augment/$sub" "$HOME/.augment/$sub"
                    done
                    ;;
                *)
                    echo "  Stow conflict: $pkg (target exists — manual fix required)"
                    ;;
            esac
        fi
    done
fi

# Step 5.5: Stow system packages (requires sudo, Linux only)
system_packages=()
while IFS= read -r entry; do
    [[ -n "$entry" ]] && system_packages+=("$entry")
done < <(jq -c '.packages.system[] // empty' "$HOST_CONFIG" 2>/dev/null || true)

if [[ ${#system_packages[@]} -gt 0 ]]; then
    echo "Stowing system packages..."
    for entry in "${system_packages[@]}"; do
        pkg="$(echo "$entry" | jq -r '.pkg')"
        target="$(echo "$entry" | jq -r '.target')"
        # A private system package lives in the private-dots repo, not the public root.
        if [[ "$(echo "$entry" | jq -r '.private // false')" == "true" ]]; then
            base_dir="$PRIVATE_DIR"
        else
            base_dir="$REPO_ROOT"
        fi
        pkg_dir="$base_dir/$pkg"

        if [[ ! -d "$pkg_dir" ]]; then
            echo "WARNING: System package not found: $pkg_dir"
            continue
        fi

        if sudo stow --adopt ${skip_args+"${skip_args[@]}"} -d "$base_dir" -t "$target" "$pkg"; then
            git -C "$base_dir" restore "$pkg/" 2>/dev/null || true
            echo "  Stowed: $pkg -> $target"
        else
            echo "WARNING: Failed to stow system package '$pkg' (target: $target)"
        fi
    done
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
    local pkg_label pkg pkg_dir stow_dir target_dir
    local found total checked remaining
    local file rel target target_canon expected_canon status
    local -a issues
    local suggestion

    pkg_label="$1"
    pkg="$2"
    pkg_dir="$3"
    stow_dir="$4"
    target_dir="${5:-$HOME}"
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
        target="$target_dir/$rel"
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
    for arg in ${skip_args[@]+"${skip_args[@]}"}; do
        suggestion+=" $(printf '%q' "$arg")"
    done
    suggestion+=" -d \"$stow_dir\" -t \"$target_dir\" \"$pkg\""
    echo "  Likely cause: Target paths already exist as real files/directories. Run '$suggestion' to see conflicts."
}

for pkg in "${public_packages[@]}"; do
    validate_package "Public" "$pkg" "$REPO_ROOT/$pkg" "$REPO_ROOT"
done

for pkg in "${private_packages[@]}"; do
    validate_package "Private" "$pkg" "$PRIVATE_DIR/$pkg" "$PRIVATE_DIR"
done

for entry in ${system_packages[@]+"${system_packages[@]}"}; do
    pkg="$(echo "$entry" | jq -r '.pkg')"
    target="$(echo "$entry" | jq -r '.target')"
    # Mirror the base_dir resolution in the Step 5.5 stow loop above — a
    # private system package lives in the private-dots repo, not the public root.
    if [[ "$(echo "$entry" | jq -r '.private // false')" == "true" ]]; then
        base_dir="$PRIVATE_DIR"
    else
        base_dir="$REPO_ROOT"
    fi
    validate_package "System" "$pkg" "$base_dir/$pkg" "$base_dir" "$target"
done

# Step 6.5: Post-sync compliance verification (opt-in via --compliance flag or DOTFILES_COMPLIANCE=1)
if [[ "$COMPLIANCE" == "1" && -x "$SCRIPT_DIR/check-compliance.sh" ]]; then
    echo "Running post-sync compliance verification..."
    "$SCRIPT_DIR/check-compliance.sh" --post || {
        echo "WARNING: Post-sync compliance verification found issues. See ~/.config/dotfiles/drift-report.json"
    }

    # Notify if drift detected (guarded: requires notify-send + graphical session)
    DRIFT_REPORT="$HOME/.config/dotfiles/drift-report.json"
    if [[ -f "$DRIFT_REPORT" ]]; then
        EXIT_CODE="$(jq -r '.exitCode // 0' "$DRIFT_REPORT")"
        if [[ "$EXIT_CODE" -ne 0 ]] && command -v notify-send >/dev/null 2>&1; then
            if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
                SUMMARY="$(jq -r '.summary | "\(.fail) required, \(.warn) warnings"' "$DRIFT_REPORT")"
                notify-send -a dotfiles -u normal \
                    "Dotfiles sync: drift detected" \
                    "$SUMMARY — run check-compliance.sh to review"
            fi
        fi
    fi
fi

# Step 7: Browser-specific setup
if [[ "$(jq -r '.os // empty' "$HOST_CONFIG")" == "linux" ]]; then
    echo "Running zen-setup..."
    "$SCRIPT_DIR/zen-setup.sh" || echo "WARNING: zen-setup failed — run scripts/zen-setup.sh manually"
fi

echo "Sync complete."
