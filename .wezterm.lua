local wezterm = require("wezterm")

local config = wezterm.config_builder()

config.color_scheme = "Tokyo Night"

config.automatically_reload_config = true

config.font = wezterm.font("Fira Code")
config.font = wezterm.font("JetBrains Mono", { weight = "Bold" })

config.leader = { key = "Space", mods = "CTRL", timeout_milliseconds = 1000 }

config.window_frame = {
	-- The font used in the tab bar.
	-- Roboto Bold is the default; this font is bundled
	-- with wezterm.
	-- Whatever font is selected here, it will have the
	-- main font setting appended to it to pick up any
	-- fallback fonts you may have used there.
	font = wezterm.font({ family = "JetBrains Mono", weight = "Bold" }),

	-- The size of the font in the tab bar.
	-- Default to 10.0 on Windows but 12.0 on other systems
	font_size = 12.0,

	-- The overall background color of the tab bar when
	-- the window is focused
	active_titlebar_bg = "#333333",

	-- The overall background color of the tab bar when
	-- the window is not focused
	inactive_titlebar_bg = "#333333",
}

config.colors = {
	tab_bar = {
		-- The color of the inactive tab bar edge/divider
		inactive_tab_edge = "#575757",
	},
}

-- Some general visual things, including opacity and tab bar
config.tab_bar_at_bottom = true

config.use_fancy_tab_bar = true

config.window_background_opacity = 0.85

config.text_background_opacity = 0.85

config.keys = {
	-- command line movement
	{ key = "LeftArrow", mods = "OPT", action = wezterm.action({ SendString = "\x1bb" }) },
	{ key = "RightArrow", mods = "OPT", action = wezterm.action({ SendString = "\x1bf" }) },
	-- tab management
	{ key = "t", mods = "OPT", action = wezterm.action.SpawnTab("CurrentPaneDomain") },
	{ key = "w", mods = "OPT", action = wezterm.action.CloseCurrentTab({ confirm = true }) },
	{ key = "h", mods = "LEADER", action = wezterm.action.SplitHorizontal({ domain = "CurrentPaneDomain" }) },
	{ key = "v", mods = "LEADER", action = wezterm.action.SplitVertical({ domain = "CurrentPaneDomain" }) },

	-- pane management
	-- { }
}

return config
