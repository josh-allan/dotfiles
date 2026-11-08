-- Jump between blocks whose programs wait on you, across every session: blocked first,
-- then error, then done, newest first within each. A block you have jumped to drops out
-- until its program reports again.

local M = {}

local TERMINAL = "com.superlogical.terminal"
local RANK = { blocked = 3, error = 2, done = 1 }

-- block_id -> updated_at of the record we last jumped to. Lives until the config reloads.
local visited = {}

-- The block's most urgent unvisited record as rank, updated_at.
function M.urgency(records, last_visit)
	local best_rank, best_at
	for _, record in ipairs(records or {}) do
		local rank = RANK[record.state]
		local fresh = last_visit == nil or record.updated_at > last_visit
		if rank and fresh and (best_rank == nil or rank > best_rank or (rank == best_rank and record.updated_at > best_at)) then
			best_rank, best_at = rank, record.updated_at
		end
	end
	return best_rank, best_at
end

-- Most urgent first, then newest; block_id breaks ties so the order is stable.
function M.sort(entries)
	table.sort(entries, function(a, b)
		if a.rank ~= b.rank then
			return a.rank > b.rank
		end
		if a.updated_at ~= b.updated_at then
			return a.updated_at > b.updated_at
		end
		return a.block_id < b.block_id
	end)
	return entries
end

-- The entry `step` away from `from`, wrapping; when `from` is not queued, next takes the
-- front and previous the back.
function M.pick(entries, from, step)
	if #entries == 0 then
		return nil
	end
	for i, entry in ipairs(entries) do
		if entry.block_id == from then
			return entries[(i - 1 + step) % #entries + 1]
		end
	end
	return step > 0 and entries[1] or entries[#entries]
end

local function must(value, err)
	if value == nil and err ~= nil then
		error(err, 0)
	end
	return value
end

local function queue()
	local entries = {}
	for _, session in ipairs(must(rex.call("session.list")).sessions) do
		-- A config action reaches only its own session until it attaches another.
		must(rex.call("session.attach", { session_id = session.session_id }))
		local view = must(rex.session.view({ session_id = session.session_id }))
		for _, window in ipairs(view.windows) do
			for _, layer in ipairs(window.layers) do
				for _, block in ipairs(layer.blocks) do
					local status = rex.block.call(TERMINAL, "program_status", {
						session_id = session.session_id,
						block_id = block.block_id,
					})
					local rank, at = M.urgency(status and status.records, visited[block.block_id])
					if rank then
						entries[#entries + 1] = {
							session_id = session.session_id,
							block_id = block.block_id,
							rank = rank,
							updated_at = at,
						}
					end
				end
			end
		end
	end
	return M.sort(entries)
end

local function jump(ctx, step)
	local target = M.pick(queue(), ctx.block_id, step)
	if target == nil then
		return nil
	end
	visited[target.block_id] = target.updated_at
	must(rex.session.focus_block({ session_id = target.session_id, block_id = target.block_id }))
	rex.client.queue("session.select", { session_id = target.session_id })
	return { session_id = target.session_id, block_id = target.block_id }
end

function M.setup()
	rex.action({
		name = "attention_next",
		title = "Next Waiting Block",
		category = "Session",
		run = function(ctx)
			return jump(ctx, 1)
		end,
	})
	rex.action({
		name = "attention_previous",
		title = "Previous Waiting Block",
		category = "Session",
		run = function(ctx)
			return jump(ctx, -1)
		end,
	})
end

return M
