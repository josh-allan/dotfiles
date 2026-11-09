#!/usr/bin/env bash
# Links ~/.config/vesktop/{settings.json,settings/settings.json,settings/quickCss.css}
# into the Vesktop roots that do not read ~/.config/vesktop: the macOS app and the Flatpak.
set -euo pipefail

SRC_DIR="$HOME/.config/vesktop"
ROOTS=("$HOME/Library/Application Support/vesktop" "$HOME/.var/app/dev.vencord.Vesktop/config/vesktop")
ENTRIES=(settings.json settings/settings.json settings/quickCss.css)

for name in "${ENTRIES[@]}"; do
    if [[ ! -e "$SRC_DIR/$name" ]]; then
        echo "vesktop-links: $SRC_DIR/$name not found"
        exit 1
    fi
done

link_entry() {
    local src="$SRC_DIR/$2" target="$1/$2"
    mkdir -p "$(dirname "$target")"
    if [[ -L "$target" ]]; then
        [[ "$(readlink "$target")" == "$src" ]] && return 0
        rm "$target"
    elif [[ -e "$target" ]]; then
        local backup
        backup="$target.bak.$(date +%Y%m%d%H%M%S)"
        echo "vesktop-links: backing up $target to $backup"
        mv "$target" "$backup"
    fi
    ln -s "$src" "$target"
    echo "vesktop-links: linked $target -> $src"
}

for root in "${ROOTS[@]}"; do
    [[ -d "$root" ]] || continue
    for name in "${ENTRIES[@]}"; do
        link_entry "$root" "$name"
    done
done
