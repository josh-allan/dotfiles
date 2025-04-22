if status is-interactive
    for config in $__fish_config_dir/user/**/*.fish
        source $config
    end
end

zoxide init fish --cmd cd | source
direnv hook fish | source
pyenv init - fish | source
