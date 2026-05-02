function fp --description "fzf-select a process to kill or inspect"
    if test (count $argv) -gt 1
        echo 'USAGE: fp ["kill"]'
        return 1
    end

    set -l action "kill"
    if test (count $argv) -eq 1
        set action $argv[1]
    end

    ps -eo pid,user,%cpu,%mem,command \
        | awk 'NR==1 {next} {
            pid=$1; user=$2; cpu=$3; mem=$4;
            cmd=""; for(i=5;i<=NF;i++) cmd=cmd (i>5?" ":"") $i;
            n=split(cmd, parts, "/");
            basename=parts[n];
            sub(/ .*/, "", basename);
            printf "%-7s %-10s %5s %5s  %s\n", pid, user, cpu, mem, basename;
        }' \
        | fzf --header 'enter: kill ╱ ctrl-s: inspect in less' \
              --ansi \
              --preview 'ps -p {1} -o pid,ppid,user,%cpu,%mem,start,comm,args 2>/dev/null | tail -n +2' \
              --preview-window=right:60% \
              --bind "enter:become(kill -9 {1})" \
              --bind "ctrl-s:execute(ps -p {1} -o pid,ppid,user,%cpu,%mem,vsz,rss,tt,stat,start,time,command | less)"
end
