# $PWD as a breadcrumb. mode: full (~ / .dotfiles / fish), short (~/.d/fish), leaf (fish).
function _prompt_breadcrumb --argument-names mode
    set -l parts (string replace -r -- '^'(string escape --style=regex -- $HOME)'(?=/|$)' '~' $PWD | string split /)
    # Absolute path outside $HOME: glue the leading / onto the first segment.
    if test "$parts[1]" = ''
        set -e parts[1]
        set parts[1] /$parts[1]
    end
    set -l leaf (set_color -o $_prompt_text)$parts[-1](set_color normal)
    set -l parents $parts[1..-2]

    switch $mode
        case full
            set -l sep (set_color $_prompt_surface2)' / '
            set -l dim (set_color $_prompt_overlay1)
            printf '%s' (string join -- $sep $dim$parents $leaf)
        case short
            set -l dim (set_color $_prompt_overlay1)
            set -l abbrev (string match -r -- '^/?\.?.' $parents)
            printf '%s' $dim(string join -- / $abbrev $leaf)
        case leaf
            printf '%s' $leaf
    end
end
