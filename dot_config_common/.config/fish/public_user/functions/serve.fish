function serve --description "Serve current directory over HTTP"
    set port (test -n "$argv[1]"; and echo $argv[1]; or echo 8000)
    echo "Serving on http://localhost:$port"
    python3 -m http.server $port
end
