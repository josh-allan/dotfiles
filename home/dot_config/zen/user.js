// Applied over prefs.js on every Zen start. Mod settings changed in Zen's UI
// revert on restart unless copied here.

// userChrome.css / userContent.css (Catppuccin Mocha theme in chrome/).
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Mod: Better Find Bar
user_pref("theme-better_find_bar-enable_custom_background", false);
user_pref("theme.better_find_bar.custom_background", "#112233");
user_pref("theme.better_find_bar.hide_find_status", false);
user_pref("theme.better_find_bar.hide_found_matches", false);
user_pref("theme.better_find_bar.hide_highlight", "not_hide");
user_pref("theme.better_find_bar.hide_match_case", "not_hide");
user_pref("theme.better_find_bar.hide_match_diacritics", "not_hide");
user_pref("theme.better_find_bar.hide_whole_words", "not_hide");
user_pref("theme.better_find_bar.horizontal_position", "default");
user_pref("theme.better_find_bar.instant_animations", false);
user_pref("theme.better_find_bar.textbox_width", "800");
user_pref("theme.better_find_bar.transparent_background", true);
user_pref("theme.better_find_bar.vertical_position", "default");

// Mod: Better Tab Indicators
user_pref("uc.tabs.custom_color_hex", "#ffffff");
user_pref("uc.tabs.dim_unloaded", false);

// Mod: Audio Indicator Enhanced
user_pref("zen.mods.AudioIndicatorEnhanced.audioWave.colorMuted", "color-mix(in srgb, -moz-dialogtext 50%, rgb(129, 0, 0) 50%)");
user_pref("zen.mods.AudioIndicatorEnhanced.audioWave.colorPlaying", "-moz-dialogtext");
user_pref("zen.mods.AudioIndicatorEnhanced.audioWave.enabled", false);
user_pref("zen.mods.AudioIndicatorEnhanced.audioWave.opacity", "0.2");
user_pref("zen.mods.AudioIndicatorEnhanced.bigEssentialIcons.enabled", false);
user_pref("zen.mods.AudioIndicatorEnhanced.hoverScaleAnimationEnabled", true);
user_pref("zen.mods.AudioIndicatorEnhanced.returnOldIcons", true);
user_pref("zen.mods.AudioIndicatorEnhanced.reverseAudioIcons", false);
