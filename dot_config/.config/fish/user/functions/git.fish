function gup --description "Fetch default branch and rebase current branch onto it"
    set default (git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||')
    test -z "$default"; and set default main
    git fetch origin $default; and git rebase origin/$default
end

function gri --description "Interactive rebase — fzf pick the base commit"
    git log --oneline --color=always \
        | fzf --ansi \
              --preview 'git show --stat --color=always {1}' \
              --preview-window=right:60% \
              --bind 'enter:become(git rebase -i --autosquash {1}^)'
end

function gfixup --description "Create a --fixup commit targeting a fzf-selected past commit"
    if test -z "$(git diff --cached --name-only)"
        echo "Nothing staged. Use 'git add' first."
        return 1
    end
    git log --oneline --color=always \
        | fzf --ansi \
              --prompt="fixup target> " \
              --preview 'git show --stat --color=always {1}' \
              --preview-window=right:60% \
              --bind 'enter:become(git commit --fixup={1})'
end

function gtidy --description "Interactive rebase a commit range then force-push with confirmation"
    if test (count $argv) -ne 2
        echo "Usage: gtidy <base-commit> <tip-commit>"
        echo "  Interactively rebases commits between <base-commit> and <tip-commit>,"
        echo "  then force-pushes with a confirmation prompt."
        return 1
    end

    set base $argv[1]
    set tip $argv[2]
    set branch (git branch --show-current)

    # Verify tip matches current HEAD so you can't accidentally target the wrong state
    set resolved_tip (git rev-parse $tip 2>/dev/null)
    set current_head (git rev-parse HEAD)
    if test "$resolved_tip" != "$current_head"
        echo "Abort: <tip-commit> ($tip) does not match current HEAD."
        echo "HEAD is: "(git log --oneline -1)
        return 1
    end

    # Verify remote tracking branch exists
    if not git rev-parse --verify origin/$branch >/dev/null 2>&1
        echo "Abort: no remote tracking branch 'origin/$branch'."
        return 1
    end

    # Show the commits about to be rebased
    echo "Branch:  $branch"
    echo "Range:   $base..$tip"
    echo ""
    echo "Commits to rebase:"
    git log --oneline $base..$tip
    echo ""

    git rebase -i --autosquash $base

    if test $status -ne 0
        echo ""
        echo "Rebase failed or was aborted — nothing pushed."
        return 1
    end

    # Show what the force-push will do vs remote
    echo ""
    echo "Rebase complete. Comparing with origin/$branch:"
    echo ""
    echo "Commits ahead of remote:"
    git log --oneline origin/$branch..HEAD
    echo ""
    echo "Commits on remote not in local (will be overwritten):"
    git log --oneline HEAD..origin/$branch
    echo ""

    read -P "Type '$branch' to confirm force-push, anything else to abort: " confirm
    echo ""

    if test "$confirm" = "$branch"
        git push --force-with-lease origin $branch
        and echo "Force-pushed '$branch'."
    else
        echo "Aborted. Local rebase is complete but nothing was pushed."
        return 1
    end
end

function gsw --description "Fuzzy switch git branch"
    git branch -a --format='%(refname:short)' | sed 's|origin/||' | sort -u \
        | fzf --preview 'git log --oneline --color=always {}' \
              --preview-window=right:60% \
              --bind 'enter:become(git switch {})'
end

function gstash --description "Interactively browse, apply, or drop git stashes"
    git stash list \
        | fzf --delimiter : \
              --header 'enter: apply ╱ ctrl-d: drop ╱ ctrl-s: open in nvim' \
              --preview 'git stash show -p --color=always {1}' \
              --preview-window=right:60% \
              --bind 'enter:become(git stash apply {1})' \
              --bind 'ctrl-d:become(git stash drop {1})' \
              --bind 'ctrl-s:execute(nvim <(git stash show -p {1}))'
end
