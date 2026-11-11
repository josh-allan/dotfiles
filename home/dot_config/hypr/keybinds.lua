-- Keybindings. Ported from keybinds.conf.
-- Bind flag mapping: bindel -> {locked, repeating}, bindl -> {locked}, bindm -> {mouse}.

hl.bind(
	"XF86AudioRaiseVolume",
	hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"),
	{ locked = true, repeating = true }
)
hl.bind(
	"XF86AudioLowerVolume",
	hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),
	{ locked = true, repeating = true }
)
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })

hl.bind("F7", hl.dsp.exec_cmd("playerctl previous"), { locked = true })
hl.bind("F8", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("F9", hl.dsp.exec_cmd("playerctl next"), { locked = true })

hl.bind("F1", hl.dsp.exec_cmd("brightnessctl set 10%-"), { locked = true, repeating = true })
hl.bind("F2", hl.dsp.exec_cmd("brightnessctl set +10%"), { locked = true, repeating = true })
hl.bind("F3", hl.dsp.exec_cmd("brightnessctl -d 'kbd_backlight' set 10%-"), { locked = true, repeating = true })
hl.bind("F4", hl.dsp.exec_cmd("brightnessctl -d 'kbd_backlight' set +10%"), { locked = true, repeating = true })

hl.bind("ALT + Tab", hl.dsp.exec_cmd("hyprswitch gui --mod-key alt --key Tab"))
hl.bind("SUPER + Tab", hl.dsp.exec_cmd("hyprswitch gui --mod-key super --key Tab"))
hl.bind("CTRL + SUPER + Q", hl.dsp.exec_cmd("hyprlock"))
hl.bind("SUPER + Return", hl.dsp.exec_cmd("ghostty"))
hl.bind("SUPER + D", hl.dsp.exec_cmd("fuzzel"))
hl.bind("CTRL + SHIFT + W", hl.dsp.exec_cmd("rofi-wifi-menu"))
hl.bind("CTRL + SHIFT + B", hl.dsp.exec_cmd("rofi-bluetooth"))

hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind("SUPER + F", hl.dsp.window.fullscreen())
hl.bind("SUPER + M", hl.dsp.exit())
hl.bind("SUPER + SHIFT + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + P", hl.dsp.window.pseudo()) -- dwindle

-- Move windows with CTRL + ALT + arrows
local navigation = dofile(os.getenv("HOME") .. "/.config/keymaps/navigation.lua")
for _, binding in ipairs(navigation) do
	hl.bind("CTRL + ALT + " .. binding.direction, hl.dsp.window.move({ direction = binding.direction }))
end

-- Move focus with SUPER + hjkl
for _, binding in ipairs(navigation) do
	hl.bind("SUPER + " .. binding.key, hl.dsp.focus({ direction = binding.direction }))
end

-- Workspaces: SUPER + [0-9] to switch, SUPER + SHIFT + [0-9] to move window
for i = 1, 10 do
	local key = i % 10 -- 10 maps to key 0
	hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }))
	hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

-- Scroll through workspaces with SUPER + scroll
hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind("SUPER + mouse_up", hl.dsp.focus({ workspace = "e-1" }))

-- Move/resize with SUPER + LMB/RMB drag
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Focused output to file
hl.bind(
	"PRINT",
	hl.dsp.exec_cmd(
		[[grim -o $(hyprctl monitors | grep -B 10 'focused: yes' | grep 'Monitor' | awk '{ print $2 }') -t jpeg ~/Pictures/Screenshots/$(date +%Y-%m-%d_%H-%m-%s).jpg]]
	)
)

-- Selected region to file
hl.bind(
	"CTRL + SHIFT + PRINT",
	hl.dsp.exec_cmd([[grim -t jpeg -g "$(slurp)" ~/Pictures/Screenshots/$(date +%Y-%m-%d_%H-%m-%s).jpg]])
)

-- Selected region to clipboard
hl.bind("CTRL + SHIFT + s", hl.dsp.exec_cmd([[grim -g "$(slurp -d)" - | wl-copy]]))
