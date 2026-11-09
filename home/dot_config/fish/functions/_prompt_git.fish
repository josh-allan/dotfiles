# ⎇ branch +ins −del for the repo containing $PWD; fails outside a work tree.
function _prompt_git
    set -l root (command git rev-parse --show-toplevel 2>/dev/null); or return 1
    set -l branch (command git symbolic-ref --short -q HEAD; or command git rev-parse --short HEAD 2>/dev/null)
    set -l out (set_color $_prompt_mauve)"⎇ $branch"
    # _prompt_diff is set by the async worker: root, insertions, deletions.
    if test "$_prompt_diff[1]" = "$root"
        test "$_prompt_diff[2]" -gt 0; and set out $out(set_color $_prompt_green)" +$_prompt_diff[2]"
        test "$_prompt_diff[3]" -gt 0; and set out $out(set_color $_prompt_red)" −$_prompt_diff[3]"
    end
    printf '%s' $out
end
