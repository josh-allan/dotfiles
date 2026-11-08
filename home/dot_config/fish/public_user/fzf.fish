##### OPTIONS #####

set fzf_preview_dir_cmd eza --all --color=always
set fzf_diff_highlighter delta --paging=never --width=20
set fzf_preview_file_cmd bat --style=plain

fzf_configure_bindings \
    --directory=\cf \
    --processes=\cp \
    --history=\cr \
    --git_status=\ct \
    --git_log=\cl \
    --variables=\ev

set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
set -gx FZF_DEFAULT_OPTS "\
    --keep-right
    --height=60%
    --info=inline
    --layout=reverse
    --color=bg+:#313244,bg:#1E1E2E,spinner:#F5E0DC,hl:#F38BA8
    --color=fg:#CDD6F4,header:#F38BA8,info:#CBA6F7,pointer:#F5E0DC
    --color=marker:#B4BEFE,fg+:#CDD6F4,prompt:#CBA6F7,hl+:#F38BA8
    --color=selected-bg:#45475A
    --color=border:#6C7086,label:#CDD6F4
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
    --color=bg+:#313244,bg:#1E1E2E,spinner:#F5E0DC,hl:#F38BA8
    --color=fg:#CDD6F4,header:#F38BA8,info:#CBA6F7,pointer:#F5E0DC
    --color=marker:#B4BEFE,fg+:#CDD6F4,prompt:#CBA6F7,hl+:#F38BA8
    --color=selected-bg:#45475A
    --color=border:#6C7086,label:#CDD6F4
    --bind=tab:down,btab:up
    --bind='alt-k:preview-up,alt-p:preview-up'
    --bind='alt-j:preview-down,alt-n:preview-down'
    --bind='alt-w:toggle-preview-wrap'
    --bind='?:toggle-preview'
    --cycle
    --ansi
 "
