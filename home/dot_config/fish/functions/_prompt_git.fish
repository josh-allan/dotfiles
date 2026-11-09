# ⎇ branch and one status slot for the repo containing $PWD; fails outside a work tree.
function _prompt_git
    set -l root (command git rev-parse --show-toplevel 2>/dev/null); or return 1
    set -l branch (command git symbolic-ref --short -q HEAD; or command git rev-parse --short HEAD 2>/dev/null)
    printf '%s' (set_color $_prompt_mauve)"⎇ $branch"
    # _prompt_git_state is set by the async worker; see _prompt_git_worker for the fields.
    if test "$_prompt_git_state[1]" = "$root"
        _prompt_git_slot $_prompt_git_state[2..]
    end
end

# First that applies: operation in progress, drift, diffstat. ● marks a dirty tree the slot hides.
function _prompt_git_slot --argument-names ins del files op unmerged ahead behind target conflict
    set -l slot
    if test "$op" != -
        set -a slot (set_color $_prompt_peach)" $op"
        test "$unmerged" -gt 0; and set -a slot (set_color $_prompt_red)" ✗ $unmerged"
    else if test "$ahead" -gt 0 -o "$behind" -gt 0
        test "$ahead" -gt 0; and set -a slot (set_color $_prompt_green)" ↑$ahead"
        test "$behind" -gt 0; and set -a slot (set_color $_prompt_peach)" ↓$behind"
        test "$target" != -; and set -a slot (set_color $_prompt_overlay1)" $target"
        test "$conflict" = 1; and set -a slot (set_color $_prompt_yellow)" ⚠"
    else
        test "$ins" -gt 0; and set -a slot (set_color $_prompt_green)" +$ins"
        test "$del" -gt 0; and set -a slot (set_color $_prompt_red)" −$del"
        printf '%s' $slot
        return
    end
    test "$files" -gt 0; and printf '%s' (set_color $_prompt_peach)●
    printf '%s' $slot
end
