#!/usr/bin/env bash
set -euo pipefail

# zen-setup.sh
# Symlinks ~/.config/zen/user.js into the active Zen profile directory.
# Must run after stow has linked dot_config_linux so user.js exists at ~/.config/zen/user.js.

ZEN_DIR="$HOME/.config/zen"
PROFILES_INI="$ZEN_DIR/profiles.ini"
USER_JS_SRC="$ZEN_DIR/user.js"

if [[ ! -f "$PROFILES_INI" ]]; then
    echo "zen-setup: no profiles.ini found at $PROFILES_INI — skipping"
    exit 0
fi

if [[ ! -f "$USER_JS_SRC" ]]; then
    echo "zen-setup: user.js not found at $USER_JS_SRC — skipping (run stow first)"
    exit 1
fi

# Extract the default profile path from profiles.ini
PROFILE_PATH="$(awk -F= '/^Path=/ { path=$2 } /^Default=1/ { print path }' "$PROFILES_INI")"

if [[ -z "$PROFILE_PATH" ]]; then
    echo "zen-setup: could not determine default profile path from $PROFILES_INI"
    exit 1
fi

PROFILE_DIR="$ZEN_DIR/$PROFILE_PATH"

if [[ ! -d "$PROFILE_DIR" ]]; then
    echo "zen-setup: profile directory not found: $PROFILE_DIR"
    exit 1
fi

TARGET="$PROFILE_DIR/user.js"

if [[ -L "$TARGET" ]]; then
    current="$(readlink "$TARGET")"
    if [[ "$current" == "$USER_JS_SRC" ]]; then
        echo "zen-setup: user.js already linked correctly — skipping"
        exit 0
    fi
    rm "$TARGET"
fi

if [[ -f "$TARGET" && ! -L "$TARGET" ]]; then
    echo "zen-setup: $TARGET exists as a real file — backing up to user.js.bak"
    mv "$TARGET" "$TARGET.bak"
fi

ln -s "$USER_JS_SRC" "$TARGET"
echo "zen-setup: linked $TARGET -> $USER_JS_SRC"
