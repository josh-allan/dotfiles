function diskspace --description "Lazily check for available disk space"
    du -ah "$argv[1]" | grep -v "/\$" | sort -rh | less
end
