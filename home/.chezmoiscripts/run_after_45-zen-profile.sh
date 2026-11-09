#!/usr/bin/env bash
# Links ~/.config/zen/{user.js,chrome,zen-themes.json} into the default Zen profile,
# whose directory name is random per machine. ZEN_DIR overrides the profile root (tests).
set -euo pipefail

# Profile roots: macOS, Linux XDG (Zen 1.21+, shared with ~/.config/zen), legacy Linux.
# The first with a profiles.ini wins.
if [[ -z "${ZEN_DIR:-}" ]]; then
    for root in "$HOME/Library/Application Support/zen" "${XDG_CONFIG_HOME:-$HOME/.config}/zen" "$HOME/.zen"; do
        if [[ -f "$root/profiles.ini" ]]; then
            ZEN_DIR="$root"
            break
        fi
    done
fi
ZEN_DIR="${ZEN_DIR:-$HOME/.zen}"
PROFILES_INI="$ZEN_DIR/profiles.ini"
SRC_DIR="$HOME/.config/zen"
ENTRIES=(user.js chrome zen-themes.json)

if [[ ! -f "$PROFILES_INI" ]]; then
    echo "zen-profile: no profiles.ini at $PROFILES_INI (Zen never started?) -- skipping"
    exit 0
fi

for name in "${ENTRIES[@]}"; do
    if [[ ! -e "$SRC_DIR/$name" ]]; then
        echo "zen-profile: $SRC_DIR/$name not found"
        exit 1
    fi
done

# The [Install*] Default= key names the profile this Zen install opens;
# older profiles.ini files only mark a [Profile*] section with Default=1.
PROFILE_PATH="$(awk -F= '
    /^\[Install/       { in_install=1; next }
    /^\[/              { in_install=0 }
    in_install && /^Default=/ { print $2; exit }
' "$PROFILES_INI")"

if [[ -z "$PROFILE_PATH" ]]; then
    PROFILE_PATH="$(awk -F= '/^Path=/ { path=$2 } /^Default=1/ { print path }' "$PROFILES_INI")"
fi

if [[ -z "$PROFILE_PATH" ]]; then
    echo "zen-profile: could not determine default profile path from $PROFILES_INI"
    exit 1
fi

PROFILE_DIR="$ZEN_DIR/$PROFILE_PATH"

if [[ ! -d "$PROFILE_DIR" ]]; then
    echo "zen-profile: profile directory not found: $PROFILE_DIR"
    exit 1
fi

link_entry() {
    local src="$SRC_DIR/$1" target="$PROFILE_DIR/$1"
    if [[ -L "$target" ]]; then
        [[ "$(readlink "$target")" == "$src" ]] && return 0
        rm "$target"
    elif [[ -e "$target" ]]; then
        local backup
        backup="$target.bak.$(date +%Y%m%d%H%M%S)"
        echo "zen-profile: backing up $target to $backup"
        mv "$target" "$backup"
    fi
    ln -s "$src" "$target"
    echo "zen-profile: linked $target -> $src"
}

for name in "${ENTRIES[@]}"; do
    link_entry "$name"
done
