# Runs in a background `fish --no-config`. Writes one value per line to `file`, then signals the
# shell that started it: seq root ins del files op unmerged ahead behind target conflict.
# op and target are `-` when absent; target is also `-` for the upstream.
function _prompt_git_worker --argument-names seq root file pid
    set -l stat (command git -C $root diff --shortstat HEAD 2>/dev/null); or return
    set -l files (string match -rg '(\d+) files? changed' -- $stat); or set files 0
    set -l ins (string match -rg '(\d+) insertion' -- $stat); or set ins 0
    set -l del (string match -rg '(\d+) deletion' -- $stat); or set del 0

    set -l op (_prompt_git_worker_op $root)
    set -l unmerged (command git -C $root diff --name-only --diff-filter=U 2>/dev/null | count)

    set -l ahead 0
    set -l behind 0
    set -l label -
    set -l conflict 0
    set -l target (_prompt_git_worker_target $root)
    if test "$op" = -; and set -q target[1]
        set label $target[2]
        set -l counts (command git -C $root rev-list --left-right --count $target[1]...HEAD 2>/dev/null | string split \t)
        if set -q counts[2]
            set behind $counts[1]
            set ahead $counts[2]
        end
        # Ahead only or behind only cannot conflict; only a diverged branch needs the trial merge.
        if test $ahead -gt 0 -a $behind -gt 0
            command git -C $root merge-tree --write-tree --quiet HEAD $target[1] >/dev/null 2>&1
            test $status -eq 1; and set conflict 1
        end
    end

    printf '%s\n' $seq $root $ins $del $files $op $unmerged $ahead $behind $label $conflict >$file.tmp
    and command mv -f $file.tmp $file
    and kill -USR1 $pid
end

# REBASE, MERGE, CHERRY-PICK or REVERT while one is stopped, else `-`.
function _prompt_git_worker_op --argument-names root
    set -l paths (command git -C $root rev-parse --path-format=absolute \
        --git-path rebase-merge --git-path rebase-apply --git-path MERGE_HEAD \
        --git-path CHERRY_PICK_HEAD --git-path REVERT_HEAD 2>/dev/null)
    if test -e "$paths[1]" -o -e "$paths[2]"
        echo REBASE
    else if test -e "$paths[3]"
        echo MERGE
    else if test -e "$paths[4]"
        echo CHERRY-PICK
    else if test -e "$paths[5]"
        echo REVERT
    else
        echo -
    end
end

# Drift target ref and its label: the upstream (label `-`), else the remote default branch
# (label its short name), unless HEAD is detached or already that branch. Prints nothing if none.
function _prompt_git_worker_target --argument-names root
    set -l branch (command git -C $root symbolic-ref -q --short HEAD); or return
    if set -l upstream (command git -C $root rev-parse -q --verify --symbolic-full-name '@{upstream}' 2>/dev/null)
        printf '%s\n' $upstream -
        return
    end
    set -l default (command git -C $root symbolic-ref -q refs/remotes/origin/HEAD)
    or for ref in refs/remotes/origin/main refs/remotes/origin/master
        command git -C $root rev-parse -q --verify $ref >/dev/null; and set default $ref; and break
    end
    set -q default[1]; or return
    set -l name (string replace refs/remotes/origin/ '' -- $default)
    test "$name" = "$branch"; and return
    printf '%s\n' $default $name
end
