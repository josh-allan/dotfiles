require("nvim-tree").setup({
	auto_reload_on_write = true,
	disable_netrw = true,
	hijack_netrw = true,
	respect_buf_cwd = true,
	sync_root_with_cwd = true,
	actions = {
		open_file = {
			quit_on_open = true,
		},
	},
	-- filters = {
	--   custom = { "^.git$" },
	-- },
	-- renderer = {
	--   indent_width = 1,
	-- },
})
