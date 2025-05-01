set -g tide_prompt_color_separator_same_color 8F8AAC
set -g tide_prompt_color_separator_same_color_color 8F8AAC
set -g tide_prompt_icon_connection ' '
set -g tide_prompt_min_cols 34
set -g tide_prompt_pad_items true

set -g tide_left_prompt_items pwd git character context newline
set -g tide_pwd_bg_color 24283B
set -g tide_pwd_color_anchors BB9AF7
set -g tide_pwd_color_dirs BB9AF7
set -g tide_pwd_color_truncated_dirs BB9AF7

set -g tide_left_prompt_separator_diff_color \uE0B0
set -g tide_right_prompt_separator_diff_color \uE0B2
set -g tide_left_prompt_separator_same_color \uE0B1
set -g tide_right_prompt_separator_same_color \uE0B3

set -g tide_left_prompt_frame_enabled true
set -g tide_right_prompt_frame_enabled true
set -g tide_prompt_color_frame_and_connection 808080

set -g tide_git_bg_color 1F202A
set -g tide_git_bg_color_unstable 1F202A
set -g tide_git_color_branch 7AA2F7
set -g tide_git_color_conflicted F7768E
set -g tide_git_color_dirty E0AF68
set -g tide_git_color_staged 9ECE6A
set -g tide_git_color_stash BB9AF7
set -g tide_git_color_operation_icon F7768E
set -g tide_git_truncation_length 20

set -g tide_character_color 9ECE6A
set -g tide_character_color_failure F7768E
set -g tide_character_icon '❯'
set -g tide_character_vi_icon_default '❮'
set -g tide_character_vi_icon_replace '▶'
set -g tide_character_vi_icon_visual V

set -g tide_right_prompt_items python time

set -g tide_time_bg_color 1F202A
set -g tide_time_color 7AA2F7
set -g tide_time_format '%H:%M:%S'
