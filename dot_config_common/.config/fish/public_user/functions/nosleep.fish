# Toggle macOS system sleep. Works around a hardware crash on entering deep sleep
# (ResetCounter "rst crash,crash_n"): with sleep disabled the display still turns
# off, but the SoC never enters the deep sleep state that triggers the reset.
function nosleep --description 'nosleep [on|off|status]: disable/enable macOS system sleep (incl. lid close)'
    if test (uname) != Darwin
        echo "nosleep: macOS only" >&2
        return 1
    end

    switch "$argv[1]"
        case on
            sudo pmset -a disablesleep 1 sleep 0
            and echo "nosleep: ON — system will not sleep (lid close included). Display still sleeps."
        case off
            sudo pmset -a disablesleep 0 sleep 1
            and echo "nosleep: OFF — normal sleep restored."
        case '' status
            if pmset -g | string match -qr 'SleepDisabled\s+1'
                echo "nosleep: ON (sleep disabled)"
            else
                echo "nosleep: OFF (normal sleep)"
            end
        case '*'
            echo "usage: nosleep [on|off|status]" >&2
            return 2
    end
end
