# Runs in a background `fish --no-config`. Writes seq, repo root, insertions and deletions
# (one per line) to `file`, then signals the shell that started it.
function _prompt_diff_worker --argument-names seq root file pid
    set -l stat (command git -C $root diff --shortstat HEAD 2>/dev/null); or return
    set -l ins (string match -rg '(\d+) insertion' -- $stat); or set ins 0
    set -l del (string match -rg '(\d+) deletion' -- $stat); or set del 0
    printf '%s\n' $seq $root $ins $del >$file.tmp; and command mv -f $file.tmp $file
    and kill -USR1 $pid
end
