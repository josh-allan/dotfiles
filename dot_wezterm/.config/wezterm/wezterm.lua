local wezterm = require("wezterm")
local keys = require("key")

local config = {}

if wezterm.config_builder then
	config = wezterm.config_builder()
end

config.font_size = 12.0
config.line_height = 1.2

-- config.window_decorations = "RESIZE"
config.initial_rows = 45
config.initial_cols = 200

config.use_fancy_tab_bar = false
config.show_new_tab_button_in_tab_bar = false
config.tab_max_width = 22
config.tab_bar_at_bottom = true

--config.front_end = "WebGpu"
config.keys = keys
config.window_padding = {
	left = 0,
	right = 0,
	top = 0,
	bottom = 0,
}
config.font = wezterm.font("Fira Code")
config.font = wezterm.font("JetBrains Mono", { weight = "Bold" })

config.color_scheme = "Tokyo Night"
config.colors = require("color")
config.window_background_opacity = 0.8
config.enable_wayland = false
--config.macos_window_background_blur = 75

local function tab_title(tab_info)
	local title = tab_info.tab_title

	if title and #title > 0 then
		return title
	end

	return tab_info.active_pane.title
end

wezterm.on("format-tab-title", function(tab, tabs, panes, cf, hover, max_width)
	local title = tab_title(tab)

	title = wezterm.truncate_left(title, max_width)
	local i = tab.tab_index + 1

	title = string.format(" %d %s ", i, title)

	local background = "rgb(22, 24, 26 / 20%)"
	local foreground = "white"

	if tab.is_active then
		background = "rgb(22, 24, 26 / 90%)"
		foreground = "white"
	end

	return {
		{ Background = { Color = "black" } },
		{ Foreground = { Color = "black" } },
		{ Text = "" },
		{ Background = { Color = background } },
		{ Foreground = { Color = foreground } },
		{ Text = title },
		{ Background = { Color = "black" } },
		{ Foreground = { Color = "black" } },
		{ Text = "" },
	}
end)

return config
