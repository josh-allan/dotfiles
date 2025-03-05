# uncomment if profiling is needed
#zmodload zsh/zprof


zstyle :compinstall filename '$HOME/.zshrc'
# fix slow shell loads 
autoload -Uz compinit
 for dump in ~/.zcompdump(N.mh+24); do
   compinit
 done
 compinit -C

 zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

autoload -U up-line-or-beginning-search
autoload -U down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

PS1='%m %~ $ '
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

setopt APPEND_HISTORY # adds history
setopt COMPLETE_IN_WORD
setopt CORRECT
setopt EXTENDED_HISTORY # add timestamps to history
setopt HIST_IGNORE_ALL_DUPS  # don't record dupes in history
setopt HIST_REDUCE_BLANKS
setopt INC_APPEND_HISTORY SHARE_HISTORY  # adds history incrementally and share it across sessions
setopt LIST_TYPES
setopt NO_BEEP
setopt PROMPT_SUBST
setopt SHARE_HISTORY # share history between sessions ???
unset BEEP #remove the beep

# Remove the annoying and wildly unhelpful autocorrect that zsh ships with by default
unsetopt correct_all


bindkey '^[^[[1;3D' backward-word
bindkey '^[^[[1;3C' forward-word
bindkey '^[[1;5D' beginning-of-line
bindkey '^[[1;5C' end-of-line
bindkey '^[[1;3~' delete-char
bindkey '^?' backward-delete-char
bindkey '^[[A' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search


# ALIASES:

alias cat='bat' #extended cat functionality
alias cdd='cd ../'
alias cddd='cd ../../'
alias cls='clear' #linux clear screen functionality
alias diskspace='~/diskspace.sh'
alias dk='ssh desktop'
alias ga="git add ."
alias gc='git commit -m' #git committer
alias gco='git checkout'
alias gcob='git checkout -b'
alias gp='git push' #git pusher
alias goimports='goimports-reviser'
alias grep='rg'
alias h='history | grep' #history grepper
alias hl="dbus-launch Hyprland"
alias ll='eza -lh'
alias ls='eza -lah'
alias mkdir='mkdir -pv' #make parent directory in verbose mode
alias mktar='tar -czvf'
alias reload='source ~/.zshrc' #reload the shell config
alias sdn='shutdown now'
alias sdr='sudo reboot now'
alias tf='terraform'
alias tree='eza -Tlh --git'
alias updt='sudo aura -Syu && sudo -aura -Auax'
alias vim='nvim' #replace vim with neovim
alias yeet='sudo reboot now'

# CD Aliases:
GITLOCAL="$HOME/git"
CONFIGLOCAL="$HOME/.config"
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

# Functions
function mcd() { # mcd: Makes new Dir and jumps inside
  mkdir -p "$1" && cd "$1"
}

function my-ps() { # my_ps: List processes owned by my user:
  ps "$@" -u "$USER" -o pid,%cpu,%mem,start,time,bsdtime,command
}

function myip() { # myip: prints out your current IP
  echo "My WAN/Public IP address: $(dig +short myip.opendns.com @resolver1.opendns.com)"
}

function diskspace() { #lazily check for available disk space
    du -ah $1 | grep -v "/$" | sort -rh | less
}

function addkey() {
  id_rsa="${HOME}/.ssh/id_rsa"
  id_ed25519="${HOME}/.ssh/id_ed25519"
  if [[ -f "${id_rsa}" ]]; then
    key_file=${id_rsa}
  elif [[ -f "${id_ed25519}" ]]; then
    key_file=${id_ed25519}
  else
    echo "key file not defined"
    exit 1
  fi

  ssh-add -K ${key_file}
}

function push() {
    upstream=$(git branch | sed -n '/\* /s///p')
    git push origin ${upstream} $@
}

# @COMMAND fetch                            git fetch and git pull from origin
function fetch() {
    upstream=$(git branch | sed -n '/\* /s///p')
    git fetch && git pull origin ${upstream}
}

function forcekill() {
    kill `ps ax | grep -i $1 | awk '{ print $1 }'`
}

export STARSHIP_CONFIG=~/.config/starship/starship.toml
eval "$(starship init zsh)"

# ex - archive extractor
# usage: ex <file>
function extract ()
{
  if [ -f $1 ] ; then
    case $1 in
      *.tar.bz2)   tar xjf $1   ;;
      *.tar.gz)    tar xzf $1   ;;
      *.bz2)       bunzip2 $1   ;;
      *.rar)       unrar x $1   ;;
      *.gz)        gunzip $1    ;;
      *.tar)       tar xf $1    ;;
      *.tbz2)      tar xjf $1   ;;
      *.tgz)       tar xzf $1   ;;
      *.zip)       unzip $1     ;;
      *.Z)         uncompress $1;;
      *.7z)        7z x $1      ;;
      *)           echo "'$1' cannot be extracted via ex()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

function addToPath() {
    if [[ "$PATH" != *"$1"* ]]; then
        export PATH=$PATH:$1 >> ~/.zshrc
    fi
}

function addToPathFront() {
    if [[ "$PATH" != *"$1"* ]]; then
        export PATH=$1:$PATH
    fi
}

export EDITOR='nvim'
export SUDO_EDITOR="nvim"
alias "sudoedit"='function _sudoedit(){sudo -e "$1";};_sudoedit'

export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - zsh)"

eval "$(zoxide init zsh --cmd cd)"

export GPG_TTY=$(tty)

function nvm() {
  echo "NVM not loaded! Loading now..."
  unset -f nvm
  export NVM_PREFIX="$HOME/.nvm"
  [ -s "$NVM_PREFIX/nvm.sh" ] && . "$NVM_PREFIX/nvm.sh"
  nvm "$@"
}

zstyle ':completion:*' menu select
fpath+=~/.zfunc

path+=('/Users/$USERNAME/.local/bin','')
export GOPATH=$HOME/dev/go
export WEZPATH="$PATH:/Applications/WezTerm.app/Contents/MacOS"
export PATH=/Library/Frameworks/Python.framework/Versions/3.10/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/go/bin:/Library/Apple/usr/bin:/Users/$USERNAME/.local/bin:/Users/$USERNAME/Documents/git/devbox/modules/cli/bin:/Users/$USERNAME/Documents/git/devbox/cli/bin:~/bin:$GOROOT/bin:$GOPATH/bin:/Users/$USERNAME/.cargo/bin:$WEZPATH/bin
alias brew='env PATH="${PATH//$(pyenv root)\/shims:/}" brew'
# uncomment if profiling is needed
#zprof
