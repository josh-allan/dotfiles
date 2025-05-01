##### OPTIONS #####

set fzf_preview_dir_cmd eza --all --color=always
set fzf_diff_highlighter delta --paging=never --width=20
set fzf_preview_file_cmd bat --style=plain

fzf_configure_bindings \
    --directory=\cf \
    --processes=\cp \
    --history=\cr \
    --git_status=\ct \
    --git_log=\cl

set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
set -gx FZF_DEFAULT_OPTS "\
    --keep-right
    --height=60%
    --info=inline
    --layout=reverse
    --color=dark
    --cycle
    --ansi
    "

# Zoxide FZF settings
set -gx _ZO_FZF_OPTS "\
    --no-sort
    --keep-right
    --height=60%
    --info=inline
    --layout=reverse
    --exit-0
    --select-1
    --bind=ctrl-z:ignore
    --preview='eza {2..} --icons -a --group-directories-first --git -F'
    --preview-window='right:60%,<100(down,30%)'
    --color=dark
    --bind=tab:down,btab:up
    --bind='alt-k:preview-up,alt-p:preview-up'
    --bind='alt-j:preview-down,alt-n:preview-down'
    --bind='alt-w:toggle-preview-wrap'
    --bind='?:toggle-preview'
    --cycle
    --ansi
 "
