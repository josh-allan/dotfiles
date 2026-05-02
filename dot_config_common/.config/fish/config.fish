set -g fish_greeting

if status is-interactive
    for config in $__fish_config_dir/public_user/**/*.fish
        source $config
    end
    for config in $__fish_config_dir/private_user/**/*.fish
        source $config
    end
end

zoxide init fish --cmd cd | source
direnv hook fish | source
export PATH="$HOME/.local/bin:$PATH"

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH

# opencode
fish_add_path $HOME/.opencode/bin
