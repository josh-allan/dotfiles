# Catppuccin Mocha everywhere a CLI tool takes a theme. fish reads the theme file from
# ~/.config/fish/themes; bat, delta, btop, lazygit and eza get theirs from chezmoi
# externals (.chezmoiexternal.toml.tmpl).
fish_config theme choose "Catppuccin Mocha"

# lazygit on macOS ignores ~/.config; point it at the Catppuccin theme layer.
set -gx LG_CONFIG_FILE $HOME/.config/lazygit/catppuccin-mocha-blue.yml
set -gx EZA_CONFIG_DIR $HOME/.config/eza
