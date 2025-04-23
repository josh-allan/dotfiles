vim.opt.conceallevel = 1

require("obsidian").setup({

	workspaces = {
		{
			name = "personal",
			path = "~/Documents/vault",
		},
		{
			name = "work",
			path = "~/Documents/vault",
			-- Optional, override certain settings.
			overrides = {
				notes_subdir = "notes",
			},
		},
	},
})
