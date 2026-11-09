# Vi modes; insert mode keeps fish's default editing keys (ctrl-a/e, ctrl-w, alt-f/b).
# Global, not universal: fish_frozen_key_bindings.fish erases the universal at startup.
set -g fish_key_bindings fish_hybrid_key_bindings

# Cursor shape shows the mode; commands start with Ghostty's default block.
set -g fish_cursor_default block
set -g fish_cursor_insert line
set -g fish_cursor_replace_one underscore
set -g fish_cursor_replace underscore
set -g fish_cursor_external block
# Block and underscore cursors sit on a character; include it in visual selections.
set -g fish_cursor_selection_mode inclusive
