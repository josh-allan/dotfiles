set -gx FISH_HOME $HOME/.config/fish
set -gx BAT_THEME Dracula
set -gx SUDO_EDITOR nvim
set -gx GOPRIVATE github.com/10gen
set -gx PYENV_ROOT $HOME/.pyenv
set -gx PIPX_DEFAULT_PYTHON (pyenv prefix)/bin/python
set -gx GPG_TTY $(tty)
set -gx KUBECONFIG "$HOME/.kube/config.prod:$HOME/.kube/config.staging"

set -gx VASA_HOME $HOME/.vasa
