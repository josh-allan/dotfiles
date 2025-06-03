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
