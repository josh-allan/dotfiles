# Prompt colours: Catppuccin Mocha. Change these hex values to switch flavour.
set -g _prompt_text cdd6f4
set -g _prompt_overlay1 7f849c
set -g _prompt_overlay0 6c7086
set -g _prompt_surface2 585b70
set -g _prompt_lavender b4befe
set -g _prompt_mauve cba6f7
set -g _prompt_green a6e3a1
set -g _prompt_red f38ba8
set -g _prompt_yellow f9e2af
set -g _prompt_peach fab387

status is-interactive || return

set -g fish_transient_prompt 1

# Async git state: each new prompt starts a worker that writes its result to this file and
# sends SIGUSR1. Universal variables would avoid the file, but `fish --no-config` cannot set them.
set -g _prompt_git_seq 0
set -l tmp /tmp
set -q TMPDIR; and set tmp (string trim -r -c / -- $TMPDIR)
set -g _prompt_git_file $tmp/fish_prompt_git_$fish_pid

function _prompt_git_start --on-event fish_prompt
    set -g _prompt_git_seq (math $_prompt_git_seq + 1)
    set -l root (command git rev-parse --show-toplevel 2>/dev/null); or return
    command git -C $root rev-parse -q --verify HEAD >/dev/null; or return
    set -l worker (functions --details _prompt_git_worker)
    set -l fish_bin (status fish-path)
    $fish_bin --no-config -c 'source $argv[1]; _prompt_git_worker $argv[2..]' \
        $worker $_prompt_git_seq $root $_prompt_git_file $fish_pid &
    builtin disown
end

function _prompt_git_ready --on-signal SIGUSR1
    set -l result (command cat $_prompt_git_file 2>/dev/null); or return
    # Drop results from workers that a newer prompt has superseded.
    test "$result[1]" = "$_prompt_git_seq"; or return
    set -g _prompt_git_state $result[2..]
    commandline -f repaint
end

function _prompt_after_command --on-event fish_postexec
    set -g _prompt_blank_line
end

function _prompt_resize --on-variable COLUMNS
    commandline -f repaint
end

function _prompt_cleanup --on-event fish_exit
    command rm -f $_prompt_git_file
end
