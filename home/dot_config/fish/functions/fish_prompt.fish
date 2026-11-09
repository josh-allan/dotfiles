function fish_prompt
    set -l last_status $status
    if contains -- --final-rendering $argv
        printf '%s%s %s› %s' (set_color $_prompt_overlay0) (date +%H:%M:%S) (set_color -o $_prompt_lavender) (set_color normal)
        return
    end

    set -l duration_ms 0
    set -q CMD_DURATION[1]; and set duration_ms $CMD_DURATION

    # Fit line 1 to the terminal: shorten the path, then drop the time, then show only the leaf.
    set -l right (_prompt_status $last_status $duration_ms yes)
    set -l left (_prompt_breadcrumb full)
    _prompt_fits "$left" "$right"; or set left (_prompt_breadcrumb short)
    _prompt_fits "$left" "$right"; or set right (_prompt_status $last_status $duration_ms no)
    _prompt_fits "$left" "$right"; or set left (_prompt_breadcrumb leaf)

    set -q _prompt_blank_line; and echo
    # Pad to COLUMNS - 1 so the line never fills the last column and wraps.
    set -l pad (math $COLUMNS - 1 - (string length --visible -- "$left$right"))
    if test $pad -lt 1
        set right ''
        set pad 1
    end
    printf '%s%s%s%s\n' "$left" (string repeat -n $pad ' ') "$right" (set_color normal)

    _prompt_caret $last_status
end

function _prompt_fits --argument-names left right
    test (string length --visible -- "$left$right") -le (math $COLUMNS - 3)
end
