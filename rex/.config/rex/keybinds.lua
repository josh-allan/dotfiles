local navigation = dofile(os.getenv("HOME") .. "/.config/keymaps/navigation.lua")

local bindings = {
	{ "ctrl+b>h", "pane.focus", { direction = "left" } },
	{ "ctrl+alt+h", "pane.focus", { direction = "left" } },
	{ "ctrl+b>j", "pane.focus", { direction = "down" } },
	{ "ctrl+alt+j", "pane.focus", { direction = "down" } },
	{ "ctrl+b>k", "pane.focus", { direction = "up" } },
	{ "ctrl+alt+k", "pane.focus", { direction = "up" } },
	{ "ctrl+b>l", "pane.focus", { direction = "right" } },
	{ "ctrl+alt+l", "pane.focus", { direction = "right" } },
	{ "ctrl+b>c", "client.tab.new" },
	{ "ctrl+alt+c", "client.tab.new" },
	{ "ctrl+b>v", "pane.split", { direction = "right" } },
	{ "ctrl+alt+d", "pane.split", { direction = "right" } },
	{ "ctrl+b>-", "pane.split", { direction = "down" } },
	{ "ctrl+alt+shift+d", "pane.split", { direction = "down" } },
	{ "ctrl+b>z", "pane.zoom" },
	{ "ctrl+alt+z", "pane.zoom" },
	{ "ctrl+b>n", "client.tab.next" },
	{ "ctrl+alt+n", "client.tab.next" },
	{ "ctrl+b>p", "client.tab.previous" },
	{ "ctrl+alt+b", "client.tab.previous" },
	{ "ctrl+alt+[", "session.previous" },
	{ "ctrl+alt+]", "session.next" },
	{ "ctrl+b>ctrl+b", "pane.send_key", { key = "ctrl+b" } },
	{ "shift+cmd+enter", "pane.split", { direction = "auto" } },
	{ "alt+shift+\\", "pane.split", { direction = "right" } },
	{ "alt+-", "pane.split", { direction = "down" } },
	{ "ctrl+k", "session.switch" },
}

for _, binding in ipairs(navigation) do
	table.insert(bindings, { "cmd+" .. binding.key, "pane.focus", { direction = binding.direction } })
	table.insert(bindings, { "ctrl+alt+" .. binding.direction, "pane.move", { direction = binding.direction } })
end

return bindings
