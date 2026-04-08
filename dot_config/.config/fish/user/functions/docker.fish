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
    set container (docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --preview 'docker logs --tail 20 {1}' --preview-window=right:60% \
        | awk '{print $1}')
    test -z "$container"; and return
    docker exec -it $container bash 2>/dev/null; or docker exec -it $container sh
end

function dlog --description "Tail logs from a container"
    set container (docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --preview 'docker logs --tail 30 {1}' --preview-window=right:60% \
        | awk '{print $1}')
    test -n "$container"; and docker logs -f $container
end

function dstop --description "Stop a running container"
    set container (docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 \
        | fzf --preview 'docker logs --tail 20 {1}' --preview-window=right:60% \
        | awk '{print $1}')
    test -n "$container"; and docker stop $container
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
