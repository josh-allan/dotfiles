local gitsigns = require("gitsigns")
gitsigns.setup({
	signs = {
		add = { text = "┃" },
		change = { text = "┃" },
		delete = { text = "_" },
		topdelete = { text = "‾" },
		changedelete = { text = "~" },
		untracked = { text = "┆" },
	},
	signcolumn = true, --Toggle with :Gitsigns toggle_signs
	linehl = false, -- Toggle with :Gitsigns line_hl
	numhl = false, -- Toggle with :Gitsigns num_hl
	word_diff = false, -- Toggle with :Gitsigns word_diff
	sign_priority = 9,
	watch_gitdir = {
		follow_files = true,
	},
	auto_attach = true,
	attach_to_untracked = false,
	current_line_blame = true,
	current_line_blame_opts = {
		virt_text = true,
		virt_text_pos = "eol", -- 'eol' | 'overlay' | 'right_align'
		delay = 500,
	},
	current_line_blame_formatter = "<author>, <author_time:%Y-%m-%d> - <summary>",
})
