# › insert, ‹ normal (green) and visual (mauve), › replace (peach); red after a failure.
function _prompt_caret --argument-names last_status
    set -l glyph ›
    set -l color $_prompt_lavender
    if contains -- "$fish_key_bindings" fish_vi_key_bindings fish_hybrid_key_bindings
        switch $fish_bind_mode
            case default
                set glyph ‹
                set color $_prompt_green
            case visual
                set glyph ‹
                set color $_prompt_mauve
            case replace replace_one
                set color $_prompt_peach
        end
    end
    test $last_status -ne 0; and set color $_prompt_red
    printf '%s%s %s' (set_color -o $color) $glyph (set_color normal)
end
