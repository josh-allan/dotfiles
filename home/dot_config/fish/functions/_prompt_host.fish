# Short hostname and a gap when this shell runs over SSH; nothing locally.
function _prompt_host --argument-names gap
    set -q SSH_CONNECTION; or set -q SSH_TTY; or return
    printf '%s%s%s%s' (set_color $_prompt_peach) (prompt_hostname) (set_color normal) $gap
end
