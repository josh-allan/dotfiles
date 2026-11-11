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
local rex_actions = {}
local current_process = { foreground = { name = "nvim" } }
local process_error
local focus_calls = {}
local focus_result = { revision = 7 }
rex = {
	bind = function(key, action, ...)
		assert(not rex_bindings[key], "duplicate Rex binding: " .. key)
		rex_bindings[key] = { action = action, args = (...), argument_count = select("#", ...) }
	end,
	action = function(spec)
		assert(not rex_actions[spec.name], "duplicate Rex action: " .. spec.name)
		assert(type(spec.run) == "function", "action without run: " .. spec.name)
		rex_actions[spec.name] = spec
	end,
	block = {
		call = function(creator, method, args)
			assert(creator == "com.superlogical.terminal")
			assert(method == "process")
			assert(args.block_id == "block:test")
			if process_error then
				return nil, process_error
			end
			return current_process
		end,
	},
	session = {
		focus_direction = function(args)
			table.insert(focus_calls, args)
			return focus_result
		end,
	},
}
package.path = repo .. "/home/dot_config/rex/?.lua;" .. package.path
dofile(repo .. "/home/dot_config/rex/init.lua")

for key, direction in pairs(directions) do
	local binding = assert(rex_bindings["cmd+" .. key], "missing Rex focus: " .. key)
	assert(type(binding.action) == "function", "Rex focus must route dynamically: " .. key)
	assert(binding.argument_count == 0, "Rex function bindings take only key and callback: " .. key)
	local context = { session_id = "session:test", block_id = "block:test" }
	local before = #focus_calls
	current_process = { foreground = { name = "nvim" } }
	assert(binding.action(context, { keybinding = "cmd+" .. key }) == false, "Neovim must receive " .. key)
	assert(#focus_calls == before, "Neovim focus must not also move a Rex pane: " .. key)

	current_process = { foreground = { name = "zsh" } }
	assert(binding.action(context, { keybinding = "cmd+" .. key }) == true, "Rex must consume a successful focus at an edge")
	local focus = assert(focus_calls[#focus_calls], "Rex did not focus a pane: " .. key)
	assert(focus_result.revision == 7, "test should model Rex succeeding without changing focus at an edge")
	assert(focus.session_id == "session:test")
	assert(focus.direction == direction)
	assert(focus.wrap == false, "Rex focus must not wrap: " .. key)
	assert(#focus_calls == before + 1, "Rex must focus at most once: " .. key)

	for _, prefix in ipairs({ "ctrl+b>", "ctrl+alt+" }) do
		local previous = assert(rex_bindings[prefix .. key], "missing existing focus: " .. prefix .. key)
		assert(previous.action == "pane.focus" and previous.args.direction == direction)
	end
	local movement = assert(rex_bindings["ctrl+alt+" .. direction], "missing Rex move: " .. direction)
	assert(movement.action == "pane.move" and movement.args.direction == direction)
end
process_error = "process details unavailable"
local focus_count = #focus_calls
local left_focus = assert(rex_bindings["cmd+h"]).action
assert(left_focus({ session_id = "session:test", block_id = "block:test" }, {}) == false)
assert(#focus_calls == focus_count, "an unknown foreground process must not trigger a second focus")
process_error = nil

local existing = {
	["ctrl+b>c"] = { "client.tab.new" },
	["ctrl+alt+c"] = { "client.tab.new" },
	["ctrl+b>v"] = { "pane.split", "right" },
	["ctrl+alt+d"] = { "pane.split", "right" },
	["ctrl+b>-"] = { "pane.split", "down" },
	["ctrl+alt+shift+d"] = { "pane.split", "down" },
	["ctrl+b>z"] = { "pane.zoom" },
	["ctrl+alt+z"] = { "pane.zoom" },
	["ctrl+b>f"] = { "pane.float" },
	["ctrl+b>a"] = { "pane.split", "auto" },
	["ctrl+b>s"] = { "session.switch" },
	["ctrl+b>shift+n"] = { "session.next" },
	["ctrl+b>shift+p"] = { "session.previous" },
	["ctrl+b>shift+h"] = { "pane.move.left" },
	["ctrl+b>shift+j"] = { "pane.move.down" },
	["ctrl+b>shift+k"] = { "pane.move.up" },
	["ctrl+b>shift+l"] = { "pane.move.right" },
	["ctrl+;"] = { "pane.zoom" },
	["cmd+;"] = { "pane.zoom" },
	["cmd+'"] = { "pane.float" },
	["ctrl+tab"] = { "client.tab.next" },
	["ctrl+shift+tab"] = { "client.tab.previous" },
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
assert(rex_bindings["alt+\\"].action == "pane.split")
assert(rex_bindings["alt+\\"].args.direction == "right")
assert(rex_bindings["alt+-"].action == "pane.split")
assert(rex_bindings["alt+-"].args.direction == "down")
local count = 0
for _ in pairs(rex_bindings) do
	count = count + 1
end
assert(count == 54, "unexpected Rex binding count: " .. count)

-- Custom actions: each key names an action init.lua's modules registered.
local custom = {
	["ctrl+b>'"] = "scratch_shell",
	["ctrl+b>g"] = "lazygit_float",
	["ctrl+b>["] = "scrollback_float",
	["ctrl+b>u"] = "attention_next",
	["ctrl+b>shift+u"] = "attention_previous",
}
for key, action in pairs(custom) do
	assert(rex_bindings[key] and rex_bindings[key].action == action, "missing custom binding: " .. key)
	assert(rex_actions[action], "binding to an unregistered action: " .. action)
end

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

local lock_count = 0
for _, binding in ipairs(hypr_bindings) do
	if binding.key == "CTRL + SUPER + Q" then
		lock_count = lock_count + 1
		assert(binding.action.name == "exec" and binding.action.args == "hyprlock")
	end
	assert(
		not (binding.key == "SUPER + L" and binding.action.name == "exec"),
		"SUPER + L must not invoke a lock command"
	)
	assert(
		not (binding.key == "CTRL + ALT + L" and binding.action.name == "exec"),
		"CTRL + ALT + L must not invoke a lock command"
	)
end
assert(lock_count == 1, "missing or duplicate CTRL + SUPER + Q lock binding")

print("Rex and Hyprland directional bindings verified")
