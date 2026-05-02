function port --description "Show process on port, or kill it with --kill"
    if test (count $argv) -eq 0
        echo "Usage: port <number> [--kill]"
        return 1
    end
    set pid (lsof -ti tcp:$argv[1])
    if test -z "$pid"
        echo "Nothing on port $argv[1]"
        return
    end
    ps -p $pid -o pid,comm,args | tail -n +2
    if contains -- --kill $argv
        kill -9 $pid; and echo "Killed PID $pid"
    end
end
