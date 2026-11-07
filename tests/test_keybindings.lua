local repo = arg[1] or "."
-- Configs load each other via $HOME/.config/...; map that onto the chezmoi source
-- (home/dot_config/) so the test reads the repo, not whatever is applied on this machine.
local fake_home = "/fakehome"
local getenv = os.getenv
os.getenv = function(name)
	if name == "HOME" then
		return fake_home
	end
	return getenv(name)
end
local real_dofile = dofile
dofile = function(path)
	return real_dofile((path:gsub("^" .. fake_home .. "/%.config/", repo .. "/home/dot_config/")))
end

local directions = {
	h = "left",
	j = "down",
	k = "up",
	l = "right",
}

local rex_bindings = {}
rex = {
	bind = function(key, action, args)
		assert(not rex_bindings[key], "duplicate Rex binding: " .. key)
		rex_bindings[key] = { action = action, args = args }
	end,
}
package.path = repo .. "/home/dot_config/rex/?.lua;" .. package.path
dofile(repo .. "/home/dot_config/rex/init.lua")

for key, direction in pairs(directions) do
	local binding = assert(rex_bindings["cmd+" .. key], "missing Rex focus: " .. key)
	assert(binding.action == "pane.focus" and binding.args.direction == direction)
	for _, prefix in ipairs({ "ctrl+b>", "ctrl+alt+" }) do
		local previous = assert(rex_bindings[prefix .. key], "missing existing focus: " .. prefix .. key)
		assert(previous.action == "pane.focus" and previous.args.direction == direction)
	end
	local movement = assert(rex_bindings["ctrl+alt+" .. direction], "missing Rex move: " .. direction)
	assert(movement.action == "pane.move" and movement.args.direction == direction)
end

local existing = {
	["ctrl+b>c"] = { "client.tab.new" },
	["ctrl+alt+c"] = { "client.tab.new" },
	["ctrl+b>v"] = { "pane.split", "right" },
	["ctrl+alt+d"] = { "pane.split", "right" },
	["ctrl+b>-"] = { "pane.split", "down" },
	["ctrl+alt+shift+d"] = { "pane.split", "down" },
	["ctrl+b>z"] = { "pane.zoom" },
	["ctrl+alt+z"] = { "pane.zoom" },
	["ctrl+b>n"] = { "client.tab.next" },
	["ctrl+alt+n"] = { "client.tab.next" },
	["ctrl+b>p"] = { "client.tab.previous" },
	["ctrl+alt+b"] = { "client.tab.previous" },
	["ctrl+alt+["] = { "session.previous" },
	["ctrl+alt+]"] = { "session.next" },
}
for key, expected in pairs(existing) do
	local binding = assert(rex_bindings[key], "missing existing Rex binding: " .. key)
	assert(binding.action == expected[1], "changed action: " .. key)
	if expected[2] then
		assert(binding.args.direction == expected[2], "changed direction: " .. key)
	end
end

assert(rex_bindings["ctrl+k"].action == "session.switch")
assert(rex_bindings["ctrl+b>ctrl+b"].action == "pane.send_key")
assert(rex_bindings["ctrl+b>ctrl+b"].args.key == "ctrl+b")
assert(rex_bindings["shift+cmd+enter"].args.direction == "auto")
assert(rex_bindings["alt+shift+\\"].args.direction == "right")
assert(rex_bindings["alt+-"].args.direction == "down")
local count = 0
for _ in pairs(rex_bindings) do
	count = count + 1
end
assert(count == 35, "unexpected Rex binding count: " .. count)

local function dispatcher(name)
	return function(args)
		return { name = name, args = args }
	end
end

local hypr_bindings = {}
hl = {
	bind = function(key, action)
		hypr_bindings[#hypr_bindings + 1] = { key = key, action = action }
	end,
	dsp = {
		exec_cmd = dispatcher("exec"),
		exit = dispatcher("exit"),
		focus = dispatcher("focus"),
		window = {
			close = dispatcher("close"),
			fullscreen = dispatcher("fullscreen"),
			float = dispatcher("float"),
			pseudo = dispatcher("pseudo"),
			move = dispatcher("move"),
			drag = dispatcher("drag"),
			resize = dispatcher("resize"),
		},
	},
}
dofile(repo .. "/home/dot_config/hypr/keybinds.lua")

local function assert_hypr(key, action, direction)
	local matches = 0
	for _, binding in ipairs(hypr_bindings) do
		if binding.key == key and binding.action.name == action and binding.action.args.direction == direction then
			matches = matches + 1
		end
	end
	assert(matches == 1, "missing or duplicate Hyprland binding: " .. key)
end

for key, direction in pairs(directions) do
	assert_hypr("SUPER + " .. key, "focus", direction)
	assert_hypr("CTRL + ALT + " .. direction, "move", direction)
end

print("Rex and Hyprland directional bindings verified")
