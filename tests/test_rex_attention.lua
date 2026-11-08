-- Usage: lua tests/test_rex_attention.lua REPO
local repo = arg[1] or "."
package.path = repo .. "/home/dot_config/rex/?.lua;" .. package.path
rex = {}
local attention = require("attention")

-- urgency: most urgent fresh record wins; visited records drop out until they change.
local records = {
	{ state = "done", updated_at = "2026-11-08T10:00:00Z" },
	{ state = "blocked", updated_at = "2026-11-08T09:00:00Z" },
	{ state = "working", updated_at = "2026-11-08T11:00:00Z" },
}
local rank, at = attention.urgency(records, nil)
assert(rank == 3 and at == "2026-11-08T09:00:00Z", "blocked outranks done")
rank = attention.urgency(records, "2026-11-08T10:00:00Z")
assert(rank == nil, "records at or before the last visit are skipped")
rank = attention.urgency({ { state = "working", updated_at = "x" } }, nil)
assert(rank == nil, "working never queues")
assert(attention.urgency(nil, nil) == nil, "no records, no entry")

-- sort: rank, then newest, then block_id.
local sorted = attention.sort({
	{ block_id = "b", rank = 1, updated_at = "2" },
	{ block_id = "a", rank = 1, updated_at = "2" },
	{ block_id = "c", rank = 2, updated_at = "1" },
	{ block_id = "d", rank = 1, updated_at = "3" },
})
local order = {}
for i, e in ipairs(sorted) do
	order[i] = e.block_id
end
assert(table.concat(order) == "cdab", "got " .. table.concat(order))

-- pick: wraps both ways; an unqueued origin starts at the front or back.
local entries = { { block_id = "x" }, { block_id = "y" }, { block_id = "z" } }
assert(attention.pick(entries, "z", 1).block_id == "x")
assert(attention.pick(entries, "x", -1).block_id == "z")
assert(attention.pick(entries, "elsewhere", 1).block_id == "x")
assert(attention.pick(entries, "elsewhere", -1).block_id == "z")
assert(attention.pick({}, "x", 1) == nil)

print("Rex attention queue ordering verified")
