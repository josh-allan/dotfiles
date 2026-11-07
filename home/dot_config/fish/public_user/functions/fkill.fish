function fkill --description "fzf-select processes by name pattern, then kill"
    if test (count $argv) -lt 1
        echo 'USAGE: fkill "<pattern>" ["signal"]'
        return 1
    end

    set -l pattern $argv[1]
    set -l sig "SIGTERM"

    if test (count $argv) -ge 2
        set sig $argv[2]
    end

    set -l pids (pgrep -f "$pattern")

    if test -z "$pids"
        echo "No processes matching: $pattern"
        return 1
    end

    echo "Processes matching '$pattern':"
    echo ""

    for pid in $pids
        ps -p $pid -o pid,ppid,user,%cpu,%mem,start,comm,args 2>/dev/null | tail -n +2
    end

    echo ""
    read -P "Kill these PIDs with $sig? Type 'yes' to confirm: " confirm

    if test "$confirm" = "yes"
        for pid in $pids
            kill -$sig $pid 2>/dev/null; and echo "Sent $sig to $pid" || echo "Failed: $pid"
        end
    else
        echo "Aborted."
    end
end
