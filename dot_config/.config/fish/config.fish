set -g fish_greeting

if status is-interactive
    for config in $__fish_config_dir/user/**/*.fish
        source $config
    end
end

zoxide init fish --cmd cd | source
direnv hook fish | source
pyenv init - fish | source
export PATH="$HOME/.local/bin:$PATH"

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH

# opencode
fish_add_path /Users/josh/.opencode/bin
