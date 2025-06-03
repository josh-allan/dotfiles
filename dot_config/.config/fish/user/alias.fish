alias brew="env PATH=(string replace (pyenv root)/shims '' \"\$PATH\") brew" # Ref: https://github.com/pyenv/pyenv#:~:text=root)%5C/shims%3A/%7D%22%20brew%27-,Fish,-%3A

# eza-related aliases
alias ls='eza -F --group-directories-first --icons --color-scale'
alias l='eza -lF --group-directories-first --icons --color-scale'
alias ll='eza -laF --group-directories-first --icons --color-scale --git --time-style long-iso'
alias tree='eza -F --group-directories-first --icons --color-scale --tree -L 2'
alias reload='source ~/.config/fish/config.fish'
alias fzf="fzf --style full --preview 'bat {}' --bind 'enter:become(nvim {})'"


# CD Aliases:
set GITLOCAL "$HOME/git"
set CONFIGLOCAL "$HOME/.config"
alias cdconf="cd $CONFIGLOCAL"
alias cddesk="cd $HOME/Desktop"
alias cddev="cd $HOME/dev"
alias cdh="cd $HOME"
alias cdgit="cd $GITLOCAL"
alias cddl="cd $HOME/Downloads"
alias cddoc="cd $HOME/docker"
alias cddot="cd $HOME/.dotfiles"
alias cdhypr="cd $CONFIGLOCAL/hypr"
alias cdlab="cd $HOME/labset"
alias cdzdot="cd $HOME/.oh-my-zsh/custom"
alias cdi3="cd $CONFIGLOCAL/i3"
alias cdsway="cd $CONFIGLOCAL/sway"
alias cdnvim="cd $CONFIGLOCAL/nvim"
alias cdup="cd .."
alias cdway="cd $CONFIGLOCAL/waybar"
alias cdnvconf="cd $CONFIGLOCAL/nvim/lua/custom"
