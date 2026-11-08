-- Floating terminals over the current window: a scratch shell, lazygit, and the focused
-- block's scrollback in a read-only nvim. Pressing a float's key again hides it (its
-- program keeps running) and the next press brings it back.

local M = {}

local TERMINAL = "com.superlogical.terminal"

local FLOATS = {
	scratch = { label = "scratch", bounds = { 0.1, 0.1, 0.8, 0.7 } },
	lazygit = { label = "lazygit", bounds = { 0.04, 0.04, 0.92, 0.92 }, command = { "lazygit" } },
}

local SCROLLBACK_LABEL = "scrollback"
-- $1 session, $2 block. buftype=nofile lets q quit without a save prompt.
local SCROLLBACK_SCRIPT = [["$REX_BIN_DIR/rex" capture -s "$1" -b "$2" --trim --unwrap |
  nvim -R -c 'setlocal buftype=nofile nomodifiable' -c 'nnoremap <buffer> q <cmd>qa!<cr>' -c 'normal! G' -]]

local function must(value, err)
	if value == nil and err ~= nil then
		error(err, 0)
	end
	return value
end

-- file:///path URLs from the shell's pwd report, percent-decoded.
local function url_path(url)
	local path = url and url:match("^file://[^/]*(/.*)$")
	if not path then
		return nil
	end
	return (path:gsub("%%(%x%x)", function(hex)
		return string.char(tonumber(hex, 16))
	end))
end

local function cwd_of(block_id)
	local reported = rex.block.call(TERMINAL, "pwd", { block_id = block_id })
	return reported and url_path(reported.pwd)
end

-- The floating layer labelled `label` in the window that holds `block_id`.
local function find_float(block_id, label)
	local view = must(rex.session.view({}))
	for _, window in ipairs(view.windows) do
		local holds, found = false, nil
		for _, layer in ipairs(window.layers) do
			for _, block in ipairs(layer.blocks) do
				if block.block_id == block_id then
					holds = true
				end
				if layer.kind == "floating" and block.label == label then
					found = layer
				end
			end
		end
		if holds then
			return found
		end
	end
	return nil
end

local function open(label, bounds, options)
	must(rex.session.new_layer({
		bounds = bounds,
		layout = { block = { flavor = TERMINAL .. ".shell", label = label, options = options } },
		focus = true,
	}))
end

local function toggle(ctx, float)
	local layer = find_float(ctx.block_id, float.label)
	if layer == nil then
		open(float.label, float.bounds, { cwd = cwd_of(ctx.block_id), command = float.command })
		return
	end
	local hidden = layer.state == "minimized"
	must(rex.session.set_layer_state({
		layer_id = layer.layer_id,
		state = hidden and "normal" or "minimized",
		focus = hidden,
	}))
end

local function toggle_scrollback(ctx)
	local layer = find_float(ctx.block_id, SCROLLBACK_LABEL)
	if layer ~= nil then
		must(rex.session.close_layer({ layer_id = layer.layer_id }))
		return
	end
	open(SCROLLBACK_LABEL, FLOATS.lazygit.bounds, {
		command = { "sh", "-c", SCROLLBACK_SCRIPT, "sh", ctx.session_id, ctx.block_id },
	})
end

function M.setup()
	rex.action({
		name = "scratch_shell",
		title = "Scratch Shell",
		category = "Pane",
		run = function(ctx)
			toggle(ctx, FLOATS.scratch)
		end,
	})
	rex.action({
		name = "lazygit_float",
		title = "lazygit",
		category = "Pane",
		run = function(ctx)
			toggle(ctx, FLOATS.lazygit)
		end,
	})
	rex.action({
		name = "scrollback_float",
		title = "Scrollback in nvim",
		category = "Pane",
		run = toggle_scrollback,
	})
end

return M
