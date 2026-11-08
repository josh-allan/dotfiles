-- Plays a sound when a block's program finishes, except in blocks rexkit dispatched
-- (their labels carry 🤖), so only work you started chimes. Run by the
-- com.josh.rex-done-chime launch agent as `rex do done-chime.lua --all`; not loaded by
-- init.lua. `rex do done-chime.lua player=PATH sound=PATH` swaps the player for tests.

local ROBOT = "🤖"
local player = tostring(rex.args.player or "/usr/bin/afplay")
local sound = tostring(rex.args.sound or "/System/Library/Sounds/Glass.aiff")

-- Root record state per block; only a change into done chimes, not a repeated done.
local last = {}

local function dispatched(block_id)
	local described = rex.session.describe_block({ block_id = block_id })
	if described == nil then
		return true -- closed since it reported; nobody is watching it
	end
	return (described.block.label or ""):find(ROBOT, 1, true) ~= nil
end

rex.on("terminal.program_status_changed", function(ctx, ev)
	if ev.id ~= "" or ctx.block_id == nil then
		return
	end
	local was = last[ctx.block_id]
	last[ctx.block_id] = ev.record.state
	if ev.record.state == "done" and was ~= "done" and not dispatched(ctx.block_id) then
		local _, err = rex.exec.start({ player, sound }, { detach = true })
		if err ~= nil then
			error(err, 0)
		end
	end
end)

rex.on("block_closed", function(_, ev)
	last[ev.block_id] = nil
end)
