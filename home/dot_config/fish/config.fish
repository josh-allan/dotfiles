set -g fish_greeting
set -x GPG_TTY (tty)

if status is-interactive
    for config in $__fish_config_dir/public_user/**/*.fish
       source $config
    end
    for config in $__fish_config_dir/private_user/**/*.fish
       source $config
    end
    for config in $__fish_config_dir/private_work/**/*.fish
    	source $config
    end
end

export PATH="$HOME/.local/bin:$PATH"

# mise-managed tools (chezmoi, zoxide, direnv, ...). Homebrew's mise activates itself via
# vendor_conf.d; the curl-installed mise in ~/.local/bin does not.
if command -v mise >/dev/null
    mise activate fish | source
end

zoxide init fish --cmd cd | source
direnv hook fish | source

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH

# opencode
fish_add_path $HOME/.opencode/bin
