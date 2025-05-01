require("neo-tree").setup({
	close_if_last_window = true,
	enable_git_status = true,
	dependencies = {
		{
			"s1n7ax/nvim-window-picker",
			opts = {
				filter_rules = {
					include_current_win = false,
					autoselect_one = true,
					-- filter using buffer options
					bo = {
						-- if the file type is one of following, the window will be ignored
						filetype = { "neo-tree", "neo-tree-popup", "notify", "noice" },
						-- if the buffer type is one of following, the window will be ignored
						buftype = { "terminal", "quickfix" },
					},
				},
			},
		},
	},
	git_status = {
		symbols = {
			-- Change type
			added = "", -- or "✚", but this is redundant info if you use git_status_colors on the name
			modified = "", -- or "", but this is redundant info if you use git_status_colors on the name
			deleted = "✖", -- this can only be used in the git_status source
			renamed = "󰁕", -- this can only be used in the git_status source
			-- Status type
			untracked = "",
			ignored = "",
			unstaged = "󰄱",
			staged = "",
			conflict = "",
		},
	},
	filesystem = {
		filtered_items = {
			visible = true, -- when true, they will just be displayed differently than normal items
			hide_dotfiles = false,
			never_show = { -- remains hidden even if visible is toggled to true, this overrides always_show
				".DS_Store",
			},
		},
		git_status = {
			window = {
				position = "float",
				mappings = {
					["A"] = "git_add_all",
					["gu"] = "git_unstage_file",
					["ga"] = "git_add_file",
					["gr"] = "git_revert_file",
					["gc"] = "git_commit",
					["gp"] = "git_push",
					["gg"] = "git_commit_and_push",
					["o"] = { "show_help", nowait = false, config = { title = "Order by", prefix_key = "o" } },
					["oc"] = { "order_by_created", nowait = false },
					["od"] = { "order_by_diagnostics", nowait = false },
					["om"] = { "order_by_modified", nowait = false },
					["on"] = { "order_by_name", nowait = false },
					["os"] = { "order_by_size", nowait = false },
					["ot"] = { "order_by_type", nowait = false },
				},
			},
		},
	},
	window = {
		mappings = {
			["J"] = function(state)
				local tree = state.tree
				local node = tree:get_node()
				local siblings = tree:get_nodes(node:get_parent_id())
				local renderer = require("neo-tree.ui.renderer")
				renderer.focus_node(state, siblings[#siblings]:get_id())
			end,
			["K"] = function(state)
				local tree = state.tree
				local node = tree:get_node()
				local siblings = tree:get_nodes(node:get_parent_id())
				local renderer = require("neo-tree.ui.renderer")
				renderer.focus_node(state, siblings[1]:get_id())
			end,
		},
	},
})
