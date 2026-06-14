if not status is-interactive
    exit
end

function _drift_check --on-event fish_prompt
    set -l state_file ~/.cache/dotfiles/drift-state
    if not test -f $state_file
        return
    end

    set -l pending (string match -rg 'pending=(\d+)' <$state_file)
    if test -z "$pending" -o "$pending" -eq 0
        return
    end

    set -l ts (string match -rg 'timestamp=(.+)' <$state_file)
    set -l age_text ""
    set -l age_sec 0
    if test -n "$ts"
        set -l now (date +%s)
        set -l then (date -d "$ts" +%s 2>/dev/null; or echo 0)
        set age_sec (math "$now - $then")
        if test "$age_sec" -lt 3600
            set age_text " (just now)"
        else if test "$age_sec" -lt 86400
            set age_text " ("(math "floor($age_sec / 3600)")"h ago)"
        else if test "$age_sec" -lt 604800
            set age_text " ("(math "floor($age_sec / 86400)")"d ago)"
        else
            set age_text " (old)"
        end
    end

    if test "$age_sec" -lt 86400
        set_color brred
    else
        set_color bryellow
    end
    echo -n "drift: $pending$age_text (run check-compliance.sh)"
    set_color normal
    echo
end
