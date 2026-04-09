function dr
    docker restart $(docker ps -a -q)
end 

function dclean
    docker rm -v $(docker ps --filter status=exited -q 2>/dev/null) 2>/dev/null
    docker rmi $(docker images --filter dangling=true -q 2>/dev/null) 2>/dev/null
end

function dockerupdate
    docker-compose pull $(docker images --filter "dangling=false" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null)
end

function dsh --description "Exec into a running container (bash, falls back to sh)"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --preview 'docker logs --tail 20 {1}' \
              --preview-window=right:60% \
              --bind 'enter:become(sh -c "docker exec -it {1} bash 2>/dev/null || docker exec -it {1} sh")'
end

function dlog --description "Stream logs from a container (enter: follow, ctrl-o: open in nvim)"
    docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --header 'enter: follow logs ╱ ctrl-o: open in nvim' \
              --preview 'docker logs --tail 50 {1}' \
              --preview-window 'right:60%' \
              --bind 'enter:become(docker logs --follow --tail 100 {1})' \
              --bind 'ctrl-o:execute(nvim <(docker logs {1}))'
end

function dstop --description "Stop a running container"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --preview 'docker logs --tail 20 {1}' \
              --preview-window=right:60% \
              --bind 'enter:become(docker stop {1})'
end

function dprune --description "Full docker system prune with confirmation"
    echo "This will remove:"
    docker system df
    echo ""
    read -P "Type 'prune' to confirm full system prune: " confirm
    if test "$confirm" = prune
        docker system prune --volumes -f
    else
        echo "Aborted."
    end
end
