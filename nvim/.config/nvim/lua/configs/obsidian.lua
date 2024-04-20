require("obsidian").setup({
	workspaces = {
		{
			name = "personal",
			path = "~/vault",
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
