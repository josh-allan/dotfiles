-- Hyprland configuration (Lua). Ported from hyprland.conf.
-- Only hyprland itself reads this file; hypridle/hyprlock/hyprpaper/hyprsunset
-- remain in their own *.conf files (those binaries do not support Lua).

hl.env("XCURSOR_SIZE", "24")
hl.env("WLR_NO_HARDWARE_CURSORS", "1")

require("monitors")
require("workspaces")

-- Host-specific overrides (env, extra monitors). Optional: absent on some hosts.
pcall(require, "host")

hl.on("hyprland.start", function()
	hl.exec_cmd("hyprctl dispatch workspace 1")
	hl.exec_cmd("hyprswitch init &")
	hl.exec_cmd("hyprsunset")
	hl.exec_cmd("udiskie --tray")
	hl.exec_cmd("hypridle")
	hl.exec_cmd("wl-clipboard-history -t")
	hl.exec_cmd("/home/josh/.cargo/bin/wayle panel start")
	hl.exec_cmd("/usr/lib/polkit-kde-authentication-agent-1")
	hl.exec_cmd("hyprpaper")
	hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
	hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
end)

hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 3,
		border_size = 2,
		col = {
			active_border = 0xff7c94bf,
			inactive_border = 0x00ffffff,
		},
	},

	decoration = {
		rounding = 3,
	},

	dwindle = {
		force_split = 2, -- always on the right/bottom
		preserve_split = true,
	},

	misc = {
		disable_hyprland_logo = true,
	},

	debug = {
		disable_logs = false,
	},

	animations = {
		enabled = true,
	},
})

hl.config({
	input = {
		kb_layout = "us",
		natural_scroll = true,
		sensitivity = 0,
		touchpad = {
			natural_scroll = true,
			tap_to_click = true,
			disable_while_typing = true,
		},
	},
})

hl.curve("myBezier", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.05 } } })

hl.animation({ leaf = "windows", enabled = true, speed = 7, bezier = "myBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 7, bezier = "default", style = "popin 80%" })
hl.animation({ leaf = "border", enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "fade", enabled = true, speed = 7, bezier = "default" })

require("keybinds")

hl.bind("CTRL + SHIFT + R", hl.dsp.exec_cmd("wayle"))
