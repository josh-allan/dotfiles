set -g tide_prompt_add_newline true

# Tokyo Night color scheme for tide prompt
set -g tide_prompt_color_separator_same_color 8F8AAC
set -g tide_prompt_color_separator_same_color_color 8F8AAC
set -g tide_prompt_icon_connection ' '
set -g tide_prompt_min_cols 34
set -g tide_prompt_pad_items true

# Left prompt items configuration
set -g tide_left_prompt_items pwd git character
set -g tide_pwd_bg_color 1F202A
set -g tide_pwd_color_anchors BB9AF7
set -g tide_pwd_color_dirs BB9AF7
set -g tide_pwd_color_truncated_dirs BB9AF7

# Git configuration
set -g tide_git_bg_color 24283B
set -g tide_git_bg_color_unstable 24283B
set -g tide_git_color_branch 7AA2F7
set -g tide_git_color_conflicted F7768E
set -g tide_git_color_dirty E0AF68
set -g tide_git_color_staged 9ECE6A
set -g tide_git_color_stash BB9AF7
set -g tide_git_color_operation_icon F7768E
set -g tide_git_truncation_length 20

# Character configuration (prompt symbol)
set -g tide_character_color 9ECE6A
set -g tide_character_color_failure F7768E
set -g tide_character_icon '❯'
set -g tide_character_vi_icon_default '❮'
set -g tide_character_vi_icon_replace '▶'
set -g tide_character_vi_icon_visual V

# Right prompt items configuration
set -g tide_right_prompt_items status cmd_duration time

# Time configuration
set -g tide_time_bg_color 1F202A
set -g tide_time_color 7AA2F7
set -g tide_time_format '%H:%M:%S' # 24-hour format

# Status configuration
set -g tide_status_bg_color 1F202A
set -g tide_status_bg_color_failure 1F202A
set -g tide_status_color 9ECE6A
set -g tide_status_color_failure F7768E

# Command duration configuration
set -g tide_cmd_duration_bg_color 1F202A
set -g tide_cmd_duration_color 7AA2F7
