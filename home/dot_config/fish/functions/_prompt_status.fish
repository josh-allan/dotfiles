# Right side of line 1: failure · git · time. show_time: yes or no.
function _prompt_status --argument-names last_status duration_ms show_time
    set -l parts
    if test "$last_status" -ne 0
        set -a parts (set_color $_prompt_red)"exit $last_status"(set_color $_prompt_overlay0)" after "(set_color $_prompt_yellow)(_prompt_duration $duration_ms)
    end
    set -l git (_prompt_git); and set -a parts $git
    test "$show_time" = yes; and set -a parts (set_color $_prompt_overlay0)(date +%H:%M:%S)
    printf '%s' (string join -- (set_color $_prompt_overlay0)' · ' $parts)
end
