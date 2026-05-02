function load_env
    set verbose 0
    set env_file ".env"

    # Parse arguments
    for arg in $argv
        switch $arg
            case "--verbose" "-v"
                set verbose 1
            case '*'
                set env_file $arg
        end
    end

    if not test -f $env_file
        if test $verbose -eq 1
            echo "No .env file found at: $env_file"
        end
        return 0
    end

    if test $verbose -eq 1
        echo "Loading environment variables from: $env_file"
    end

    for line in (grep -v '^#' $env_file | sed '/^\s*$/d')
        set key (echo $line | cut -d '=' -f 1)
        set value (echo $line | cut -d '=' -f 2-)
        set -gx $key "$value"
        if test $verbose -eq 1
            echo "Exported $key"
        end
    end
end
