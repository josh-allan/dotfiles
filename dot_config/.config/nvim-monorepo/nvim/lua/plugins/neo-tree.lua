-- Filetree
local Cmd = require("config.helpers").Cmd
local LazyVim = require("lazyvim.util")

return {
  "nvim-neo-tree/neo-tree.nvim",
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
  opts = {
    filesystem = {
      filtered_items = {
        visible = true, -- when true, they will just be displayed differently than normal items
        hide_dotfiles = false,
        hide_hidden = true, -- only works on Windows for hidden files/directories
        never_show = { -- remains hidden even if visible is toggled to true, this overrides always_show
          ".DS_Store",
        },
      },
    },
  },
  keys = {
    { "<leader>e", Cmd("Neotree reveal"), desc = "Unveil in Neotree" },
  },
}
